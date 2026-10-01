"""Head Focus — simple dashboard."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

import numpy as np
from PIL import Image, ImageTk

from action_feedback import ActionNotice
from app_resources import ICON_PATH, ensure_app_icon
from camera_preview import LiveCameraPreview
from config import AppConfig, ensure_user_config
from notifications import notify
from startup_checks import camera_warning_message, probe_camera
from tracking_engine import TrackingSession, TrackingStatus
from ui_widgets import CameraPreviewBox, RoundedButton, RoundedPanel, apply_round_window

BG = "#eef1f5"
COLOR_START = "#2ecc71"
COLOR_START_H = "#27ae60"
COLOR_STOP = "#e74c3c"
COLOR_STOP_H = "#c0392b"
COLOR_PAUSE = "#f39c12"
COLOR_PAUSE_H = "#d68910"


class DashboardApp:
    def __init__(self):
        ensure_user_config()
        ensure_app_icon()
        self.cfg = AppConfig.load()
        self.session: TrackingSession | None = None
        self._tracking = False
        self._tracking_boot = False
        self._preview_rgb: np.ndarray | None = None
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._test_preview = LiveCameraPreview()
        self._test_preview_mode: str | None = None
        self._start_allowed = False
        self._link_buttons: list[tk.Button] = []

        self.root = tk.Tk()
        self.root.title("Head Focus")
        self.root.configure(bg=BG)
        self.root.minsize(500, 720)
        self.root.geometry("520x780")
        try:
            self.root.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass

        self._build()
        apply_round_window(self.root)
        self._center()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._lock_for_app_startup()
        self.root.after(120, self._initial_camera_setup)
        self.root.after(80, self._tick_preview)

    def _center(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")

    def _build(self):
        pad = tk.Frame(self.root, bg=BG, padx=20, pady=16)
        pad.pack(fill=tk.BOTH, expand=True)

        tk.Label(pad, text="Head Focus", font=("Segoe UI", 22, "bold"), bg=BG, fg="#1a1a1a").pack(anchor="w")
        tk.Label(
            pad,
            text="Look at a monitor to move keyboard focus",
            font=("Segoe UI", 10),
            bg=BG,
            fg="#555",
        ).pack(anchor="w", pady=(2, 8))

        card = RoundedPanel(pad, panel_bg="#ffffff")
        self._card = card
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        inner = tk.Frame(card, bg="#ffffff", padx=10, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)

        self._preview_box = CameraPreviewBox(inner)
        self._preview_box.pack(anchor=tk.CENTER)

        status_row = tk.Frame(card, bg="#ffffff")
        status_row.pack(fill=tk.X, padx=12, pady=(8, 10))
        self._status = tk.StringVar(value="Starting…")
        tk.Label(status_row, textvariable=self._status, font=("Segoe UI", 13, "bold"), bg="#ffffff", fg="#222").pack(
            anchor="w"
        )
        self._sub = tk.StringVar(value="Setting up camera…")
        tk.Label(status_row, textvariable=self._sub, font=("Segoe UI", 9), bg="#ffffff", fg="#666", wraplength=460).pack(
            anchor="w", pady=(4, 0)
        )

        self._btn_main = RoundedButton(
            pad,
            text="Start",
            command=self._toggle,
            fill=COLOR_START,
            fill_hover=COLOR_START_H,
            font=("Segoe UI", 13, "bold"),
            height=50,
            bg=BG,
        )
        self._btn_main.pack(fill=tk.X, pady=(0, 8))

        self._btn_pause = RoundedButton(
            pad,
            text="Pause",
            command=self._pause,
            fill=COLOR_PAUSE,
            fill_hover=COLOR_PAUSE_H,
            font=("Segoe UI", 11),
            height=42,
            bg=BG,
        )
        self._btn_pause.pack(fill=tk.X, pady=(0, 16))
        self._btn_pause.configure(state=tk.DISABLED)

        links = tk.Frame(pad, bg=BG)
        links.pack(fill=tk.X)
        for label, cmd in (
            ("Settings", self._settings),
            ("Test camera", self._test_camera),
            ("Recenter", self._recenter),
            ("Refresh", lambda: self._refresh_checks(user_initiated=True)),
        ):
            b = tk.Button(
                links,
                text=label,
                command=cmd,
                relief=tk.FLAT,
                bg=BG,
                fg="#1a5fb4",
                activebackground=BG,
                activeforeground="#0d3d7a",
                font=("Segoe UI", 10, "underline"),
                cursor="hand2",
                borderwidth=0,
            )
            b.pack(side=tk.LEFT, padx=(0, 16))
            self._link_buttons.append(b)

        tk.Label(
            pad,
            text="Ctrl+Alt+H pause  ·  Ctrl+Alt+C recenter  ·  Ctrl+Alt+S settings",
            font=("Segoe UI", 8),
            bg=BG,
            fg="#999",
        ).pack(anchor="w", pady=(12, 0))

    def _set_links_enabled(self, enabled: bool) -> None:
        for b in self._link_buttons:
            b.configure(state=tk.NORMAL if enabled else tk.DISABLED, fg="#1a5fb4" if enabled else "#aaa")

    def _lock_for_app_startup(self) -> None:
        self._btn_main.configure(state=tk.DISABLED)
        self._btn_pause.configure(state=tk.DISABLED)
        self._set_links_enabled(False)

    def _lock_for_tracking_boot(self) -> None:
        self._tracking_boot = True
        self._preview_rgb = None
        self._btn_main.configure(state=tk.NORMAL, text="Stop", fill=COLOR_STOP, fill_hover=COLOR_STOP_H)
        self._btn_pause.configure(state=tk.DISABLED)
        self._set_links_enabled(False)
        self._preview_box.show_loader("Starting camera…", 10)

    def _unlock_idle(self) -> None:
        self._tracking_boot = False
        self._tracking = False
        self._preview_rgb = None
        self._preview_box.hide_loader()
        if self._start_allowed:
            self._btn_main.configure(state=tk.NORMAL, text="Start", fill=COLOR_START, fill_hover=COLOR_START_H)
        else:
            self._btn_main.configure(state=tk.DISABLED, text="Start", fill=COLOR_START, fill_hover=COLOR_START_H)
        self._btn_pause.configure(state=tk.DISABLED, text="Pause")
        self._set_links_enabled(True)
        self._status.set("Ready")
        if not self._test_preview.running:
            self._preview_box.set_placeholder("Click Test camera for live video")

    def _unlock_tracking_ready(self) -> None:
        if not self._tracking_boot:
            return
        self._tracking_boot = False
        self._tracking = True
        self._preview_box.hide_loader()
        self._btn_main.configure(state=tk.NORMAL, text="Stop", fill=COLOR_STOP, fill_hover=COLOR_STOP_H)
        self._btn_pause.configure(state=tk.NORMAL, text="Pause")
        self._set_links_enabled(True)
        self._status.set("Tracking")

    def _feedback(self, notice: ActionNotice) -> None:
        """Toast or status line only — no duplicate banner inside the window."""
        self.cfg = AppConfig.load()
        if self.cfg.show_toast_notifications:
            notify(notice.title, notice.toast_body(), True)
        else:
            line = notice.detail
            if notice.undo:
                line = f"{line} ({notice.undo.replace('Undo: ', '')})"
            self._sub.set(line[:240])

    def _on_action(self, notice: ActionNotice) -> None:
        # TrackingSession._announce already shows toasts when enabled.
        if self.cfg.show_toast_notifications:
            return
        self.root.after(0, lambda n=notice: self._feedback(n))

    def _hint_outside(self, text: str | None, *, force: bool = False) -> None:
        """Camera hints via toast only — never a box inside the window."""
        if not text:
            return
        self.cfg = AppConfig.load()
        if self.cfg.show_toast_notifications or force:
            notify("Camera", text, True)
        else:
            self._sub.set(text[:220])

    def _scale_preview(self, rgb: np.ndarray) -> ImageTk.PhotoImage:
        w, h = CameraPreviewBox.PREVIEW_W, CameraPreviewBox.PREVIEW_H
        img = Image.fromarray(rgb).resize((w, h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _initial_camera_setup(self):
        self._preview_box.show_loader("Checking camera…", 15)
        self._sub.set("Please wait — detecting webcam…")

        def work():
            mean, mode = probe_camera(self.cfg.camera_index)
            hint = camera_warning_message(mean, mode)
            self.root.after(0, lambda: self._finish_initial_setup(mean, mode, hint))

        threading.Thread(target=work, daemon=True, name="InitialCameraProbe").start()

    def _finish_initial_setup(self, mean, mode, hint):
        self._start_allowed = bool(mode)
        self._preview_box.hide_loader()
        if not mode:
            self._hint_outside(hint)
        if mode:
            self._sub.set(f"Camera OK · brightness {mean:.0f}")
            self._preview_box.set_placeholder("Click Test camera for live video")
        else:
            self._sub.set("Camera not ready — use Test camera or Refresh")
            self._preview_box.set_placeholder("Camera unavailable")
        self._unlock_idle()

    def _refresh_checks(self, *, user_initiated: bool = False):
        if self._tracking or self._tracking_boot:
            return
        if user_initiated:
            self._preview_box.show_loader("Checking camera…", 40)
            self._set_links_enabled(False)
            self._btn_main.configure(state=tk.DISABLED)
            self._sub.set("Checking camera…")
        else:
            self._sub.set("Checking camera…")

        def work():
            mean, mode = probe_camera(self.cfg.camera_index)
            hint = camera_warning_message(mean, mode)
            self.root.after(0, lambda: self._apply_checks(mean, mode, hint, user_initiated))

        threading.Thread(target=work, daemon=True).start()

    def _apply_checks(self, mean, mode, hint, user_initiated: bool = False):
        if not user_initiated:
            if mode:
                self._start_allowed = True
                self._sub.set(f"Camera OK · brightness {mean:.0f}")
            return
        self._start_allowed = bool(mode)
        self._preview_box.hide_loader()
        if mode:
            self._sub.set(f"Camera OK · brightness {mean:.0f}")
            if not self._test_preview.running:
                self._preview_box.set_placeholder("Click Test camera for live video")
        else:
            self._sub.set("Camera not ready — see toast notification")
            self._hint_outside(hint)
        if not self._tracking and not self._tracking_boot:
            self._unlock_idle()

    def _on_preview(self, rgb: np.ndarray):
        self._preview_rgb = rgb
        if self._tracking_boot:
            self.root.after(0, self._unlock_tracking_ready)

    def _tick_preview(self):
        if self._tracking and self._preview_rgb is not None:
            self._preview_photo = self._scale_preview(self._preview_rgb)
            self._preview_box.hide_loader()
            self._preview_box.set_video_image(self._preview_photo)
        elif not self._tracking and not self._tracking_boot:
            live = self._test_preview.latest_rgb()
            if live is not None:
                self._preview_photo = self._scale_preview(live)
                self._preview_box.hide_loader()
                self._preview_box.set_video_image(self._preview_photo)
            elif not self._test_preview.running:
                pass
        self.root.after(80, self._tick_preview)

    def _toggle(self):
        if self._tracking or self._tracking_boot:
            self._stop()
        else:
            self._start()

    def _on_status(self, status: TrackingStatus):
        def update():
            if self._tracking_boot and not status.preview_ready:
                if status.boot_label:
                    self._sub.set(status.boot_label)
                if status.boot_progress:
                    self._preview_box.show_loader(status.boot_label or "Starting…", status.boot_progress)
                if status.message == "Camera check failed":
                    messagebox.showwarning(
                        "Camera",
                        "Webcam not available. Close other camera apps and check Privacy settings.",
                    )
                    self._stop()
                    self._refresh_checks()
                return

            if status.running:
                if status.paused:
                    self._sub.set("Paused")
                    self._btn_pause.configure(text="Resume")
                elif status.yaw is not None:
                    self._sub.set(
                        f"Yaw {status.yaw:+.0f}° · {status.zone or '--'} · {status.target_monitor or '—'}"
                    )
                    self._btn_pause.configure(text="Pause")
                elif status.preview_ready:
                    self._sub.set("Face the camera")
            elif status.message in ("Stopped", "Ready"):
                self._unlock_idle()
                self._sub.set("Tap Start when your camera is free" if self._start_allowed else "Fix camera, then Refresh")

        self.root.after(0, update)

    def _start(self):
        if not self._start_allowed:
            self._feedback(
                ActionNotice.custom(
                    "Camera not ready",
                    "Use Test camera or Refresh after closing other apps that use the webcam.",
                ),
            )
            return
        self.cfg = AppConfig.load()
        self._stop_test_preview(quiet=True)
        self._lock_for_tracking_boot()
        self._status.set("Starting…")
        self._sub.set("Loading model and opening webcam…")
        self.session = TrackingSession(
            self.cfg,
            on_status=self._on_status,
            on_preview=self._on_preview,
            on_action=self._on_action,
            gui_mode=True,
        )
        self.session.start()

    def _stop(self):
        if self.session:
            self.session.stop()
            self.session = None
        self._unlock_idle()
        self.root.after(600, lambda: self._refresh_checks(user_initiated=False))

    def _pause(self):
        if self.session and self.session.status.running and self.session.status.preview_ready:
            self.session.toggle_pause()
        elif self._tracking_boot:
            pass
        else:
            self._feedback(
                ActionNotice.custom("Pause", "Start tracking first, then use Pause or Ctrl+Alt+H."),
            )

    def _recenter(self):
        if self.session and self.session.status.running and self.session.status.preview_ready:
            self.session.recenter()
        elif not self._tracking_boot:
            self._feedback(ActionNotice.from_key("recenter_need_start"))

    def _settings(self):
        if self._tracking_boot:
            return
        subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(__file__), "settings_ui.py")],
            cwd=os.path.dirname(__file__),
        )

    def _stop_test_preview(self, *, quiet: bool = False) -> None:
        was_running = self._test_preview.running
        self._test_preview.stop()
        self._test_preview_mode = None
        if was_running and not quiet:
            self._preview_box.set_placeholder("Click Test camera for live video")
            self._sub.set("Live preview stopped")

    def _test_camera(self):
        if self._tracking or self._tracking_boot:
            return
        if self._test_preview.running:
            self._stop_test_preview()
            self._refresh_checks()
            return
        self._preview_box.show_loader("Opening live preview…", 20)
        self._set_links_enabled(False)
        self._btn_main.configure(state=tk.DISABLED)
        self._status.set("Preview…")
        self._sub.set("Starting live camera…")
        idx = self.cfg.camera_index

        def work():
            ok, mode = self._test_preview.start(idx)

            def done():
                self._preview_box.hide_loader()
                if ok:
                    self._test_preview_mode = mode
                    self._status.set("Live preview")
                    self._sub.set(f"{mode or 'Camera'} · Test camera again to stop")
                else:
                    self._preview_box.set_placeholder("Camera test failed")
                    self._status.set("Camera failed")
                    hint = camera_warning_message(0.0, None) or ""
                    self._sub.set(hint[:80] if hint else "Try Refresh")
                self._unlock_idle()

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _on_close(self):
        self._test_preview.stop()
        if self.session:
            self.session.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
