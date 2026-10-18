import time
import os
import logging
import cv2 as cv

logger = logging.getLogger(__name__)


def _open_camera():
    try:
        cap = cv.VideoCapture(0, cv.CAP_DSHOW)
        if cap is not None and cap.isOpened():
            ret, test_frame = cap.read()
            if ret and test_frame is not None:
                return cap
            cap.release()
    except Exception:
        logger.exception("Could not open webcam with DirectShow")

    try:
        cap = cv.VideoCapture(0)
        if cap is not None and cap.isOpened():
            ret, test_frame = cap.read()
            if ret and test_frame is not None:
                return cap
            cap.release()
    except Exception:
        logger.exception("Could not open webcam with default backend")

    return None


def _create_video_writer(output_path, fps, width, height):
    codecs = ["MJPG", "XVID", "mp4v", "DIVX"]
    for codec in codecs:
        try:
            fourcc = cv.VideoWriter_fourcc(*codec)
            out = cv.VideoWriter(output_path, fourcc, fps, (width, height))
            if out is not None and out.isOpened():
                return out
        except Exception:
            logger.exception("Video codec %s could not be initialized", codec)
    return None


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
    width = 640
    height = 480
    declared_fps = 24.0
    cap = None
    out = None
    frame_count = 0
    actual_fps = declared_fps

    try:
        cap = _open_camera()
        status["camera_available"] = cap is not None
        if cap is None:
            status["video_error"] = "Webcam could not be opened; no placeholder video was created."
            status["video_analysis_eligible"] = False
            ready_event.set()
            return

        cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
        camera_fps = cap.get(cv.CAP_PROP_FPS)
        if 0 < camera_fps <= 60:
            actual_fps = camera_fps

        out = _create_video_writer(output_path, actual_fps, width, height)
        status["video_writer_available"] = out is not None
        if out is None:
            status["video_error"] = "Could not create a video file with an available codec."
            status["video_analysis_eligible"] = False
            ready_event.set()
            return

        status["video_analysis_eligible"] = True
        ready_event.set()
        start_event.wait()

        frame_interval = 1.0 / max(actual_fps, 20.0)
        while not (stop_event and stop_event.is_set()):
            if time.perf_counter() >= timing.get("deadline", float("inf")):
                break

            loop_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret or frame is None:
                status["video_error"] = "Webcam stopped producing frames during recording."
                status["video_analysis_eligible"] = False
                logger.error(status["video_error"])
                break

            frame = cv.flip(frame, 1)
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv.resize(frame, (width, height))

            out.write(frame)
            frame_count += 1

            if frame_callback:
                try:
                    frame_callback(frame)
                except Exception:
                    logger.exception("Video frame callback failed")

            if show_window:
                cv.imshow("SpeakWise Camera", frame)
                key = cv.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    if stop_event:
                        stop_event.set()
                    break
            else:
                sleep_time = frame_interval - (time.perf_counter() - loop_start)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    except Exception as error:
        status["video_error"] = str(error)
        status["video_analysis_eligible"] = False
        logger.exception("Video recording failed")
    finally:
        ready_event.set()
        if cap is not None:
            try:
                cap.release()
            except Exception:
                logger.exception("Failed to release webcam")
        if out is not None:
            try:
                out.release()
            except Exception:
                logger.exception("Failed to release video writer")
        if show_window:
            try:
                cv.destroyAllWindows()
            except Exception:
                logger.exception("Failed to close camera window")

    timing["video_frames"] = frame_count
    timing["video_actual_fps"] = actual_fps
    timing["video_real_frames"] = frame_count
    status["video_frames"] = frame_count
    status["video_real_frames"] = frame_count
    status["video_recording_valid"] = (
        frame_count > 0
        and os.path.exists(output_path)
        and os.path.getsize(output_path) > 0
    )
    status["video_analysis_eligible"] = bool(
        status.get("video_analysis_eligible") and status["video_recording_valid"]
    )
    if frame_count == 0 and not status.get("video_error"):
        status["video_error"] = "No webcam frames were recorded."
