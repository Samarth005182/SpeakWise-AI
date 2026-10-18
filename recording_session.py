import logging
import threading
import time

import audio
import video_capture


logger = logging.getLogger(__name__)


def record_session(
    duration,
    audio_path,
    video_path,
    *,
    stop_event=None,
    frame_callback=None,
    show_window=True,
    on_tick=None,
    ready_timeout=15.0,
):
    stop_event = stop_event or threading.Event()
    start_event = threading.Event()
    audio_ready = threading.Event()
    video_ready = threading.Event()
    status = {}
    timing = {}

    def audio_worker():
        try:
            audio.record_audio(duration, start_event, audio_ready, status, audio_path, stop_event)
        except Exception as error:
            status['audio_error'] = str(error)
            logger.exception('Audio recording worker failed')
        finally:
            audio_ready.set()

    def video_worker():
        try:
            video_capture.record_video(
                duration,
                start_event,
                video_ready,
                status,
                timing,
                video_path,
                frame_callback,
                show_window,
                stop_event,
            )
        except Exception as error:
            status['video_error'] = str(error)
            status['video_analysis_eligible'] = False
            logger.exception('Video recording worker failed')
        finally:
            video_ready.set()

    audio_thread = threading.Thread(target=audio_worker, name='speakwise-audio', daemon=True)
    video_thread = threading.Thread(target=video_worker, name='speakwise-video', daemon=True)
    audio_thread.start()
    video_thread.start()

    ready_deadline = time.monotonic() + ready_timeout
    ready_results = []
    for ready_event in (audio_ready, video_ready):
        ready_results.append(ready_event.wait(max(0.0, ready_deadline - time.monotonic())))

    if not all(ready_results):
        if not ready_results[0]:
            status['audio_error'] = 'Microphone setup did not finish before the readiness timeout.'
        if not ready_results[1]:
            status['video_error'] = 'Webcam setup did not finish before the readiness timeout.'
            status['video_analysis_eligible'] = False
        status['recording_started'] = False
        stop_event.set()
        start_event.set()
        audio_thread.join(timeout=2.0)
        video_thread.join(timeout=2.0)
        return status, timing

    if status.get('audio_error'):
        status['recording_started'] = False
        stop_event.set()
        start_event.set()
        audio_thread.join(timeout=2.0)
        video_thread.join(timeout=2.0)
        return status, timing

    timing['start_time'] = time.perf_counter()
    timing['deadline'] = timing['start_time'] + duration
    status['recording_started'] = True
    start_event.set()

    while not stop_event.is_set():
        remaining = timing['deadline'] - time.perf_counter()
        if remaining <= 0:
            break
        if on_tick:
            try:
                on_tick(remaining, duration)
            except Exception:
                logger.exception('Recording timer callback failed')
        stop_event.wait(min(0.08, remaining))

    stop_event.set()
    audio_thread.join()
    video_thread.join()
    return status, timing
