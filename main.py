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
from ai import ai_prepare
from recording_paths import generate_recording_paths
from login import authenticate, user_menu, save_session


RECORDING_SECONDS = 60

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


def run_speech_session():
    """Run a single speech practice session.

    Returns:
        tuple of (topic, scores_dict) on success, or (None, None) on failure.
    """

    time.sleep(1)
    print("\n ----- SPEAKWISE AI ----- \n")
    time.sleep(2)

    topics = [
        "The Great Emu War",
        "Tetris Effect",
        "The Dancing Plague of 1518",
        "Ghost Ships and the 'Mary Celeste' Mystery",
        "The Overview Effect",
        "Kessler Syndrome",
        "The Voynich Manuscript",
        "The Year Without a Summer (1816)",
        "The Antikythera Mechanism",
        "The Dark Flow",
    ]

    topic = random.choice(topics)
    print("The topic is:", topic)
    time.sleep(3)

    PREP_SECONDS = 120

    print("\n--- Preparation Phase ---")
    print("You can chat with an AI coach to prepare your speech.")
    print(f"You have {PREP_SECONDS} seconds.\n")
    time.sleep(2)

    try:
        ai_prepare(topic, time_limit=PREP_SECONDS)
    except Exception as e:
        print(f"\nAI Coach unavailable ({e}). Proceeding with silent prep...")
        print("\n###### PREPARATION TIME ######")
        countdown(PREP_SECONDS)

    print("\n----- Preparation Over! Get Comfortable for Speaking -----")
    countdown(10)

    print("\n###### GET SPEAKING ######")
    print(f"You have {RECORDING_SECONDS} seconds.\n")
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
        args=(RECORDING_SECONDS, start_event, audio_ready, recording_status, audio_path),
    )
    video_thread = threading.Thread(
        target=video_capture.record_video,
        args=(
            RECORDING_SECONDS,
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
        return topic, None

    # `perf_counter` provides a monotonic, common deadline for video and timer.
    timing["start_time"] = time.perf_counter()
    timing["deadline"] = timing["start_time"] + RECORDING_SECONDS
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

    text = transcribe_audio(audio_path)
    if text is None:
        print("\nTranscription failed.")
        return topic, None

    words = text.split()
    total_words = len(words)

    fillers = detect_fillers(text)
    total_fillers = sum(fillers.values())

    pauses = detect_pauses(audio_path)

    print("Analysis complete!")

    print_report(
        video_report,
        total_words,
        total_fillers,
        pauses,
        RECORDING_SECONDS,
        text,
    )

    # Build scores dict for database storage
    from report import (
        score_speech_fluency,
        score_pause_management,
        score_eye_contact,
        score_head_stability,
        score_speech_pace,
    )

    scores = {
        "fluency": score_speech_fluency(total_words, total_fillers),
        "pauses": score_pause_management(pauses, RECORDING_SECONDS),
        "eye_contact": score_eye_contact(video_report),
        "head_stability": score_head_stability(video_report),
        "pace": score_speech_pace(total_words, RECORDING_SECONDS),
        "relevance": None,
        "total_words": total_words,
        "total_fillers": total_fillers,
    }
    scores["overall"] = calculate_overall(scores)

    return topic, scores


if __name__ == "__main__":

    while True:
        # --- Authentication Gate ---
        user = authenticate()
        if user is None:
            break

        # --- Post-login loop ---
        while True:
            action = user_menu(user)

            if action == "speech":
                topic, scores = run_speech_session()

                if scores is not None:
                    save_session(user["id"], topic, scores)
                    print("\n  ✓ Session saved to your history.\n")
                else:
                    print("\n  ⚠ Session could not be scored.\n")

                input("\nPress ENTER to continue...")

            elif action == "logout":
                print(f"\n  Logged out. Goodbye, {user['username']}!\n")
                break
