# SpeakWise AI

A local command-line speaking-practice application. It selects a prompt,
records synchronized microphone and webcam input, transcribes the recording,
and reports filler words and pauses.

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For fast NVIDIA GPU transcription, install the CUDA-compatible PyTorch build
from the [official PyTorch selector](https://pytorch.org/get-started/locally/).
The application automatically uses CUDA with FP16 when it is available and
otherwise falls back to CPU.

Download the `CrisperWhisper2.0_small` model and place it here:

```text
models/CrisperWhisper2.0_small/
```

For video-presence analysis, also download the MediaPipe task models and place
them here:

```text
models/face_landmarker.task
models/hand_landmarker.task
```

The face model is required for head pose and camera-facing gaze estimation.
The hand model is optional: without it, the app still runs and reports that
hand-motion feedback is unavailable. The first three seconds of a video are
used as a personal camera-facing baseline, so start each recording by looking
naturally at the camera. The analyzer reports calibration and tracking quality
instead of guessing when eyes are closed, the face is too small, or the
baseline is insufficient. Camera-facing feedback is an iris-and-head-pose
estimate, not a medical pupil or attention measurement.

Model weights are intentionally excluded from Git because they are large and
have their own license.

## Run

```powershell
.\.venv\Scripts\python.exe main.py
```

Press `Q` in the camera window to stop the video recording early.
