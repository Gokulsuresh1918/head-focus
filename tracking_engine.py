"""Background head-tracking session (thread-safe controls)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np

from config import AppConfig, USER_CONFIG_PATH
from head_focus import (
    DEBUG_WINDOW,
    FocusSwitcher,
    HeadTracker,
    ScreenMapper,
    debug_window_closed,
    draw_overlay,
    enable_dpi_awareness,
    handle_debug_keys,
    open_settings_window,
)
from action_feedback import ActionNotice
from hotkeys import HotkeyService
from notifications import notify
from startup_checks import check_camera_on_start
from tray_ui import TrayController


@dataclass
class TrackingStatus:
    running: bool = False
    paused: bool = False
    yaw: float | None = None
    zone: str | None = None
    target_monitor: str | None = None
    camera: str = ""
    message: str = "Ready"


class TrackingSession:
    def __init__(
        self,
        cfg: AppConfig,
        on_status: Callable[[TrackingStatus], None] | None = None,
        on_preview: Callable[[np.ndarray], None] | None = None,
        on_action: Callable[[ActionNotice], None] | None = None,
    ):
        self.cfg = cfg
        self._on_status = on_status
        self._on_preview = on_preview
        self._on_action = on_action
        self.status = TrackingStatus()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._starting = False
        self._hotkeys: HotkeyService | None = None
        self._tray: TrayController | None = None
        self._tracker: HeadTracker | None = None

    def start(self) -> bool:
        """Start tracking on a background thread (does not block the UI)."""
        if self._starting or (self.status.running and self._thread and self._thread.is_alive()):
            return True

        enable_dpi_awareness()
        self._starting = True
        self._stop_event.clear()
        self.status.running = True
        self.status.paused = False
        self.status.message = "Starting camera..."
        self._emit()

        self._hotkeys = HotkeyService(
            on_toggle=self.toggle_pause,
            on_recenter=self.recenter,
            on_settings=self._open_settings,
            enable_toggle=self.cfg.hotkey_toggle_pause,
            enable_recenter=self.cfg.hotkey_recenter,
            enable_settings=self.cfg.hotkey_open_settings,
        )
        self._hotkeys.start()

        if self.cfg.show_tray_icon:
            self._tray = TrayController(
                get_paused=lambda: self.status.paused,
                on_toggle_pause=self.toggle_pause,
                on_recenter=self.recenter,
                on_open_settings=self._open_settings,
                on_quit=self.stop,
            )
            self._tray.start()

        self._thread = threading.Thread(target=self._boot_and_run, name="TrackingLoop", daemon=True)
        self._thread.start()
        return True

    def _shutdown_services(self) -> None:
        if self._hotkeys:
            self._hotkeys.stop()
            self._hotkeys = None
        if self._tray:
            self._tray.stop()
            self._tray = None

    def stop(self) -> None:
        if not self.status.running and not self._thread and not self._starting:
            return
        self._stop_event.set()
        self.status.running = False
        self.status.message = "Stopped"
        self._emit()
        self._shutdown_services()
        if self._thread:
            self._thread.join(timeout=8.0)
            self._thread = None
        self._starting = False
        cv2.destroyAllWindows()
        self._announce("stop")

    def _announce(self, key: str) -> None:
        notice = ActionNotice.from_key(key)
        if self._on_action:
            self._on_action(notice)
        notify(notice.title, notice.toast_body(), self.cfg.show_toast_notifications)

    def toggle_pause(self) -> None:
        if not self.status.running:
            return
        self.status.paused = not self.status.paused
        if self.status.paused:
            self.status.message = "Paused"
            self._announce("pause")
        else:
            self.status.message = "Tracking"
            self._announce("resume")
        if self._tray:
            self._tray.refresh()
        self._emit()

    def recenter(self) -> None:
        if not self._tracker:
            self._announce("recenter_need_start")
            return
        self._tracker.recenter()
        self._announce("recenter")
        self._emit()

    def _open_settings(self) -> None:
        open_settings_window()
        self._announce("settings")

    def _emit(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self.status, k, v)
        if self._on_status:
            self._on_status(self.status)

    def _send_preview(self, frame_bgr) -> None:
        if not self._on_preview or frame_bgr is None:
            return
        small = cv2.resize(cv2.flip(frame_bgr, 1), (320, 240))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        self._on_preview(rgb)

    def _boot_and_run(self) -> None:
        try:
            if self.cfg.check_camera_on_start and not check_camera_on_start(self.cfg):
                self.status.running = False
                self.status.message = "Camera check failed"
                self._emit()
                notify(
                    "Head Focus",
                    "Camera not ready. Use Test camera or check privacy settings.",
                    self.cfg.show_toast_notifications,
                )
                self._shutdown_services()
                return

            self._run_loop()
        except Exception as exc:
            self.status.message = f"Error: {exc}"
            self.status.running = False
            self._emit()
            notify("Head Focus", str(exc), self.cfg.show_toast_notifications)
        finally:
            self._starting = False
            if self._tracker:
                self._tracker.close()
                self._tracker = None
            if self.status.running:
                self.status.running = False
                self._emit()

    def _run_loop(self) -> None:
        mapper = ScreenMapper(self.cfg)
        switcher = FocusSwitcher(verbose=self.cfg.debug_preview)
        tracker = HeadTracker(self.cfg)
        self._tracker = tracker
        self.status.camera = tracker._camera_label
        self.status.message = "Tracking"
        self._emit()
        self._announce("start")

        if self.cfg.debug_preview:
            cv2.namedWindow(DEBUG_WINDOW, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(DEBUG_WINDOW, 640, 480)

        last_target = None
        pending = None
        frame_interval = 1.0 / max(1, self.cfg.target_fps)

        while not self._stop_event.is_set():
            frame_start = time.monotonic()
            if self.status.paused:
                time.sleep(0.1)
                if self.cfg.debug_preview:
                    key = cv2.waitKey(1) & 0xFF
                    if handle_debug_keys(key, tracker) == "quit" or debug_window_closed():
                        break
                continue

            frame, yaw = tracker.read()
            if frame is None:
                self.status.message = "Camera lost"
                self._emit()
                break

            self._send_preview(frame)

            target = mapper.update(yaw, frame_start)
            self.status.yaw = yaw
            self.status.zone = mapper.zone
            self.status.target_monitor = f"Monitor {target.number}" if target else None
            self._emit()

            if target != last_target:
                if target and self.cfg.notify_on_monitor_switch:
                    notify(
                        "Head Focus",
                        f"Focus -> monitor {target.number}",
                        self.cfg.show_toast_notifications,
                    )
                last_target = target
                pending = target
            if pending is not None and switcher.focus_screen(pending):
                pending = None

            if self.cfg.debug_preview:
                cv2.imshow(
                    DEBUG_WINDOW,
                    draw_overlay(frame, yaw, mapper, target, self.cfg, tracker._black_frames),
                )
                key = cv2.waitKey(1) & 0xFF
                if handle_debug_keys(key, tracker) == "quit" or debug_window_closed():
                    self._stop_event.set()
                    break

            time.sleep(max(0.0, frame_interval - (time.monotonic() - frame_start)))
