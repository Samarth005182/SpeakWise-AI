import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")


def generate_recording_paths():
    os.makedirs(RECORDINGS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    audio_path = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.wav")
    video_path = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.avi")

    return audio_path, video_path
