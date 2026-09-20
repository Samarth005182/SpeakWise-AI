from google import genai
import json
import os
import threading
import time


MAX_RETRIES = 5
RETRY_DELAY = 3  # base seconds between retries (exponential backoff)

# Models to try in order — if one is overloaded or deprecated, try the next
FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def _send_with_retry(chat, message):
    """Send a message with automatic retry on transient errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return chat.send_message(message)
        except Exception as e:
            error_str = str(e)
            is_transient = any(
                code in error_str
                for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
            )
            if is_transient and attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                print(f"  (Server busy, retrying in {wait}s... attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise


def _connect_with_fallback(client, setup_message):
    """Try each model in FALLBACK_MODELS until one responds successfully."""
    last_error = None
    for model_name in FALLBACK_MODELS:
        print(f"  Trying model: {model_name}...")
        try:
            chat = client.chats.create(model=model_name)
            res = _send_with_retry(chat, setup_message)
            print(f"  Connected to {model_name} [OK]")
            return chat, res
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "404" in error_str:
                print(f"  {model_name} not available, trying next...")
            else:
                print(f"  {model_name} failed ({type(e).__name__}), trying next...")
    if last_error is None:
        raise RuntimeError("No models configured in FALLBACK_MODELS.")
    raise RuntimeError(
        f"All models failed: {', '.join(FALLBACK_MODELS)}"
    ) from last_error


def ai_prepare(topic, time_limit=120):
    """Interactive AI chat to help the user prepare for their speech topic.

    Args:
        topic: The speech topic the user needs to prepare for.
        time_limit: Seconds allowed for AI-assisted preparation.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set. Add it to your .env file.")

    client = genai.Client(api_key=api_key)

    # Send an initial system-like message to set context
    setup_message = (
        f"You are a helpful speech coach. The user has been given the topic: "
        f"\"{topic}\". Help them brainstorm key points, structure their speech, "
        f"and prepare to speak about this topic for 1 minute. Keep your responses "
        f"concise and actionable. Start by giving them 3-4 key talking points."
    )

    print(f"AI Coach is ready! Ask questions about \"{topic}\" to prepare.")
    print(f"You have {time_limit} seconds. Type 'done' to finish early.\n")

    print("Connecting to AI Coach...")
    chat, res = _connect_with_fallback(client, setup_message)
    print(f"\nAI Coach: {res.text}\n")

    # Flag to signal time is up
    time_up = threading.Event()

    def _timer():
        time_up.wait(timeout=time_limit)
        if not time_up.is_set():
            time_up.set()
            print("\n\n⏰ Preparation time is up!\n")

    timer_thread = threading.Thread(target=_timer, daemon=True)
    timer_thread.start()

    while not time_up.is_set():
        try:
            message = input("You > ")
        except EOFError:
            break

        if time_up.is_set():
            break
        if message.strip().lower() in ("done", "exit", "quit"):
            time_up.set()
            break
        if not message.strip():
            continue

        try:
            res = _send_with_retry(chat, message)
            print(f"\nAI Coach: {res.text}\n")
        except Exception as e:
            print(f"\n[!] Couldn't get a response: {e}")
            print("Try again or type 'done' to move on.\n")

    # Ensure timer thread finishes
    time_up.set()
    timer_thread.join(timeout=2)


def analyze_relevance(topic, transcription):
    """Analyze how relevant the transcribed speech content is to the topic.

    Sends the transcription text to Gemini AI and returns a dict with
    a relevance score (1-10) and a list of off-topic sentences.

    Returns None if the analysis cannot be completed.
    """
    if not transcription or not transcription.strip():
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)

    prompt = (
        f'You are a speech evaluation assistant. The speaker was assigned '
        f'the topic: "{topic}".\n'
        f'Below is the transcription of their speech. Rate how relevant the '
        f'speech CONTENT is to the assigned topic on a scale of 1 to 10, '
        f'where:\n'
        f'  1-3: Mostly off-topic, barely mentions the subject\n'
        f'  4-6: Partially relevant, touches on the topic but drifts '
        f'significantly\n'
        f'  7-8: Mostly relevant with minor tangents\n'
        f'  9-10: Highly focused and directly addresses the topic '
        f'throughout\n\n'
        f'Also identify any specific sentences from the transcription that '
        f'are off-topic or irrelevant to the assigned topic. If the entire '
        f'speech is relevant, return an empty list.\n\n'
        f'Respond ONLY with valid JSON in this exact format:\n'
        f'{{"relevance_score": <number 1-10>, '
        f'"off_topic_sentences": ["sentence1", "sentence2"]}}\n\n'
        f'Transcription:\n"{transcription}"'
    )

    try:
        chat, res = _connect_with_fallback(client, prompt)
        raw = res.text.strip()

        # Strip markdown code fences if the model wraps its reply
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Remove first and last fence lines
            lines = [
                ln for ln in lines
                if not ln.strip().startswith("```")
            ]
            raw = "\n".join(lines).strip()

        result = json.loads(raw)

        score = result.get("relevance_score")
        if score is None or not isinstance(score, (int, float)):
            return None
        score = max(1.0, min(10.0, float(score)))

        off_topic = result.get("off_topic_sentences", [])
        if not isinstance(off_topic, list):
            off_topic = []

        return {
            "score": score,
            "off_topic_sentences": off_topic,
        }

    except Exception:
        return None
