"""Background head-tracking session (thread-safe controls)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

import cv2

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
from hotkeys import HotkeyService
from notifications import notify
from startup_checks import check_camera_on_start, warn_eviacam_if_needed
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
    ):
        self.cfg = cfg
        self._on_status = on_status
        self.status = TrackingStatus()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._hotkeys: HotkeyService | None = None
        self._tray: TrayController | None = None
        self._tracker: HeadTracker | None = None

    def start(self) -> bool:
        if self.status.running:
            return True
        enable_dpi_awareness()
        warn_eviacam_if_needed(self.cfg)
        if not check_camera_on_start(self.cfg):
            self._emit(message="Camera check failed")
            notify("Head Focus", "Camera check failed. Run Test camera in settings.", self.cfg.show_toast_notifications)
            return False

        self._stop_event.clear()
        self.status.running = True
        self.status.paused = False
        self.status.message = "Starting..."
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

        self._thread = threading.Thread(target=self._run_loop, name="TrackingLoop", daemon=True)
        self._thread.start()
        notify("Head Focus", "Tracking started", self.cfg.show_toast_notifications)
        return True

    def stop(self) -> None:
        if not self.status.running and not self._thread:
            return
        self._stop_event.set()
        self.status.running = False
        self.status.message = "Stopped"
        self._emit()
        if self._hotkeys:
            self._hotkeys.stop()
            self._hotkeys = None
        if self._tray:
            self._tray.stop()
            self._tray = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        cv2.destroyAllWindows()
        notify("Head Focus", "Tracking stopped", self.cfg.show_toast_notifications)

    def toggle_pause(self) -> None:
        if not self.status.running:
            return
        self.status.paused = not self.status.paused
        if self.status.paused:
            self.status.message = "Paused"
            notify("Head Focus", "Tracking paused (Ctrl+Alt+H)", self.cfg.show_toast_notifications)
        else:
            self.status.message = "Tracking"
            notify("Head Focus", "Tracking resumed", self.cfg.show_toast_notifications)
        if self._tray:
            self._tray.refresh()
        self._emit()

    def recenter(self) -> None:
        if self._tracker:
            self._tracker.recenter()
            notify(
                "Head Focus",
                f"Recentered. Offset saved ({self.cfg.yaw_offset_deg:.1f} deg)",
                self.cfg.show_toast_notifications,
            )
            self._emit()

    def reload_config(self) -> None:
        from config import AppConfig
        self.cfg = AppConfig.load(USER_CONFIG_PATH)

    def _open_settings(self) -> None:
        open_settings_window()
        notify("Head Focus", "Settings opened", self.cfg.show_toast_notifications)

    def _emit(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self.status, k, v)
        if self._on_status:
            self._on_status(self.status)

    def _run_loop(self) -> None:
        try:
            mapper = ScreenMapper(self.cfg)
            switcher = FocusSwitcher(verbose=self.cfg.debug_preview)
            tracker = HeadTracker(self.cfg)
            self._tracker = tracker
            self.status.camera = tracker._camera_label
            self.status.message = "Tracking"
            self._emit()

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

                target = mapper.update(yaw, frame_start)
                self.status.yaw = yaw
                self.status.zone = mapper.zone
                self.status.target_monitor = (
                    f"Monitor {target.number}" if target else None
                )
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
        except Exception as exc:
            self.status.message = f"Error: {exc}"
            self._emit()
            notify("Head Focus", str(exc), self.cfg.show_toast_notifications)
        finally:
            if self._tracker:
                self._tracker.close()
                self._tracker = None
            self.status.running = False
            self._emit()
