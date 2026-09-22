import time
import sounddevice as sd
from scipy.io.wavfile import write


def record_audio(duration, start_event, ready_event, status, output_path="myrecording.wav", stop_event=None):
    """Prepare the microphone, then record when the shared event is released."""
    sample_rate = 44100

    try:
        # Fail before the recording session begins if no input device is available.
        sd.query_devices(kind="input")
        ready_event.set()

        start_event.wait()
        print("Microphone recording started...")

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
        recorded_part = recording[:actual_samples] if actual_samples > 0 else recording

        write(output_path, sample_rate, recorded_part)
        print("\nMicrophone recording finished!")
        print(f"Audio saved as {output_path}")

    except Exception as error:
        status["audio_error"] = str(error)
        print(f"[Audio Error] {error}. Writing silence fallback.")
        ready_event.set()
        try:
            import numpy as np
            silence = np.zeros(sample_rate * 2, dtype=np.float32)
            write(output_path, sample_rate, silence)
        except Exception:
            pass

