from audio_text import detect_pauses, get_audio_duration
import threading
import time

from dotenv import load_dotenv
load_dotenv()

import audio
import video_capture
from filler_detection import detect_fillers
from transcription import transcribe_audio_detailed
from video_analysis import analyze_video
from report import print_report
from ai import ai_prepare, analyze_relevance
from recording_paths import generate_recording_paths
from login import authenticate, user_menu, save_session
from topics import get_random_topic, get_all_categories


def countdown(total_seconds):
    for remaining in range(total_seconds, 0, -1):
        time.sleep(1)


def recording_countdown(timing):
    deadline = timing["deadline"]
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        time.sleep(min(0.5, remaining))


def select_category():
    categories = get_all_categories()

    while True:
        choice = input().strip()
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


def select_speaking_duration():
    while True:
        choice = input().strip()
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
                custom = input().strip()
                if custom.lower() in ("b", "back"):
                    break
                if not custom:
                    return 60
                if custom.isdigit():
                    sec = int(custom)
                    if 15 <= sec <= 300:
                        return sec


def run_speech_session():
    selected_category = select_category()
    if selected_category == "CANCELLED":
        return None

    speaking_seconds = select_speaking_duration()
    if speaking_seconds is None:
        return None

    category, topic = get_random_topic(selected_category)

    PREP_SECONDS = 120

    try:
        ai_prepare(topic, time_limit=PREP_SECONDS, speaking_time=speaking_seconds)
    except Exception:
        countdown(PREP_SECONDS)

    countdown(10)

    start_event = threading.Event()
    audio_ready = threading.Event()
    video_ready = threading.Event()
    recording_status = {}
    timing = {}

    audio_path, video_path = generate_recording_paths()

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

    audio_ready.wait()
    video_ready.wait()

    timing["start_time"] = time.perf_counter()
    timing["deadline"] = timing["start_time"] + speaking_seconds
    start_event.set()

    timer_thread = threading.Thread(target=recording_countdown, args=(timing,))
    timer_thread.start()

    video_thread.join()
    audio_thread.join()
    timer_thread.join()

    video_report = None
    video_status = "unavailable"
    video_error = recording_status.get("video_error")
    if recording_status.get("video_analysis_eligible", True):
        try:
            video_report = analyze_video(video_path)
            video_status = "success" if video_report else "unavailable"
        except Exception as error:
            video_status = "failed"
            video_error = str(error)

    audio_duration = get_audio_duration(audio_path)
    audio_status = "available" if audio_duration > 0 and not recording_status.get("audio_error") else "unavailable"
    if recording_status.get("audio_error"):
        transcription_result = {"text": "", "status": "failed", "error": recording_status["audio_error"]}
    else:
        transcription_result = transcribe_audio_detailed(audio_path)
    text = transcription_result["text"]
    words = text.split()
    total_words = len(words)

    fillers = detect_fillers(text)
    total_fillers = sum(fillers.values())

    pauses = detect_pauses(audio_path)

    relevance_result = None
    try:
        relevance_result = analyze_relevance(topic, text)
    except Exception:
        pass

    scores = print_report(
        video_report=video_report,
        total_words=total_words,
        total_fillers=total_fillers,
        pauses=pauses,
        duration=audio_duration or speaking_seconds,
        transcription=text,
        topic=topic,
        relevance_result=relevance_result,
        filler_breakdown=fillers,
        transcription_status=transcription_result["status"],
        transcription_error=transcription_result.get("error"),
        audio_status=audio_status,
        video_status=video_status,
        video_error=video_error,
    )

    return category, topic, speaking_seconds, audio_path, video_path, text, scores


if __name__ == "__main__":
    import sys

    if "--cli" not in sys.argv:
        try:
            from gui import SpeakWiseApp
            app = SpeakWiseApp()
            app.mainloop()
            sys.exit(0)
        except Exception:
            pass

    while True:
        user = authenticate()
        if user is None:
            break

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

                input()

            elif action == "logout":
                break

            elif action == "deleted":
                break
