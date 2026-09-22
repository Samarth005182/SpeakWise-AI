import os
import librosa
import numpy as np


def get_audio_stats(audio_file):
    """
    Load audio and compute RMS energy, peak amplitude, and active speech intervals.
    
    Returns:
        dict: {
            "duration": float,
            "mean_rms": float,
            "max_amplitude": float,
            "has_speech": bool,
            "speech_intervals": list of tuples,
            "speech_ratio": float
        }
    """
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
    except Exception as e:
        print(f"[Audio Analysis Error] {e}")
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
    
    # Calculate RMS (Root Mean Square) energy
    rms = librosa.feature.rms(y=audio, frame_length=1024, hop_length=512)[0]
    mean_rms = float(np.mean(rms)) if len(rms) > 0 else 0.0

    # Detect speech intervals using energy-based top_db split
    # top_db=25 detects reasonably audible speech above background noise
    intervals = librosa.effects.split(audio, top_db=25)
    
    total_speech_samples = sum((end - start) for start, end in intervals) if len(intervals) > 0 else 0
    speech_duration = total_speech_samples / sample_rate
    speech_ratio = speech_duration / duration if duration > 0 else 0.0

    # Audio is considered to have speech if:
    # 1. Max amplitude > 0.02 (not pure noise/hiss)
    # 2. Mean RMS > 0.003
    # 3. Speech duration >= 0.4 seconds
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


def is_audio_silent(audio_file):
    """Return True if the audio file contains only silence or background noise."""
    stats = get_audio_stats(audio_file)
    return not stats["has_speech"]


def detect_pauses(audio_file, min_pause_duration=0.5):
    """
    Detect pauses between spoken intervals in seconds.
    If no speech is detected at all, returns empty list (the caller checks has_speech).
    """
    if not os.path.exists(audio_file):
        return []

    try:
        audio, sample_rate = librosa.load(audio_file, sr=16000)
    except Exception:
        return []

    if len(audio) == 0:
        return []

    # Detect intervals where speech is present
    intervals = librosa.effects.split(audio, top_db=25)

    if len(intervals) <= 1:
        return []

    pauses = []
    # Compare the end of one speech section with the beginning of the next
    for i in range(len(intervals) - 1):
        speech_end = intervals[i][1]
        next_speech_start = intervals[i + 1][0]

        pause_duration = (next_speech_start - speech_end) / sample_rate

        if pause_duration >= min_pause_duration:
            pauses.append(pause_duration)

    return pauses