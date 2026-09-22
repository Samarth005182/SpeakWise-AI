import os
import logging

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"

import cv2
import time
import numpy as np

from dataclasses import dataclass
from collections import Counter
from statistics import median

import mediapipe as mp

try:
    from absl import logging as absl_logging
    absl_logging.set_verbosity(absl_logging.ERROR)
except ImportError:
    pass

logging.getLogger("mediapipe").setLevel(logging.ERROR)

from face_geometry import (
    PCF,
    get_metric_landmarks,
    procrustes_landmark_basis,
)


# ============================================================
# CONFIGURATION
# ============================================================

VIDEO_FILE = "myrecording.avi"
MODEL_FILE = "models/face_landmarker.task"


CALIBRATION_SECONDS = 2.0
SMOOTHING_WINDOW = 5
MIN_STATE_DURATION = 0.35

GAZE_X_TOLERANCE = 0.16
GAZE_Y_TOLERANCE = 0.18

YAW_TOLERANCE = 15.0
PITCH_TOLERANCE = 12.0
ROLL_TOLERANCE = 15.0

LEFT_EYE = [33, 133, 160, 144, 158, 153]
RIGHT_EYE = [362, 263, 385, 380, 387, 373]

LEFT_IRIS = 468
RIGHT_IRIS = 473

JAW_LANDMARKS = [61, 291, 199]


# ============================================================
# MEDIA PIPE SETUP
# ============================================================

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class FrameResult:
    timestamp: float = 0.0
    face_detected: bool = False

    left_x: float | None = None
    left_y: float | None = None
    right_x: float | None = None
    right_y: float | None = None

    yaw: float | None = None
    pitch: float | None = None
    roll: float | None = None

    is_blinking: bool = False
    state: str = "face_missing"


# ============================================================
# ANGLE HELPERS
# ============================================================

def normalize_angle(angle):
    """
    Normalize angle to [-180, 180].
    """
    while angle > 180:
        angle -= 360

    while angle < -180:
        angle += 360

    return angle


def angle_difference(angle, baseline):
    """
    Smallest signed difference between two angles.
    """
    difference = angle - baseline

    while difference > 180:
        difference -= 360

    while difference < -180:
        difference += 360

    return difference


# ============================================================
# EYE GAZE & BLINK
# ============================================================

def calculate_ear(landmarks, eye_points):
    """Calculate Eye Aspect Ratio (EAR) for blink detection."""
    try:
        pts = landmarks[eye_points]
        # eye_points: [p1(outer), p4(inner), p2(top1), p6(bottom1), p3(top2), p5(bottom2)]
        p1 = pts[0, :2]
        p4 = pts[1, :2]
        p2 = pts[2, :2]
        p6 = pts[3, :2]
        p3 = pts[4, :2]
        p5 = pts[5, :2]

        vertical_1 = np.linalg.norm(p2 - p6)
        vertical_2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)

        if horizontal < 1e-6:
            return 0.3
        return float((vertical_1 + vertical_2) / (2.0 * horizontal))
    except Exception:
        return 0.3


def get_eye_gaze(landmarks, eye_points, iris_point):
    """
    Return normalized iris coordinates inside an eye.

    X:
        0 = left side of eye
        1 = right side of eye

    Y:
        0 = top
        1 = bottom
    """

    eye = landmarks[eye_points]
    iris = landmarks[iris_point]

    x0 = eye[:, 0].min()
    x1 = eye[:, 0].max()

    y0 = eye[:, 1].min()
    y1 = eye[:, 1].max()

    if x1 <= x0 or y1 <= y0:
        return None, None

    x = (iris[0] - x0) / (x1 - x0)
    y = (iris[1] - y0) / (y1 - y0)

    return float(x), float(y)



# ============================================================
# HEAD POSE
# ============================================================

def get_head_pose(landmarks, frame_size):
    """
    Estimate head yaw, pitch and roll using MediaPipe's
    metric face geometry and solvePnP.

    This is the original implementation used by the
    working SpeakWise version.
    """

    width, height = frame_size

    focal = width

    camera_matrix = np.array(
        [
            [focal, 0, width / 2],
            [0, focal, height / 2],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )

    dist_coeffs = np.zeros((5, 1), dtype=np.float64)

    try:

        metric_landmarks, _ = get_metric_landmarks(
            landmarks.T.copy(),
            PCF(
                frame_height=height,
                frame_width=width,
                fy=focal,
            ),
        )

        model_landmark_ids = sorted(
            set(
                JAW_LANDMARKS
                + [key for key, _ in procrustes_landmark_basis]
            )
        )

        image_landmarks = (
            np.clip(
                landmarks[model_landmark_ids, :2],
                0.0,
                1.0,
            )
            * np.array([width, height])
        )

        metric_points = metric_landmarks[
            :,
            model_landmark_ids,
        ].T.astype(np.float64)

        image_points = image_landmarks.astype(np.float64)

        success, rotation_vector, translation_vector = cv2.solvePnP(
            metric_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return None, None, None

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

    except (
        cv2.error,
        ValueError,
        IndexError,
        TypeError,
    ):
        return None, None, None

    sy = np.hypot(
        rotation_matrix[0, 0],
        rotation_matrix[1, 0],
    )

    if sy >= 1e-6:

        pitch = np.arctan2(
            rotation_matrix[2, 1],
            rotation_matrix[2, 2],
        )

        yaw = np.arctan2(
            -rotation_matrix[2, 0],
            sy,
        )

        roll = np.arctan2(
            rotation_matrix[1, 0],
            rotation_matrix[0, 0],
        )

    else:

        pitch = np.arctan2(
            -rotation_matrix[1, 2],
            rotation_matrix[1, 1],
        )

        yaw = np.arctan2(
            -rotation_matrix[2, 0],
            sy,
        )

        roll = 0.0

    yaw = float(np.degrees(yaw))
    pitch = float(np.degrees(pitch))
    roll = float(np.degrees(roll))

    yaw = normalize_angle(yaw)
    pitch = normalize_angle(pitch)
    roll = normalize_angle(roll)

    return yaw, pitch, roll


# ============================================================
# MEDIAN HELPER
# ============================================================

def safe_median(values, default=0.0):

    valid = [
        float(value)
        for value in values
        if value is not None
        and np.isfinite(value)
    ]

    if not valid:
        return default

    return float(median(valid))


# ============================================================
# CALIBRATION
# ============================================================

def calibrate(frames):
    """
    Calculate neutral eye and head position from the
    beginning of the video.
    """

    calibration_frames = [
        frame
        for frame in frames
        if frame.timestamp <= CALIBRATION_SECONDS
        and frame.face_detected
    ]

    valid_iris = [
        frame
        for frame in calibration_frames
        if frame.left_x is not None
        and frame.left_y is not None
        and frame.right_x is not None
        and frame.right_y is not None
    ]

    valid_pose = [
        frame
        for frame in calibration_frames
        if frame.yaw is not None
        and frame.pitch is not None
        and frame.roll is not None
    ]

    # --------------------------------------------------------
    # Iris calibration
    # --------------------------------------------------------

    if valid_iris:

        left_x = safe_median(
            [frame.left_x for frame in valid_iris],
            0.5,
        )

        left_y = safe_median(
            [frame.left_y for frame in valid_iris],
            0.5,
        )

        right_x = safe_median(
            [frame.right_x for frame in valid_iris],
            0.5,
        )

        right_y = safe_median(
            [frame.right_y for frame in valid_iris],
            0.5,
        )

    else:

        left_x = 0.5
        left_y = 0.5
        right_x = 0.5
        right_y = 0.5

    # --------------------------------------------------------
    # Head pose calibration
    # --------------------------------------------------------

    if valid_pose:

        yaw = safe_median(
            [frame.yaw for frame in valid_pose],
            0.0,
        )

        pitch = safe_median(
            [frame.pitch for frame in valid_pose],
            0.0,
        )

        roll = safe_median(
            [frame.roll for frame in valid_pose],
            0.0,
        )

    else:

        yaw = 0.0
        pitch = 0.0
        roll = 0.0

    return {
        "left_x": left_x,
        "left_y": left_y,
        "right_x": right_x,
        "right_y": right_y,
        "yaw": yaw,
        "pitch": pitch,
        "roll": roll,
        "calibration_samples": len(valid_pose),
        "iris_samples": len(valid_iris),
    }


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_face(
    frame,
    calibration,
):
    """
    Determine the user's visual state.
    """

    if not frame.face_detected:
        return "face_missing"

    # --------------------------------------------------------
    # Head differences
    # --------------------------------------------------------

    yaw_difference = 0.0
    pitch_difference = 0.0
    roll_difference = 0.0

    if frame.yaw is not None:
        yaw_difference = angle_difference(
            frame.yaw,
            calibration["yaw"],
        )

    if frame.pitch is not None:
        pitch_difference = angle_difference(
            frame.pitch,
            calibration["pitch"],
        )

    if frame.roll is not None:
        roll_difference = angle_difference(
            frame.roll,
            calibration["roll"],
        )

    # --------------------------------------------------------
    # Head turned
    # --------------------------------------------------------

    if abs(yaw_difference) > YAW_TOLERANCE:
        return "head_turned"

    # If the user is simply blinking while facing the camera, retain contact
    if getattr(frame, "is_blinking", False):
        return "camera_contact"

    # --------------------------------------------------------
    # Iris differences
    # --------------------------------------------------------

    left_dx = 0.0
    left_dy = 0.0

    right_dx = 0.0
    right_dy = 0.0

    if frame.left_x is not None:
        left_dx = frame.left_x - calibration["left_x"]

    if frame.left_y is not None:
        left_dy = frame.left_y - calibration["left_y"]

    if frame.right_x is not None:
        right_dx = frame.right_x - calibration["right_x"]

    if frame.right_y is not None:
        right_dy = frame.right_y - calibration["right_y"]

    avg_dx = (left_dx + right_dx) / 2.0
    avg_dy = (left_dy + right_dy) / 2.0

    # --------------------------------------------------------
    # Looking up/down
    # --------------------------------------------------------

    if avg_dy < -GAZE_Y_TOLERANCE:
        return "looking_up"

    if avg_dy > GAZE_Y_TOLERANCE:
        return "looking_down"

    # --------------------------------------------------------
    # Looking left/right
    # --------------------------------------------------------

    if avg_dx < -GAZE_X_TOLERANCE:
        return "looking_left"

    if avg_dx > GAZE_X_TOLERANCE:
        return "looking_right"

    # --------------------------------------------------------
    # Camera contact
    # --------------------------------------------------------

    return "camera_contact"



# ============================================================
# SMOOTH STATES
# ============================================================

def smooth_states(frames):
    """
    Remove very short state changes caused by landmark noise.
    """

    if not frames:
        return frames

    states = [
        frame.state
        for frame in frames
    ]

    fps = 30.0

    if len(frames) > 1:

        timestamps = [
            frame.timestamp
            for frame in frames
            if frame.timestamp is not None
        ]

        if len(timestamps) > 1:

            duration = timestamps[-1] - timestamps[0]

            if duration > 0:

                fps = (len(timestamps) - 1) / duration

    minimum_frames = max(
        1,
        int(MIN_STATE_DURATION * fps),
    )

    i = 0

    while i < len(states):

        j = i + 1

        while (
            j < len(states)
            and states[j] == states[i]
        ):
            j += 1

        run_length = j - i

        if run_length < minimum_frames:

            previous_state = (
                states[i - 1]
                if i > 0
                else None
            )

            next_state = (
                states[j]
                if j < len(states)
                else None
            )

            replacement = previous_state or next_state

            if replacement is not None:

                for k in range(i, j):
                    states[k] = replacement

        i = j

    for index, frame in enumerate(frames):

        frame.state = states[index]

    return frames


# ============================================================
# LOAD VIDEO
# ============================================================

def get_video_information(video_file):

    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video: {video_file}"
        )

    fps = cap.get(cv2.CAP_PROP_FPS)

    frame_count = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    width = int(
        cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    cap.release()

    if fps <= 0:
        fps = 30.0

    duration = frame_count / fps

    return fps, frame_count, width, height, duration


# ============================================================
# CREATE FACE LANDMARKER
# ============================================================

def create_face_landmarker():

    if not os.path.exists(MODEL_FILE):

        raise FileNotFoundError(
            f"Face Landmarker model not found: {MODEL_FILE}"
        )

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(
            model_asset_path=MODEL_FILE
        ),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )

    return FaceLandmarker.create_from_options(options)


# ============================================================
# PROCESS VIDEO
# ============================================================

def process_video(
    video_file,
    fps,
    width,
    height,
):
    """
    Process every video frame and collect:
    - face landmarks
    - iris position
    - head pose
    """

    frames = []

    landmarker = create_face_landmarker()

    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():

        landmarker.close()

        raise RuntimeError(
            f"Could not open video: {video_file}"
        )

    frame_index = 0

    try:

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            timestamp_ms = int(
                (frame_index / fps) * 1000
            )

            timestamp = frame_index / fps

            frame_result = FrameResult(
                timestamp=timestamp
            )

            # ------------------------------------------------
            # Convert OpenCV BGR → RGB
            # ------------------------------------------------

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            try:

                result = landmarker.detect_for_video(
                    mp_image,
                    timestamp_ms,
                )

            except Exception:

                result = None

            # ------------------------------------------------
            # Face
            # ------------------------------------------------

            if (
                result is not None
                and result.face_landmarks
            ):

                landmarks = np.array(
                    [
                        [
                            landmark.x,
                            landmark.y,
                            landmark.z,
                        ]
                        for landmark
                        in result.face_landmarks[0]
                    ],
                    dtype=np.float64,
                )

                frame_result.face_detected = True

                # --------------------------------------------
                # Iris & Blink
                # --------------------------------------------

                (
                    frame_result.left_x,
                    frame_result.left_y,
                ) = get_eye_gaze(
                    landmarks,
                    LEFT_EYE,
                    LEFT_IRIS,
                )

                (
                    frame_result.right_x,
                    frame_result.right_y,
                ) = get_eye_gaze(
                    landmarks,
                    RIGHT_EYE,
                    RIGHT_IRIS,
                )

                left_ear = calculate_ear(landmarks, LEFT_EYE)
                right_ear = calculate_ear(landmarks, RIGHT_EYE)
                avg_ear = (left_ear + right_ear) / 2.0
                frame_result.is_blinking = (avg_ear < 0.17)

                # --------------------------------------------
                # Head pose
                # --------------------------------------------

                (
                    frame_result.yaw,
                    frame_result.pitch,
                    frame_result.roll,
                ) = get_head_pose(
                    landmarks,
                    (width, height),
                )

            frames.append(frame_result)

            frame_index += 1

    finally:


        cap.release()
        landmarker.close()

    return frames


# ============================================================
# CALCULATE STATE DURATIONS
# ============================================================

def calculate_state_durations(frames):

    durations = Counter()

    if len(frames) < 2:
        return durations

    for i in range(len(frames) - 1):

        current = frames[i]
        next_frame = frames[i + 1]

        if (
            current.timestamp is None
            or next_frame.timestamp is None
        ):
            continue

        delta = (
            next_frame.timestamp
            - current.timestamp
        )

        if delta < 0:
            continue

        if delta > 0.5:
            delta = 1.0 / 30.0

        durations[current.state] += delta

    return durations


# ============================================================
# HEAD FORWARD ANALYSIS
# ============================================================

def calculate_head_position(frames, calibration):

    forward_time = 0.0
    total_pose_time = 0.0

    if len(frames) < 2:
        return {
            "forward_time": 0.0,
            "total_pose_time": 0.0,
            "percentage": 0.0,
            "longest_steady": 0.0,
            "face_detected": False,
        }

    baseline_yaw = calibration.get("yaw", 0.0)
    baseline_pitch = calibration.get("pitch", 0.0)
    baseline_roll = calibration.get("roll", 0.0)

    longest_steady = 0.0
    current_steady = 0.0

    for i in range(len(frames) - 1):

        frame = frames[i]
        next_frame = frames[i + 1]

        if frame.timestamp is None or next_frame.timestamp is None:
            continue

        delta = (
            next_frame.timestamp
            - frame.timestamp
        )

        if delta <= 0 or delta > 0.5:
            delta = 1.0 / 30.0

        if (
            frame.yaw is not None
            and frame.pitch is not None
            and frame.roll is not None
        ):

            total_pose_time += delta

            if (
                abs(
                    angle_difference(
                        frame.yaw,
                        baseline_yaw,
                    )
                ) <= YAW_TOLERANCE
                and abs(
                    angle_difference(
                        frame.pitch,
                        baseline_pitch,
                    )
                ) <= PITCH_TOLERANCE
                and abs(
                    angle_difference(
                        frame.roll,
                        baseline_roll,
                    )
                ) <= ROLL_TOLERANCE
            ):

                forward_time += delta
                current_steady += delta

                longest_steady = max(
                    longest_steady,
                    current_steady,
                )

            else:

                current_steady = 0.0

        else:

            current_steady = 0.0

    # If pose was detectable for less than 1.5 seconds, do not award high percentage
    if total_pose_time < 1.5:
        percentage = 0.0
    else:
        percentage = (
            forward_time / total_pose_time * 100.0
            if total_pose_time > 0
            else 0.0
        )

    return {
        "forward_time": forward_time,
        "total_pose_time": total_pose_time,
        "percentage": percentage,
        "longest_steady": longest_steady,
        "face_detected": total_pose_time >= 1.5,
    }


# ============================================================
# EYE CONTACT ANALYSIS
# ============================================================

def calculate_eye_contact(frames):

    if not frames:
        return {
            "contact_time": 0.0,
            "trackable_time": 0.0,
            "overall_percentage": 0.0,
            "contact_percentage": 0.0,
            "confidence": 0.0,
            "longest_streak": 0.0,
            "times_looked_away": 0,
            "face_detected": False,
        }

    contact_time = 0.0
    trackable_time = 0.0

    longest_streak = 0.0
    current_streak = 0.0

    times_looked_away = 0

    previous_contact = False

    for i in range(len(frames) - 1):

        frame = frames[i]
        next_frame = frames[i + 1]

        if (
            frame.timestamp is None
            or next_frame.timestamp is None
        ):
            continue

        delta = (
            next_frame.timestamp
            - frame.timestamp
        )

        if delta <= 0 or delta > 0.5:
            delta = 1.0 / 30.0

        if frame.face_detected:
            trackable_time += delta

        if frame.state == "camera_contact":

            contact_time += delta
            current_streak += delta

            longest_streak = max(
                longest_streak,
                current_streak,
            )

            previous_contact = True

        else:

            if previous_contact:
                times_looked_away += 1

            previous_contact = False
            current_streak = 0.0

    video_duration = frames[-1].timestamp if frames[-1].timestamp else 1.0

    overall_percentage = (
        contact_time
        / video_duration
        * 100.0
    )

    confidence = (
        trackable_time
        / video_duration
        * 100.0
    )

    # Guard against giving 100% eye contact when face was only visible for 1 frame
    if trackable_time < 1.5 or confidence < 15.0:
        contact_percentage = 0.0
        has_face = False
    else:
        contact_percentage = (
            contact_time
            / trackable_time
            * 100.0
            if trackable_time > 0
            else 0.0
        )
        has_face = True

    return {
        "contact_time": contact_time,
        "trackable_time": trackable_time,
        "overall_percentage": overall_percentage,
        "contact_percentage": contact_percentage,
        "confidence": confidence,
        "longest_streak": longest_streak,
        "times_looked_away": times_looked_away,
        "face_detected": has_face,
    }



# ============================================================
# PRINT CALIBRATION
# ============================================================

def print_calibration(calibration):

    print()
    print("========== CALIBRATION ==========")

    print(
        f"left_x: {calibration['left_x']:.3f}"
    )

    print(
        f"left_y: {calibration['left_y']:.3f}"
    )

    print(
        f"right_x: {calibration['right_x']:.3f}"
    )

    print(
        f"right_y: {calibration['right_y']:.3f}"
    )

    print(
        f"yaw: {calibration['yaw']:.3f}"
    )

    print(
        f"pitch: {calibration['pitch']:.3f}"
    )

    print(
        f"roll: {calibration['roll']:.3f}"
    )


# ============================================================
# HEAD POSE DIAGNOSTICS
# ============================================================

def print_head_diagnostics(frames, calibration):

    yaw_values = [
        frame.yaw
        for frame in frames
        if frame.yaw is not None
    ]

    pitch_values = [
        frame.pitch
        for frame in frames
        if frame.pitch is not None
    ]

    roll_values = [
        frame.roll
        for frame in frames
        if frame.roll is not None
    ]

    print()
    print("========== HEAD POSE DIAGNOSTICS ==========")

    if yaw_values:

        print(
            f"Raw yaw   — min: "
            f"{min(yaw_values):+.1f}°  "
            f"max: {max(yaw_values):+.1f}°  "
            f"median: {median(yaw_values):+.1f}°  "
            f"baseline: {calibration['yaw']}"
        )

    else:

        print("Raw yaw   — unavailable")

    if pitch_values:

        print(
            f"Raw pitch — min: "
            f"{min(pitch_values):+.1f}°  "
            f"max: {max(pitch_values):+.1f}°  "
            f"median: {median(pitch_values):+.1f}°  "
            f"baseline: {calibration['pitch']}"
        )

    else:

        print("Raw pitch — unavailable")

    if roll_values:

        print(
            f"Raw roll  — min: "
            f"{min(roll_values):+.1f}°  "
            f"max: {max(roll_values):+.1f}°  "
            f"median: {median(roll_values):+.1f}°  "
            f"baseline: {calibration['roll']}"
        )

    else:

        print("Raw roll  — unavailable")

    print(
        f"\nCalibration samples: "
        f"{calibration['calibration_samples']}/20"
    )

    print(
        f"Iris baseline — "
        f"L({calibration['left_x']:.3f}, "
        f"{calibration['left_y']:.3f}) "
        f"R({calibration['right_x']:.3f}, "
        f"{calibration['right_y']:.3f})"
    )

    if abs(calibration["pitch"]) > 45:

        print(
            "WARNING: Baseline pitch is large — "
            "user may have been looking up/down "
            "during calibration."
        )


# ============================================================
# STATE BREAKDOWN
# ============================================================

def print_state_breakdown(
    durations,
    total_duration,
    eye_report,
):

    print()
    print("========== GAZE STATE BREAKDOWN ==========")

    ordered_states = [
        "face_missing",
        "camera_contact",
        "head_turned",
        "looking_up",
        "looking_down",
        "looking_left",
        "looking_right",
    ]

    for state in ordered_states:

        duration = durations.get(
            state,
            0.0,
        )

        if duration <= 0:
            continue

        percentage = (
            duration / total_duration * 100.0
            if total_duration > 0
            else 0.0
        )

        print(
            f"  {state:<30}"
            f"{duration:5.1f}s"
            f" ({percentage:5.1f}%)"
        )

    print(
        f"  {'TOTAL':<30}"
        f"{total_duration:5.1f}s"
    )

    print(
        f"  Trackable: "
        f"{eye_report['trackable_time']:.1f}s "
        f"Confidence: "
        f"{eye_report['confidence']:.0f}%"
    )


# ============================================================
# VIDEO PRESENCE REPORT
# ============================================================

def print_video_presence_report(
    total_duration,
    eye_report,
    head_report,
    calibration,
):

    print()
    print(
        "=================================================="
    )

    print(
        "          VIDEO PRESENCE ANALYSIS"
    )

    print(
        "=================================================="
    )

    print()

    print(
        f"Video duration:  "
        f"{total_duration:.1f}s"
    )

    reliable = (
        calibration["calibration_samples"] >= 20
    )

    print(
        "Calibration:     "
        + (
            f"reliable "
            f"({calibration['calibration_samples']}/20 "
            f"neutral frames)"
            if reliable
            else
            f"limited "
            f"({calibration['calibration_samples']}/20 "
            f"neutral frames)"
        )
    )

    # --------------------------------------------------------
    # Eye contact
    # --------------------------------------------------------

    print()
    print("--- Camera Eye Contact ---")

    print(
        f"Contact time:      "
        f"{eye_report['contact_time']:.1f}s / "
        f"{eye_report['trackable_time']:.1f}s "
        f"trackable "
        f"({eye_report['contact_percentage']:.0f}%)"
    )

    print(
        f"Overall contact:   "
        f"{eye_report['overall_percentage']:.0f}% "
        f"of total video"
    )

    print(
        f"Confidence:        "
        f"{eye_report['confidence']:.0f}% "
        f"(trackable / total video)"
    )

    print(
        f"Face visible:      "
        f"{eye_report['confidence']:.0f}% "
        f"of video"
    )

    print(
        f"Longest streak:    "
        f"{eye_report['longest_streak']:.1f}s"
    )

    print(
        f"Times looked away: "
        f"{eye_report['times_looked_away']}"
    )

    if eye_report["contact_percentage"] >= 75:

        assessment = "good"

    elif eye_report["contact_percentage"] >= 50:

        assessment = "fair"

    else:

        assessment = "needs improvement"

    print(
        f"Assessment:        {assessment}"
    )

    # --------------------------------------------------------
    # Head position
    # --------------------------------------------------------

    print()
    print("--- Head Position ---")

    print(
        f"Facing forward:    "
        f"{head_report['forward_time']:.1f}s "
        f"({head_report['percentage']:.0f}%)"
    )

    print(
        f"Longest steady:    "
        f"{head_report['longest_steady']:.1f}s"
    )

    if head_report["percentage"] >= 75:

        print("Assessment:        good")

    elif head_report["percentage"] >= 50:

        print("Assessment:        fair")

    else:

        print("Assessment:        needs improvement")

    # --------------------------------------------------------
    # Coaching
    # --------------------------------------------------------

    print()
    print("--- Coaching Focus ---")

    if eye_report["contact_percentage"] >= 75:

        print(
            "  * Camera eye contact was generally strong; "
            "keep that steady presence."
        )

    else:

        print(
            "  * Try to maintain eye contact with the "
            "camera more consistently."
        )

    if head_report["percentage"] >= 75:

        print(
            "  * Your head position was steady and "
            "camera-facing for most of the response."
        )

    else:

        print(
            "  * Try to keep your head facing the camera "
            "more consistently."
        )


# ============================================================
# DEBUG SAMPLE
# ============================================================

def print_sample_data(frames):

    print()
    print(
        "========== SAMPLE HEAD / GAZE DATA =========="
    )

    sample_indices = [
        0,
        len(frames) // 4,
        len(frames) // 2,
        (len(frames) * 3) // 4,
        len(frames) - 1,
    ]

    used = set()

    for index in sample_indices:

        if index in used:
            continue

        if index < 0 or index >= len(frames):
            continue

        used.add(index)

        frame = frames[index]

        timestamp = (
            frame.timestamp
            if frame.timestamp is not None
            else 0.0
        )

        if not frame.face_detected:

            print(
                f"[{timestamp:5.1f}s] "
                f"Face not detected"
            )

            continue

        yaw = (
            f"{frame.yaw:+.1f}"
            if frame.yaw is not None
            else "N/A"
        )

        pitch = (
            f"{frame.pitch:+.1f}"
            if frame.pitch is not None
            else "N/A"
        )

        roll = (
            f"{frame.roll:+.1f}"
            if frame.roll is not None
            else "N/A"
        )

        left = (
            f"({frame.left_x:.3f}, "
            f"{frame.left_y:.3f})"
            if frame.left_x is not None
            and frame.left_y is not None
            else "N/A"
        )

        right = (
            f"({frame.right_x:.3f}, "
            f"{frame.right_y:.3f})"
            if frame.right_x is not None
            and frame.right_y is not None
            else "N/A"
        )

        print(
            f"[{timestamp:5.1f}s] "
            f"state={frame.state:<16} "
            f"yaw={yaw:>7} "
            f"pitch={pitch:>7} "
            f"roll={roll:>7} "
            f"L={left} "
            f"R={right}"
        )


# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================

def analyze_video(video_file=None):

    if video_file is None:
        video_file = VIDEO_FILE

    if not os.path.exists(video_file):

        print(
            f"Video file not found: {video_file}"
        )

        return None

    # --------------------------------------------------------
    # Video information
    # --------------------------------------------------------

    (
        fps,
        frame_count,
        width,
        height,
        duration,
    ) = get_video_information(
        video_file
    )

    # --------------------------------------------------------
    # Process frames
    # --------------------------------------------------------

    frames = process_video(
        video_file,
        fps,
        width,
        height,
    )

    if not frames:

        return None

    # --------------------------------------------------------
    # Calibration
    # --------------------------------------------------------

    calibration = calibrate(frames)

    # --------------------------------------------------------
    # Classify frames
    # --------------------------------------------------------

    for frame in frames:

        frame.state = classify_face(
            frame,
            calibration,
        )

    # --------------------------------------------------------
    # Smooth state changes
    # --------------------------------------------------------

    frames = smooth_states(frames)

    # --------------------------------------------------------
    # State durations
    # --------------------------------------------------------

    durations = calculate_state_durations(
        frames
    )

    # --------------------------------------------------------
    # Eye contact
    # --------------------------------------------------------

    eye_report = calculate_eye_contact(
        frames
    )

    # --------------------------------------------------------
    # Head position
    # --------------------------------------------------------

    head_report = calculate_head_position(
        frames,
        calibration,
    )

    # --------------------------------------------------------
    # Return report
    # --------------------------------------------------------

    return {
        "duration": duration,

        "calibration": calibration,

        "eye_contact": eye_report,

        "head_position": head_report,

        "state_durations": dict(durations),

        "frames": frames,
    }


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    analyze_video()