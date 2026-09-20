import time

import cv2 as cv


def record_video(duration, start_event, ready_event, status, timing, output_path="myrecording.avi"):
    """Prepare the camera, then record against the shared recording deadline."""
    cap = cv.VideoCapture(0)

    if not cap.isOpened():
        status["video_error"] = "Cannot open camera"
        ready_event.set()
        return

    width = 640
    height = 480
    declared_fps = 20.0
    cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)

    # Query the camera's actual FPS capability; fall back to the declared
    # value when the driver does not report one.
    actual_fps = cap.get(cv.CAP_PROP_FPS)
    if actual_fps <= 0:
        actual_fps = declared_fps

    out = cv.VideoWriter(
        output_path,
        cv.VideoWriter_fourcc(*"XVID"),
        actual_fps,
        (width, height),
    )

    if not out.isOpened():
        cap.release()
        status["video_error"] = "Cannot create video output file"
        ready_event.set()
        return

    # Both devices initialize before main.py releases this shared start barrier.
    ready_event.set()
    start_event.wait()
    print("Camera recording started...")

    frame_count = 0
    try:
        while time.perf_counter() < timing["deadline"]:
            ret, frame = cap.read()

            if not ret:
                print("Can't receive frame.")
                break

            frame = cv.flip(frame, 1)
            out.write(frame)
            cv.imshow("SpeakWise Camera", frame)
            frame_count += 1

            if cv.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        out.release()
        cv.destroyAllWindows()

    timing["video_frames"] = frame_count
    timing["video_actual_fps"] = actual_fps
    print("Camera recording finished!")

