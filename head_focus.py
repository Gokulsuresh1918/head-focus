"""Head-tracked monitor focus switcher for Windows.

Tracks head yaw with a webcam and gives keyboard focus to the topmost window
on the monitor you are looking at. The mouse cursor is never moved.

Run:   python head_focus.py
       python head_focus.py --settings
       python settings_ui.py

Hotkeys: Ctrl+Alt+H pause, Ctrl+Alt+C recenter, Ctrl+Alt+S settings
Debug window (if enabled): q / Esc quit, c recenter
"""

from __future__ import annotations

import argparse
import ctypes
import math
import os
import subprocess
import sys
import time
import urllib.request
from ctypes import wintypes
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
import pywintypes
import win32api
import win32con
import win32gui
import win32process
from screeninfo import get_monitors

from config import USER_CONFIG_PATH, AppConfig, ensure_user_config
# Camera internals (not exposed in settings UI)
MIN_FRAME_MEAN = 8.0
CAMERA_WARMUP_FRAMES = 30

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_WINDOW = "Head Focus (debug)"


def debug_window_closed() -> bool:
    """True if the user closed the OpenCV window with the X button."""
    try:
        return cv2.getWindowProperty(DEBUG_WINDOW, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def handle_debug_keys(key: int, tracker: HeadTracker) -> str:
    """Return 'quit', 'recenter', or '' after a debug-window key press."""
    if key in (ord("q"), 27):
        return "quit"
    if key == ord("c"):
        tracker.recenter()
        return "recenter"
    return ""


# ----------------------------------------------------------------------------
# 1. Vision module: head tracking
# ----------------------------------------------------------------------------
class HeadTracker:
    """Reads webcam frames and estimates head yaw from Face Mesh landmarks."""

    _LANDMARK_IDS = (1, 152, 33, 263, 61, 291)
    _MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),
        (0.0, 330.0, 65.0),
        (-225.0, -170.0, 135.0),
        (225.0, -170.0, 135.0),
        (-150.0, 150.0, 125.0),
        (150.0, 150.0, 125.0),
    ], dtype=np.float64)

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.offset_deg = cfg.yaw_offset_deg
        self._smoothing = cfg.smoothing
        self._smoothed_yaw = None
        self._last_timestamp_ms = 0
        self._cap, self._camera_label = self._open_camera(cfg.camera_index)
        self._black_frames = 0

        with open(self._ensure_model(), "rb") as f:
            model = f.read()
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=model),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    @classmethod
    def _open_camera(cls, preferred_index):
        indices = [preferred_index] + [i for i in range(4) if i != preferred_index]
        last_error = None
        configs = (
            (1920, 1080, False),
            (640, 480, False),
            (640, 480, True),
            (1280, 720, True),
        )
        for index in indices:
            tries = configs if index == preferred_index else ((640, 480, False), (640, 480, True))
            for width, height, use_mjpg in tries:
                cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    last_error = f"index {index} did not open"
                    break
                if use_mjpg:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                mean = cls._warmup_mean(cap, frames=15)
                if mean >= MIN_FRAME_MEAN:
                    mode = "MJPG" if use_mjpg else "YUY2"
                    return cap, f"index {index} {width}x{height} {mode} (brightness {mean:.0f})"
                cap.release()
                last_error = f"index {index} {width}x{height} black (mean {mean:.1f})"

        cap = cv2.VideoCapture(preferred_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera {preferred_index}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print(
            "WARNING: Webcam opened but frames look black. "
            f"({last_error}). Run: python check_camera.py"
        )
        try:
            os.startfile("ms-settings:privacy-webcam")
        except OSError:
            pass
        return cap, f"index {preferred_index} (black feed - check camera access)"

    @staticmethod
    def _warmup_mean(cap, frames=None):
        frame = None
        for _ in range(frames or CAMERA_WARMUP_FRAMES):
            ok, frame = cap.read()
            if not ok:
                return 0.0
        return float(frame.mean()) if frame is not None else 0.0

    @staticmethod
    def _ensure_model():
        if not os.path.exists(MODEL_PATH):
            print("Downloading face landmark model...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        return MODEL_PATH

    def read(self):
        ok, frame = self._cap.read()
        if not ok:
            return None, None
        if frame.mean() < MIN_FRAME_MEAN:
            self._black_frames += 1

        rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = max(int(time.monotonic() * 1000), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        result = self._landmarker.detect_for_video(image, timestamp_ms)

        if not result.face_landmarks:
            self._smoothed_yaw = None
            return frame, None

        raw_yaw = self.estimate_yaw(result.face_landmarks[0], frame.shape[1], frame.shape[0])
        if raw_yaw is None:
            return frame, None
        if self._smoothed_yaw is None:
            self._smoothed_yaw = raw_yaw
        else:
            self._smoothed_yaw += self._smoothing * (raw_yaw - self._smoothed_yaw)
        return frame, self._smoothed_yaw - self.offset_deg

    @classmethod
    def estimate_yaw(cls, landmarks, width, height):
        image_points = np.array(
            [(landmarks[i].x * width, landmarks[i].y * height) for i in cls._LANDMARK_IDS],
            dtype=np.float64,
        )
        camera_matrix = np.array([
            (width, 0.0, width / 2.0),
            (0.0, width, height / 2.0),
            (0.0, 0.0, 1.0),
        ], dtype=np.float64)
        ok, rvec, _ = cv2.solvePnP(
            cls._MODEL_POINTS, image_points, camera_matrix, np.zeros(4), flags=cv2.SOLVEPNP_SQPNP
        )
        if not ok:
            return None
        rotation, _ = cv2.Rodrigues(rvec)
        return math.degrees(math.atan2(rotation[0, 2], rotation[2, 2]))

    def recenter(self):
        if self._smoothed_yaw is not None:
            self.offset_deg = self._smoothed_yaw
            self.cfg.yaw_offset_deg = self.offset_deg
            self.cfg.save_yaw_offset()
            print(f"Recentered: yaw_offset_deg = {self.offset_deg:.1f} (saved to config.json)")

    def close(self):
        self._cap.release()
        self._landmarker.close()


# ----------------------------------------------------------------------------
# 2. Screen mapping
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Screen:
    number: int
    name: str
    x: int
    y: int
    width: int
    height: int

    def contains(self, px, py):
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height


class ScreenMapper:
    LEFT, CENTER, RIGHT = "LEFT", "CENTER", "RIGHT"

    def __init__(self, cfg: AppConfig):
        self.threshold_deg = cfg.yaw_threshold_deg
        self.hysteresis_deg = cfg.hysteresis_deg
        self.dwell_seconds = cfg.dwell_seconds
        self.zone = None
        self._zone_since = 0.0
        monitors = sorted(get_monitors(), key=lambda m: (m.x, m.y))
        self.screens = [
            Screen(i, m.name or f"Monitor {i}", m.x, m.y, m.width, m.height)
            for i, m in enumerate(monitors, start=1)
        ]

    def _classify(self, yaw):
        left_limit = -self.threshold_deg + (self.hysteresis_deg if self.zone == self.LEFT else 0.0)
        right_limit = self.threshold_deg - (self.hysteresis_deg if self.zone == self.RIGHT else 0.0)
        if yaw <= left_limit:
            return self.LEFT
        if yaw >= right_limit:
            return self.RIGHT
        return self.CENTER

    def _screen_for(self, zone):
        if len(self.screens) < 2:
            return None
        if zone == self.LEFT:
            return self.screens[0]
        if zone == self.RIGHT:
            return self.screens[-1]
        if len(self.screens) % 2 == 1:
            return self.screens[len(self.screens) // 2]
        return None

    def update(self, yaw, now):
        if yaw is None:
            self.zone = None
            return None
        zone = self._classify(yaw)
        if zone != self.zone:
            self.zone = zone
            self._zone_since = now
        if now - self._zone_since < self.dwell_seconds:
            return None
        return self._screen_for(zone)


# ----------------------------------------------------------------------------
# 3. Focus switching
# ----------------------------------------------------------------------------
class FocusSwitcher:
    _SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}
    _DWMWA_CLOAKED = 14

    def __init__(self, verbose: bool = False):
        self._own_pid = os.getpid()
        self._verbose = verbose

    def focus_screen(self, screen):
        if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0:
            return False
        foreground = win32gui.GetForegroundWindow()
        if foreground and self._is_on_screen(foreground, screen):
            return True
        hwnd = self._top_window_on(screen)
        if hwnd and not self._force_foreground(hwnd) and self._verbose:
            print(
                f"Could not focus '{win32gui.GetWindowText(hwnd)}' "
                "(is the active window running as administrator?)"
            )
        return True

    def _top_window_on(self, screen):
        candidates = []

        def visit(hwnd, _):
            if self._is_candidate(hwnd) and self._is_on_screen(hwnd, screen):
                candidates.append(hwnd)
                return False
            return True

        try:
            win32gui.EnumWindows(visit, None)
        except pywintypes.error:
            pass
        return candidates[0] if candidates else None

    def _is_candidate(self, hwnd):
        if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            return False
        if not win32gui.GetWindowText(hwnd):
            return False
        if win32gui.GetClassName(hwnd) in self._SHELL_CLASSES:
            return False
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex_style & (win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE):
            return False
        if win32process.GetWindowThreadProcessId(hwnd)[1] == self._own_pid:
            return False
        return not self._is_cloaked(hwnd)

    @classmethod
    def _is_cloaked(cls, hwnd):
        cloaked = wintypes.DWORD(0)
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd), wintypes.DWORD(cls._DWMWA_CLOAKED),
            ctypes.byref(cloaked), ctypes.sizeof(cloaked),
        )
        return cloaked.value != 0

    @staticmethod
    def _is_on_screen(hwnd, screen):
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return screen.contains((left + right) // 2, (top + bottom) // 2)

    @classmethod
    def _force_foreground(cls, hwnd):
        this_thread = win32api.GetCurrentThreadId()
        foreground = win32gui.GetForegroundWindow()
        fg_thread = win32process.GetWindowThreadProcessId(foreground)[0] if foreground else 0
        attached = False
        if fg_thread and fg_thread != this_thread:
            try:
                win32process.AttachThreadInput(this_thread, fg_thread, True)
                attached = True
            except pywintypes.error:
                pass
        try:
            cls._set_foreground(hwnd)
        finally:
            if attached:
                win32process.AttachThreadInput(this_thread, fg_thread, False)
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        for _ in range(2):
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        cls._set_foreground(hwnd)
        return win32gui.GetForegroundWindow() == hwnd

    @staticmethod
    def _set_foreground(hwnd):
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        except pywintypes.error:
            pass


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass


def draw_overlay(frame, yaw, mapper, target, cfg: AppConfig, black_frames=0):
    view = cv2.flip(frame, 1)
    h, w = view.shape[:2]
    if w != 640:
        view = cv2.resize(view, (640, max(480, int(h * 640 / w))))
    if view.mean() < MIN_FRAME_MEAN or black_frames > cfg.target_fps * 2:
        lines = [
            "Camera feed is black",
            "Run: python check_camera.py",
            "Close eViacam / other camera apps",
        ]
    elif yaw is None:
        lines = ["No face detected"]
    else:
        direction = "right" if yaw > 0 else "left"
        lines = [f"Yaw: {yaw:+.1f} deg ({direction})", f"Zone: {mapper.zone}"]
    if target is not None:
        lines.append(f"Target: monitor {target.number} ({target.name})")
    else:
        lines.append("Target: none (deadzone)")
    for i, line in enumerate(lines):
        position = (10, 30 + 30 * i)
        cv2.putText(view, line, position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(view, line, position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return view


def open_settings_window():
    subprocess.Popen(
        [sys.executable, os.path.join(APP_DIR, "settings_ui.py")],
        cwd=APP_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )


def parse_args():
    p = argparse.ArgumentParser(description="Head Focus - head-tracked monitor focus for Windows")
    p.add_argument("--settings", action="store_true", help="Open the settings window and exit")
    p.add_argument("--console", action="store_true", help="Run in the terminal without the dashboard window")
    p.add_argument("--config", metavar="PATH", help="Path to config.json (default: beside this script)")
    p.add_argument("--no-tray", action="store_true", help="Hide system tray icon")
    return p.parse_args()


def run_console(cfg: AppConfig) -> None:
    """Terminal-only mode (tray + hotkeys, optional debug preview)."""
    from tracking_engine import TrackingSession

    session = TrackingSession(cfg)
    if not session.start():
        sys.exit(1)
    print("Head Focus running. Ctrl+C to stop.")
    try:
        while session._thread and session._thread.is_alive():
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    session.stop()


def main():
    args = parse_args()
    ensure_user_config()
    if args.settings:
        from settings_ui import SettingsApp
        SettingsApp().run()
        return

    if not args.console:
        from dashboard import DashboardApp
        DashboardApp().run()
        return

    cfg_path = args.config or USER_CONFIG_PATH
    cfg = AppConfig.load(cfg_path)
    if args.no_tray:
        cfg.show_tray_icon = False
    run_console(cfg)


if __name__ == "__main__":
    main()
