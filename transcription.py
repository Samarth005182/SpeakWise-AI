import os
import re
import warnings

import torch
from crisperwhisper import CrisperWhisperModel
from audio_text import get_audio_stats

warnings.filterwarnings(
    "ignore",
    message=r".*torch_dtype.*deprecated.*"
)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore")


MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "CrisperWhisper2.0_small")

model = None
model_device = None


def preferred_device():
    if torch.cuda.is_available():
        return "cuda", "float16"

    return "cpu", "float32"


def load_model():

    global model, model_device

    if model is None:

        device, compute_type = preferred_device()

        try:
            model = CrisperWhisperModel(
                MODEL_PATH,
                backend="transformers",
                device=device,
                compute_type=compute_type,
            )
            model_device = device

        except Exception as error:
            if device != "cuda":
                raise

            model = CrisperWhisperModel(
                MODEL_PATH,
                backend="transformers",
                device="cpu",
                compute_type="float32",
            )
            model_device = "cpu"

    return model


def transcribe_audio_detailed(audio_file):
    """Transcribe an audio file and retain the reason when no transcript is returned."""
    if not os.path.exists(audio_file):
        return {"text": "", "status": "audio_missing", "error": f"Audio file not found: {audio_file}"}

    try:
        audio_stats = get_audio_stats(audio_file)
        # Use a conservative hard-silence gate. The looser speech detector is
        # useful for diagnostics, but can reject quiet voices before ASR sees them.
        if audio_stats["duration"] <= 0 or (
            audio_stats["max_amplitude"] < 0.005 and audio_stats["mean_rms"] < 0.0005
        ):
            return {"text": "", "status": "no_speech", "error": None,
                    "audio_diagnostics": audio_stats}
        silence_check_error = None
    except Exception as error:
        # Let ASR make the decision if acoustic validation itself is unavailable.
        audio_stats = None
        silence_check_error = str(error)

    try:
        whisper_model = load_model()
        result = whisper_model.transcribe(audio_file, mode="verbatim", language="en")
        raw_text = result.text if result and hasattr(result, "text") else ""
        cleaned_text = _clean_transcription(raw_text)
        if not cleaned_text:
            return {"text": "", "status": "no_speech", "error": None,
                    "diagnostic": silence_check_error, "audio_diagnostics": audio_stats}
        return {"text": cleaned_text, "status": "success", "error": None,
                "audio_diagnostics": audio_stats}
    except Exception as error:
        return {"text": "", "status": "failed", "error": str(error),
                "diagnostic": silence_check_error}


def _clean_transcription(text):
    if not text:
        return ""

    text = text.strip()

    hallucinations = [
        r"^\[BLANK_AUDIO\]$",
        r"^\[silence\]$",
        r"^\[music\]$",
        r"^\[applause\]$",
        r"^(thank you\W*){2,}$",
        r"^(thanks for watching\W*)+$",
        r"^(subtitles? by\W*)+.*$",
        r"^(you\W*){4,}$",
        r"^(\.\W*)+$",
    ]

    for pattern in hallucinations:
        if re.match(pattern, text, re.IGNORECASE):
            return ""

    words = text.split()
    if len(words) >= 5:
        unique_words = set(w.lower().strip(".,!?;:\"'") for w in words)
        if len(unique_words) == 1:
            return ""

    return text


def transcribe_audio(audio_file):
    return transcribe_audio_detailed(audio_file)["text"]
