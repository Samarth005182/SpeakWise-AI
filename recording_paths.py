import os
from datetime import datetime

RECORDINGS_DIR = "recordings"


def generate_recording_paths():
    """Generate unique, timestamped file paths for audio and video.

    Creates the recordings directory if it does not exist and returns
    a (audio_path, video_path) tuple with filenames based on the
    current date and time so that previous recordings are never
    overwritten.
    """
    os.makedirs(RECORDINGS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    audio_path = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.wav")
    video_path = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.avi")

    return audio_path, video_path
