import os
import time
import warnings

import torch

warnings.filterwarnings(
    "ignore",
    message=r".*torch_dtype.*deprecated.*"
)
# Hide Hugging Face / Transformers warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore")

from crisperwhisper import CrisperWhisperModel


MODEL_PATH = r".\models\CrisperWhisper2.0_small"

model = None
model_device = None


def preferred_device():
    """Use the NVIDIA GPU when PyTorch can access it."""
    if torch.cuda.is_available():
        return "cuda", "float16"

    return "cpu", "float32"


def load_model():

    global model, model_device

    if model is None:

        device, compute_type = preferred_device()

        load_started = time.perf_counter()

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

            # A missing/unsupported CUDA runtime should not prevent the app
            # from working, although CPU inference is much slower.
            print(f"GPU model loading failed ({error}). Falling back to CPU.")
            model = CrisperWhisperModel(
                MODEL_PATH,
                backend="transformers",
                device="cpu",
                compute_type="float32",
            )
            model_device = "cpu"

    return model


def transcribe_audio(audio_file):

    if not os.path.exists(audio_file):

        print("ERROR: Audio file not found!")

        return None

    try:

        whisper_model = load_model()

        result = whisper_model.transcribe(
            audio_file,
            mode="verbatim",
            language="en",
        )

        return result.text

    except Exception as e:

        print("\nTranscription error:")
        print(e)

        return None
