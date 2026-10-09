import os
import re
import warnings

import torch
from crisperwhisper import CrisperWhisperModel
from audio_text import is_audio_silent

warnings.filterwarnings(
    "ignore",
    message=r".*torch_dtype.*deprecated.*"
)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore")


MODEL_PATH = r".\models\CrisperWhisper2.0_small"

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

            print(f"GPU model loading failed ({error}). Falling back to CPU.")
            model = CrisperWhisperModel(
                MODEL_PATH,
                backend="transformers",
                device="cpu",
                compute_type="float32",
            )
            model_device = "cpu"

    return model


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
    if not os.path.exists(audio_file):
        print("ERROR: Audio file not found!")
        return ""

    try:
        if is_audio_silent(audio_file):
            print("[Audio] Silence detected (no vocal activity). Skipping Whisper inference.")
            return ""
    except Exception as e:
        print(f"[Audio Check Warning] {e}")

    try:
        whisper_model = load_model()

        result = whisper_model.transcribe(
            audio_file,
            mode="verbatim",
            language="en",
        )

        raw_text = result.text if result and hasattr(result, "text") else ""
        cleaned_text = _clean_transcription(raw_text)

        return cleaned_text

    except Exception as e:
        print("\nTranscription error:")
        print(e)
        return ""
