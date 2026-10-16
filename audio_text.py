import os
import librosa
import numpy as np


def get_audio_stats(audio_file):
    if not os.path.exists(audio_file):
        return {
            "duration": 0.0,
            "mean_rms": 0.0,
            "max_amplitude": 0.0,
            "has_speech": False,
            "speech_intervals": [],
            "speech_ratio": 0.0,
        }

    try:
        audio, sample_rate = librosa.load(audio_file, sr=16000)
    except Exception:
        return {
            "duration": 0.0,
            "mean_rms": 0.0,
            "max_amplitude": 0.0,
            "has_speech": False,
            "speech_intervals": [],
            "speech_ratio": 0.0,
        }

    if len(audio) == 0:
        return {
            "duration": 0.0,
            "mean_rms": 0.0,
            "max_amplitude": 0.0,
            "has_speech": False,
            "speech_intervals": [],
            "speech_ratio": 0.0,
        }

    duration = len(audio) / sample_rate
    max_amp = float(np.max(np.abs(audio)))
    
    rms = librosa.feature.rms(y=audio, frame_length=1024, hop_length=512)[0]
    mean_rms = float(np.mean(rms)) if len(rms) > 0 else 0.0

    intervals = librosa.effects.split(audio, top_db=25)
    
    total_speech_samples = sum((end - start) for start, end in intervals) if len(intervals) > 0 else 0
    speech_duration = total_speech_samples / sample_rate
    speech_ratio = speech_duration / duration if duration > 0 else 0.0

    has_speech = (max_amp >= 0.02) and (mean_rms >= 0.003) and (speech_duration >= 0.4)

    return {
        "duration": duration,
        "mean_rms": mean_rms,
        "max_amplitude": max_amp,
        "has_speech": has_speech,
        "speech_intervals": intervals,
        "speech_ratio": speech_ratio,
        "speech_duration": speech_duration,
    }


def get_audio_duration(audio_file):
    """Return actual decoded audio duration in seconds, or 0 when unavailable."""
    if not os.path.exists(audio_file):
        return 0.0
    try:
        info = librosa.get_duration(path=audio_file)
        return float(info) if np.isfinite(info) else 0.0
    except Exception:
        return 0.0


def is_audio_silent(audio_file):
    stats = get_audio_stats(audio_file)
    return not stats["has_speech"]


def detect_pauses(audio_file, min_pause_duration=0.5):
    if not os.path.exists(audio_file):
        return []

    try:
        audio, sample_rate = librosa.load(audio_file, sr=16000)
    except Exception:
        return []

    if len(audio) == 0:
        return []

    intervals = librosa.effects.split(audio, top_db=25)

    if len(intervals) <= 1:
        return []

    pauses = []
    for i in range(len(intervals) - 1):
        speech_end = intervals[i][1]
        next_speech_start = intervals[i + 1][0]

        pause_duration = (next_speech_start - speech_end) / sample_rate

        if pause_duration >= min_pause_duration:
            pauses.append(pause_duration)

    return pauses
