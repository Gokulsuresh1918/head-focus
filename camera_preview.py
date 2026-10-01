"""Live webcam preview for in-app UI (no disk capture)."""

from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from startup_checks import CAMERA_ATTEMPTS, MIN_FRAME_MEAN


class LiveCameraPreview:
    """Reads frames from the webcam until stop(); latest frame is mirrored RGB."""

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_rgb: np.ndarray | None = None
        self.mode_label: str | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, camera_index: int) -> tuple[bool, str | None]:
        if self.running:
            return True, self.mode_label
        self.stop()
        cap, mode = _open_camera(camera_index)
        if cap is None:
            return False, None
        self._cap = cap
        self.mode_label = mode
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="LiveCameraPreview", daemon=True)
        self._thread.start()
        return True, mode

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        if self._cap is not None:
            try:
                self._cap.release()
            except cv2.error:
                pass
            self._cap = None
        with self._lock:
            self._latest_rgb = None
        self.mode_label = None

    def latest_rgb(self) -> np.ndarray | None:
        with self._lock:
            if self._latest_rgb is None:
                return None
            return self._latest_rgb

    def _loop(self) -> None:
        while not self._stop.is_set() and self._cap is not None:
            ok, frame = self._cap.read()
            if ok and frame is not None and float(frame.mean()) >= MIN_FRAME_MEAN:
                rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                with self._lock:
                    self._latest_rgb = rgb
            time.sleep(0.033)


def _open_camera(index: int) -> tuple[cv2.VideoCapture | None, str | None]:
    for width, height, use_mjpg in CAMERA_ATTEMPTS:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            continue
        if use_mjpg:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        frame = None
        for _ in range(20):
            ok, frame = cap.read()
            if not ok:
                break
        if frame is None:
            cap.release()
            continue
        if float(frame.mean()) >= MIN_FRAME_MEAN:
            mode = "MJPG" if use_mjpg else "YUY2"
            return cap, f"{mode} {width}x{height}"
        cap.release()
    return None, None
