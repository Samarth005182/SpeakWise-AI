import time
import logging
import os
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


logger = logging.getLogger(__name__)


def record_audio(duration, start_event, ready_event, status, output_path="myrecording.wav", stop_event=None):
    sample_rate = 44100

    try:
        sd.query_devices(kind="input")
        status["audio_device_available"] = True
        ready_event.set()

        start_event.wait()
        if stop_event and stop_event.is_set():
            return

        start_time = time.perf_counter()
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
        )

        if stop_event:
            while sd.get_stream().active:
                if stop_event.is_set():
                    sd.stop()
                    break
                time.sleep(0.05)
        else:
            sd.wait()

        elapsed = time.perf_counter() - start_time
        actual_samples = min(len(recording), int(elapsed * sample_rate))
        if actual_samples <= 0:
            raise RuntimeError("Microphone produced no audio samples.")
        recorded_part = recording[:actual_samples]

        write(output_path, sample_rate, recorded_part)
        if not os.path.exists(output_path) or os.path.getsize(output_path) <= 44:
            raise RuntimeError("Audio recording file is empty or invalid.")
        status["audio_samples"] = int(actual_samples)
        status["audio_recording_valid"] = True

    except Exception as error:
        status["audio_error"] = str(error)
        status["audio_device_available"] = False
        logger.exception("Audio recording failed")
        ready_event.set()

