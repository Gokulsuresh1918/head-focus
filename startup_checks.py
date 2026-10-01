"""Startup helpers: camera probe and conflicting apps."""

from __future__ import annotations

import os
import subprocess
import sys

import cv2
import numpy as np

from config import AppConfig

MIN_FRAME_MEAN = 8.0
CAMERA_ATTEMPTS = (
    (1920, 1080, False),
    (640, 480, False),
    (640, 480, True),
)


def is_process_running(image_name: str) -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return image_name.lower() in out.stdout.lower() and "No tasks" not in out.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def warn_eviacam_if_needed(cfg: AppConfig) -> None:
    if not cfg.warn_if_eviacam_running:
        return
    if is_process_running("eviacam.exe"):
        print(
            "WARNING: eViacam is running and often blocks the webcam for other apps.\n"
            "         Quit eViacam from the system tray before using Head Focus."
        )


def probe_camera(index: int) -> tuple[float, str | None]:
    """Return (mean brightness, mode label) or (0, None) if all attempts fail."""
    for width, height, use_mjpg in CAMERA_ATTEMPTS:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            continue
        if use_mjpg:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        frame = None
        for _ in range(25):
            ok, frame = cap.read()
            if not ok:
                break
        cap.release()
        if frame is None:
            continue
        mean = float(frame.mean())
        if mean >= MIN_FRAME_MEAN:
            mode = "MJPG" if use_mjpg else "YUY2"
            return mean, f"{mode} {width}x{height}"
    return 0.0, None


def check_camera_on_start(cfg: AppConfig) -> bool:
    if not cfg.check_camera_on_start:
        return True
    mean, mode = probe_camera(cfg.camera_index)
    if mode:
        print(f"Camera check OK ({mode}, brightness {mean:.0f}).")
        return True
    print(
        "Camera check failed: feed looks black or unavailable.\n"
        "  - Quit eViacam / Zoom / Teams\n"
        "  - Allow camera for python.exe in Settings > Privacy > Camera\n"
        "  - Run: python check_camera.py"
    )
    try:
        os.startfile("ms-settings:privacy-webcam")
    except OSError:
        pass
    if cfg.exit_on_black_camera:
        return False
    return True


def run_check_camera_script() -> int:
    """Invoke check_camera.py (same process folder)."""
    script = os.path.join(os.path.dirname(__file__), "check_camera.py")
    return subprocess.call([sys.executable, script])
