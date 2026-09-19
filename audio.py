import sounddevice as sd
from scipy.io.wavfile import write


def record_audio(duration, start_event, ready_event, status):
    """Prepare the microphone, then record when the shared event is released."""
    sample_rate = 44100

    try:
        # Fail before the recording session begins if no input device is available.
        sd.query_devices(kind="input")
        ready_event.set()

        start_event.wait()
        print("Microphone recording started...")

        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
        )
        sd.wait()

        write("myrecording.wav", sample_rate, recording)
        print("\nMicrophone recording finished!")
        print("Audio saved as myrecording.wav")

    except Exception as error:
        status["audio_error"] = str(error)
        ready_event.set()
