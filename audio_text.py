import librosa
import numpy as np


def detect_pauses(audio_file, min_pause_duration=0.5):

    # Load audio
    audio, sample_rate = librosa.load(
        audio_file,
        sr=16000
    )

    # Detect intervals where speech is present
    intervals = librosa.effects.split(
        audio,
        top_db=30
    )

    pauses = []

    # Compare the end of one speech section
    # with the beginning of the next speech section

    for i in range(len(intervals) - 1):

        speech_end = intervals[i][1]
        next_speech_start = intervals[i + 1][0]

        pause_duration = (
            next_speech_start - speech_end
        ) / sample_rate

        if pause_duration >= min_pause_duration:
            pauses.append(pause_duration)

    return pauses