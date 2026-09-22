import time
import numpy as np
import cv2 as cv


def _open_camera():
    """Directly open camera with DirectShow backend for instant startup on Windows."""
    try:
        cap = cv.VideoCapture(0, cv.CAP_DSHOW)
        if cap is not None and cap.isOpened():
            ret, test_frame = cap.read()
            if ret and test_frame is not None:
                return cap
            cap.release()
    except Exception:
        pass

    try:
        cap = cv.VideoCapture(0)
        if cap is not None and cap.isOpened():
            ret, test_frame = cap.read()
            if ret and test_frame is not None:
                return cap
            cap.release()
    except Exception:
        pass

    return None


def _create_video_writer(output_path, fps, width, height):
    """Try multiple codecs to create a valid video writer."""
    codecs = ["MJPG", "XVID", "mp4v", "DIVX"]
    for codec in codecs:
        try:
            fourcc = cv.VideoWriter_fourcc(*codec)
            out = cv.VideoWriter(output_path, fourcc, fps, (width, height))
            if out is not None and out.isOpened():
                return out
        except Exception:
            pass
    return None


def _generate_fallback_frame(width, height, frame_count, topic_text="SpeakWise AI"):
    """Generate an animated placeholder frame if no physical webcam is accessible."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (18, 12, 9)  # Dark navy

    center_x, center_y = width // 2, height // 2
    pulse = int(15 * np.sin(frame_count * 0.15))
    radius = max(30, 70 + pulse)
    cv.circle(img, (center_x, center_y - 20), radius, (246, 130, 59), 2)  # Blue ring
    cv.circle(img, (center_x, center_y - 20), 40, (70, 30, 20), -1)

    cv.putText(img, "LIVE AUDIO RECORDING", (center_x - 140, center_y + 80), cv.FONT_HERSHEY_SIMPLEX, 0.7, (248, 250, 252), 2)
    cv.putText(img, "Camera feed standby / Voice active", (center_x - 130, center_y + 115), cv.FONT_HERSHEY_SIMPLEX, 0.5, (148, 163, 184), 1)
    return img


def record_video(
    duration,
    start_event,
    ready_event,
    status,
    timing,
    output_path="myrecording.avi",
    frame_callback=None,
    show_window=True,
    stop_event=None,
):
    """Prepare the camera, then record against the shared recording deadline."""
    width = 640
    height = 480
    declared_fps = 24.0

    cap = _open_camera()
    using_fallback_camera = False

    if cap is None:
        print("[Video Notice] Physical camera not opened. Running with animated audio-reactive stream.")
        using_fallback_camera = True
        actual_fps = declared_fps
    else:
        cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
        actual_fps = cap.get(cv.CAP_PROP_FPS)
        if actual_fps <= 0 or actual_fps > 60:
            actual_fps = declared_fps

    out = _create_video_writer(output_path, actual_fps, width, height)

    # Both devices initialize before releasing the shared start barrier.
    ready_event.set()
    start_event.wait(timeout=5.0)
    print("Camera recording started...")

    frame_count = 0
    frame_interval = 1.0 / max(actual_fps, 20.0)

    try:
        while True:
            # Check deadline or explicit stop event
            if stop_event and stop_event.is_set():
                break
            if time.perf_counter() >= timing.get("deadline", float("inf")):
                break

            loop_start = time.perf_counter()

            if not using_fallback_camera and cap is not None:
                ret, frame = cap.read()
                if not ret or frame is None:
                    frame = _generate_fallback_frame(width, height, frame_count)
                else:
                    frame = cv.flip(frame, 1)
                    if frame.shape[1] != width or frame.shape[0] != height:
                        frame = cv.resize(frame, (width, height))
            else:
                frame = _generate_fallback_frame(width, height, frame_count)

            if out is not None and out.isOpened():
                out.write(frame)
            frame_count += 1

            if frame_callback:
                try:
                    frame_callback(frame)
                except Exception:
                    pass

            if show_window:
                cv.imshow("SpeakWise Camera", frame)
                key = cv.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    if stop_event:
                        stop_event.set()
                    break
            else:
                elapsed = time.perf_counter() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        if out is not None:
            try:
                out.release()
            except Exception:
                pass
        if show_window:
            try:
                cv.destroyAllWindows()
            except Exception:
                pass

    timing["video_frames"] = frame_count
    timing["video_actual_fps"] = actual_fps
    print(f"Camera recording finished! Total frames: {frame_count}")
