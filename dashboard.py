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
from config import AppConfig, ensure_user_config
from notifications import notify
from startup_checks import camera_warning_message, probe_camera, run_check_camera_script
from tracking_engine import TrackingSession, TrackingStatus
from ui_widgets import RoundedButton, RoundedPanel, apply_round_window

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
        self._preview_rgb: np.ndarray | None = None
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._action_after: str | None = None

        self.root = tk.Tk()
        self.root.title("Head Focus")
        self.root.configure(bg=BG)
        self.root.minsize(380, 520)
        self.root.geometry("400x560")
        try:
            self.root.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass

        self._build()
        apply_round_window(self.root)
        self._center()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(400, self._refresh_checks)
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

        self._action_frame = tk.Frame(pad, bg="#dbeafe", highlightbackground="#93c5fd", highlightthickness=1)
        self._action_title = tk.StringVar(value="")
        self._action_detail = tk.StringVar(value="")
        tk.Label(
            self._action_frame,
            textvariable=self._action_title,
            font=("Segoe UI", 10, "bold"),
            bg="#dbeafe",
            fg="#1e3a8a",
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(8, 2))
        tk.Label(
            self._action_frame,
            textvariable=self._action_detail,
            font=("Segoe UI", 9),
            bg="#dbeafe",
            fg="#1e40af",
            wraplength=340,
            justify=tk.LEFT,
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(0, 8))

        self._warn = tk.Label(
            pad, text="", bg="#fff3cd", fg="#664d03", font=("Segoe UI", 9), wraplength=340, padx=10, pady=8
        )

        card = RoundedPanel(pad, panel_bg="#ffffff")
        self._card = card
        card.pack(fill=tk.X, pady=(0, 12))
        inner = tk.Frame(card, bg="#ffffff", padx=8, pady=8)
        inner.pack(fill=tk.X)

        self._preview = tk.Label(
            inner,
            text="Camera preview",
            bg="#2c3e50",
            fg="#95a5a6",
            font=("Segoe UI", 9),
            height=10,
        )
        self._preview.pack(fill=tk.X)

        self._status = tk.StringVar(value="Ready")
        tk.Label(card, textvariable=self._status, font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#222").pack(
            anchor="w", padx=12, pady=(4, 0)
        )
        self._sub = tk.StringVar(value="Tap Start when your camera is free")
        tk.Label(card, textvariable=self._sub, font=("Segoe UI", 9), bg="#ffffff", fg="#666", wraplength=320).pack(
            anchor="w", padx=12, pady=(0, 10)
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
        for label, cmd in (("Settings", self._settings), ("Test camera", self._test_camera), ("Recenter", self._recenter)):
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

        tk.Label(
            pad,
            text="Ctrl+Alt+H pause  ·  Ctrl+Alt+C recenter  ·  Ctrl+Alt+S settings",
            font=("Segoe UI", 8),
            bg=BG,
            fg="#999",
        ).pack(anchor="w", pady=(12, 0))

    def _show_action(self, notice: ActionNotice) -> None:
        self._action_title.set(notice.title)
        self._action_detail.set(notice.window_lines())
        if not self._action_frame.winfo_ismapped():
            self._action_frame.pack(fill=tk.X, pady=(0, 10), before=self._warn if self._warn.winfo_ismapped() else self._card)
        if self._action_after:
            self.root.after_cancel(self._action_after)
        self._action_after = self.root.after(8000, self._hide_action)

    def _hide_action(self) -> None:
        self._action_after = None
        self._action_frame.pack_forget()

    def _on_action(self, notice: ActionNotice) -> None:
        self.root.after(0, lambda n=notice: self._show_action(n))

    def _announce_local(self, key: str) -> None:
        notice = ActionNotice.from_key(key)
        self._show_action(notice)
        notify(notice.title, notice.toast_body(), self.cfg.show_toast_notifications)

    def _show_warn(self, text: str | None):
        if text:
            self._warn.config(text=text)
            self._warn.pack(fill=tk.X, pady=(0, 10), before=self._card)
        else:
            self._warn.pack_forget()

    def _refresh_checks(self):
        self._sub.set("Checking camera…")

        def work():
            mean, mode = probe_camera(self.cfg.camera_index)
            hint = camera_warning_message(mean, mode)
            self.root.after(0, lambda: self._apply_checks(mean, mode, hint))

        threading.Thread(target=work, daemon=True).start()

    def _apply_checks(self, mean, mode, hint):
        if mode:
            self._sub.set(f"Camera OK · brightness {mean:.0f}")
        else:
            self._sub.set("Camera not ready — see tip below")
        self._show_warn(hint)

    def _on_preview(self, rgb: np.ndarray):
        self._preview_rgb = rgb

    def _tick_preview(self):
        if self._preview_rgb is not None and self._tracking:
            self._preview_photo = ImageTk.PhotoImage(Image.fromarray(self._preview_rgb))
            self._preview.config(image=self._preview_photo, text="")
        elif not self._tracking:
            self._preview.config(image="", text="Camera preview", bg="#2c3e50")
            self._preview_rgb = None
        self.root.after(80, self._tick_preview)

    def _set_running(self, running: bool, paused: bool = False):
        self._tracking = running
        if running:
            self._btn_main.configure(text="Stop", fill=COLOR_STOP, fill_hover=COLOR_STOP_H)
            self._btn_pause.configure(state=tk.NORMAL, text="Resume" if paused else "Pause")
            self._status.set("Paused" if paused else "Tracking")
        else:
            self._btn_main.configure(text="Start", fill=COLOR_START, fill_hover=COLOR_START_H)
            self._btn_pause.configure(state=tk.DISABLED, text="Pause")
            self._status.set("Ready")

    def _toggle(self):
        if self._tracking:
            self._stop()
        else:
            self._start()

    def _on_status(self, status: TrackingStatus):
        def update():
            if status.message == "Starting camera...":
                self._status.set("Starting…")
                self._sub.set("Opening webcam")
                self._set_running(True, False)
                return
            if status.running:
                if status.paused:
                    self._sub.set("Paused")
                elif status.yaw is not None:
                    self._sub.set(f"Yaw {status.yaw:+.0f}° · {status.zone or '--'} · {status.target_monitor or '—'}")
                else:
                    self._sub.set("Face the camera")
            else:
                self._sub.set("Tap Start when your camera is free")
                if status.message == "Camera check failed":
                    messagebox.showwarning(
                        "Camera",
                        "Webcam not available. Close other camera apps and check Privacy settings.",
                    )
                    self._refresh_checks()
            self._set_running(status.running, status.paused)

        self.root.after(0, update)

    def _start(self):
        self.cfg = AppConfig.load()
        self.session = TrackingSession(
            self.cfg,
            on_status=self._on_status,
            on_preview=self._on_preview,
            on_action=self._on_action,
        )
        self.session.start()

    def _stop(self):
        if self.session:
            self.session.stop()
            self.session = None
        self._set_running(False)
        self._refresh_checks()

    def _pause(self):
        if self.session and self.session.status.running:
            self.session.toggle_pause()

    def _recenter(self):
        if self.session and self.session.status.running:
            self.session.recenter()
        else:
            self._announce_local("recenter_need_start")

    def _settings(self):
        self._announce_local("settings")
        subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "settings_ui.py")], cwd=os.path.dirname(__file__))

    def _test_camera(self):
        run_check_camera_script()
        self.root.after(2500, self._refresh_checks)

    def _on_close(self):
        if self.session:
            self.session.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
