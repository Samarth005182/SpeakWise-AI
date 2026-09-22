from audio_text import detect_pauses
import os
import random
import threading
import time

from dotenv import load_dotenv
load_dotenv()  # Load .env file (contains GEMINI_API_KEY)

import audio
import video_capture
from filler_detection import detect_fillers
from transcription import transcribe_audio
from video_analysis import analyze_video
from report import print_report, calculate_overall
from ai import ai_prepare, analyze_relevance
from recording_paths import generate_recording_paths
from login import authenticate, user_menu, save_session
from topics import get_random_topic, get_all_categories


DEFAULT_RECORDING_SECONDS = 60

def countdown(total_seconds):
    for remaining in range(total_seconds, 0, -1):
        minutes = remaining // 60
        seconds = remaining % 60
        print(f"\rTime remaining: {minutes:02d}:{seconds:02d}", end="")
        time.sleep(1)
    print()


def recording_countdown(timing):
    """Display a countdown that stays synchronized with the recording deadline."""
    deadline = timing["deadline"]
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        minutes = int(remaining) // 60
        seconds = int(remaining) % 60
        print(f"\rTime remaining: {minutes:02d}:{seconds:02d}", end="")
        time.sleep(min(0.5, remaining))
    print()


def select_category():
    """Prompt the user to choose a category or surprise random selection."""
    categories = get_all_categories()
    print("\n" + "=" * 60)
    print("               CHOOSE SPEECH CATEGORY")
    print("=" * 60)
    print()
    for i, cat in enumerate(categories, 1):
        print(f"  {i:>2}. {cat}")
    print("   0. Surprise Me / Random Category")
    print()
    print("  (Type 'b' or 'back' to cancel)\n")

    while True:
        choice = input("  Select category (0-16) [Default: 0]: ").strip()
        if choice.lower() in ("b", "back"):
            return "CANCELLED"
        if not choice or choice == "0":
            return None

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(categories):
                return categories[idx - 1]

        for cat in categories:
            if choice.lower() == cat.lower():
                return cat

        print(f"  [-] Invalid option. Please enter a number between 0 and {len(categories)}.")


def select_speaking_duration():
    """Prompt the user to choose the speech recording duration in seconds."""
    print("\n" + "=" * 60)
    print("               CHOOSE SPEAKING DURATION")
    print("=" * 60)
    print()
    print("  1. 30 Seconds  (Quick Extempore)")
    print("  2. 60 Seconds  (1 Minute - Standard Default)")
    print("  3. 90 Seconds  (1.5 Minutes)")
    print("  4. 120 Seconds (2 Minutes - Deep Dive)")
    print("  5. Custom Duration")
    print()
    print("  (Type 'b' or 'back' to cancel)\n")

    while True:
        choice = input("  Select duration (1-5) [Default: 2]: ").strip()
        if choice.lower() in ("b", "back"):
            return None
        if not choice or choice == "2":
            return 60
        elif choice == "1":
            return 30
        elif choice == "3":
            return 90
        elif choice == "4":
            return 120
        elif choice == "5":
            while True:
                custom = input("  Enter custom seconds (15 - 300) [Default: 60]: ").strip()
                if custom.lower() in ("b", "back"):
                    break
                if not custom:
                    return 60
                if custom.isdigit():
                    sec = int(custom)
                    if 15 <= sec <= 300:
                        return sec
                    else:
                        print("  [-] Duration must be between 15 and 300 seconds.")
                else:
                    print("  [-] Please enter a valid number.")
        else:
            print("  [-] Invalid option. Please choose 1-5.")


def run_speech_session():
    """Run a single speech practice session.

    Returns:
        tuple of (category, topic, speaking_seconds, audio_path, video_path, text, scores)
        or None on failure/cancel.
    """

    # --- Step 1: Category Selection ---
    selected_category = select_category()
    if selected_category == "CANCELLED":
        print("\n  Practice cancelled. Returning to menu...\n")
        return None

    # --- Step 2: Speaking Duration Selection ---
    speaking_seconds = select_speaking_duration()
    if speaking_seconds is None:
        print("\n  Practice cancelled. Returning to menu...\n")
        return None

    time.sleep(1)
    print("\n" + "=" * 60)
    print("             SPEAKWISE AI — GENERATING TOPIC")
    print("=" * 60)
    if selected_category:
        print(f"\n  Selected Category : {selected_category}")
    else:
        print("\n  Category Mode     : Random / Surprise Me")

    print("  Generating fresh speech topic with AI...\n")
    category, topic = get_random_topic(selected_category)

    time.sleep(1)
    print("=" * 60)
    print(f"  CATEGORY : {category}")
    print(f"  TOPIC    : \"{topic}\"")
    print(f"  DURATION : {speaking_seconds} seconds")
    print("=" * 60)
    time.sleep(3)

    PREP_SECONDS = 120

    print("\n--- Preparation Phase ---")
    print("You can chat with an AI coach to brainstorm and structure your speech.")
    print(f"You have {PREP_SECONDS} seconds.\n")
    time.sleep(2)

    try:
        ai_prepare(topic, time_limit=PREP_SECONDS, speaking_time=speaking_seconds)
    except Exception as e:
        print(f"\nAI Coach unavailable ({e}). Proceeding with silent prep...")
        print("\n###### PREPARATION TIME ######")
        countdown(PREP_SECONDS)

    print("\n----- Preparation Over! Get Comfortable for Speaking -----")
    countdown(10)

    print("\n###### GET SPEAKING ######")
    print(f"You have {speaking_seconds} seconds.\n")
    print("For the first 3 seconds, look naturally at the camera for visual calibration.")

    # The two workers prepare their devices independently, then wait behind the
    # same barrier. This removes the previous six-second audio-only lead-in.
    start_event = threading.Event()
    audio_ready = threading.Event()
    video_ready = threading.Event()
    recording_status = {}
    timing = {}

    # Generate unique file paths for this session
    audio_path, video_path = generate_recording_paths()
    print(f"Audio will be saved to: {audio_path}")
    print(f"Video will be saved to: {video_path}")

    print("Preparing microphone and camera...")
    audio_thread = threading.Thread(
        target=audio.record_audio,
        args=(speaking_seconds, start_event, audio_ready, recording_status, audio_path),
    )
    video_thread = threading.Thread(
        target=video_capture.record_video,
        args=(
            speaking_seconds,
            start_event,
            video_ready,
            recording_status,
            timing,
            video_path,
        ),
    )

    audio_thread.start()
    video_thread.start()

    # Do not start a partial recording if either capture device cannot initialize.
    audio_ready.wait()
    video_ready.wait()
    if recording_status:
        print("\nUnable to start recording:")
        for device, error in recording_status.items():
            print(f"- {device}: {error}")
        return None

    # `perf_counter` provides a monotonic, common deadline for video and timer.
    timing["start_time"] = time.perf_counter()
    timing["deadline"] = timing["start_time"] + speaking_seconds
    print("\nRecording started: microphone and camera are synchronized.")
    start_event.set()

    timer_thread = threading.Thread(target=recording_countdown, args=(timing,))
    timer_thread.start()

    video_thread.join()
    audio_thread.join()
    timer_thread.join()

    # Sync diagnostics
    actual_fps = timing.get("video_actual_fps", 20.0)
    video_frames = timing.get("video_frames", 0)
    actual_video_duration = video_frames / actual_fps if actual_fps > 0 else 0
    print(
        f"\nVideo captured: {video_frames} frames "
        f"({actual_video_duration:.1f}s at {actual_fps:.1f} fps)"
    )

    print("\n\n###### That's it! Nice Work! ######")
    print("\nAnalyzing video and audio...\n")

    video_report = None
    try:
        video_report = analyze_video(video_path)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"  Video analysis skipped: {error}")

    text = transcribe_audio(audio_path) or ""
    words = text.split()
    total_words = len(words)


    fillers = detect_fillers(text)
    total_fillers = sum(fillers.values())

    pauses = detect_pauses(audio_path)

    print("Analyzing topic relevance...")
    relevance_result = None
    try:
        relevance_result = analyze_relevance(topic, text)
    except Exception as e:
        print(f"  Topic relevance analysis skipped: {e}")

    print("Analysis complete!")

    scores = print_report(
        video_report=video_report,
        total_words=total_words,
        total_fillers=total_fillers,
        pauses=pauses,
        duration=speaking_seconds,
        transcription=text,
        topic=topic,
        relevance_result=relevance_result,
        filler_breakdown=fillers,
    )

    return category, topic, speaking_seconds, audio_path, video_path, text, scores


if __name__ == "__main__":
    import sys

    # Default to GUI mode unless --cli flag is passed
    if "--cli" not in sys.argv:
        try:
            from gui import SpeakWiseApp
            app = SpeakWiseApp()
            app.mainloop()
            sys.exit(0)
        except Exception as e:
            print(f"[!] GUI launch notice: {e}. Falling back to CLI mode.\n")

    while True:
        # --- Authentication Gate ---
        user = authenticate()
        if user is None:
            break

        # --- Post-login loop ---
        while True:
            action = user_menu(user)

            if action == "speech":
                result = run_speech_session()

                if result and result[1] is not None:
                    category, topic, speaking_time, audio_path, video_path, text, report_data = result
                    save_session(
                        user_id=user["user_id"],
                        category=category,
                        topic_name=topic,
                        speaking_time=speaking_time,
                        audio_path=audio_path,
                        video_path=video_path,
                        transcription=text,
                        report=report_data,
                    )
                    print("\n  [+] Session and take saved to your history.\n")
                else:
                    print("\n  [!] Session could not be saved.\n")

                input("\nPress ENTER to continue...")

            elif action == "logout":
                print(f"\n  Logged out. Goodbye, {user['name']}!\n")
                break

            elif action == "deleted":
                break
