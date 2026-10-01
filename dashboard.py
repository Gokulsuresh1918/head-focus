"""Head Focus desktop dashboard (main application window)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app_resources import ICON_PATH, ensure_app_icon
from config import AppConfig, ensure_user_config
from notifications import notify
from startup_checks import is_process_running, probe_camera, run_check_camera_script
from tracking_engine import TrackingSession, TrackingStatus

# Button colors
COLOR_START = "#2ecc71"
COLOR_START_H = "#27ae60"
COLOR_STOP = "#e74c3c"
COLOR_STOP_H = "#c0392b"
COLOR_PAUSE = "#f39c12"


class DashboardApp:
    def __init__(self):
        ensure_user_config()
        ensure_app_icon()
        self.cfg = AppConfig.load()
        self.session: TrackingSession | None = None
        self._tracking_active = False

        self.root = tk.Tk()
        self.root.title("Head Focus")
        self.root.minsize(460, 580)
        self.root.geometry("480x620")
        try:
            self.root.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass

        self._status_var = tk.StringVar(value="Stopped")
        self._detail_var = tk.StringVar(value="Press the green button to start.")
        self._live_var = tk.StringVar(value="Yaw --  |  Zone --  |  Monitor --")
        self._camera_var = tk.StringVar(value="Camera: not checked yet")

        self._build()
        self._center()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, self._refresh_checks)

    def _center(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

    def _build(self):
        header = tk.Frame(self.root, bg="#1a5fb4", padx=20, pady=14)
        header.pack(fill=tk.X)
        tk.Label(header, text="Head Focus", font=("Segoe UI", 20, "bold"), fg="white", bg="#1a5fb4").pack(
            anchor="w"
        )
        tk.Label(
            header,
            text="Look at a monitor to move keyboard focus there",
            font=("Segoe UI", 10),
            fg="#dce8f5",
            bg="#1a5fb4",
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self.root, padding=(16, 12))
        body.pack(fill=tk.BOTH, expand=True)

        # --- Warnings (eViacam etc.) ---
        self._alert_frame = tk.Frame(body, bg="#fdebd0", padx=12, pady=10)
        self._alert_label = tk.Label(
            self._alert_frame,
            text="",
            bg="#fdebd0",
            fg="#7d6608",
            font=("Segoe UI", 10),
            justify=tk.LEFT,
            wraplength=420,
        )
        self._alert_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(self._alert_frame, text="Refresh", command=self._refresh_checks, width=10).pack(
            side=tk.RIGHT, padx=(8, 0)
        )

        # --- Main start / stop ---
        hero = ttk.Frame(body, padding=(0, 12))
        hero.pack(fill=tk.X)

        self._btn_main = tk.Button(
            hero,
            text="START TRACKING",
            command=self._toggle_main,
            bg=COLOR_START,
            fg="white",
            activebackground=COLOR_START_H,
            activeforeground="white",
            font=("Segoe UI", 14, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            pady=16,
        )
        self._btn_main.pack(fill=tk.X)

        self._btn_pause = tk.Button(
            hero,
            text="Pause",
            command=self._pause,
            bg=COLOR_PAUSE,
            fg="white",
            activebackground="#d68910",
            activeforeground="white",
            font=("Segoe UI", 11),
            relief=tk.FLAT,
            cursor="hand2",
            pady=10,
            state=tk.DISABLED,
        )
        self._btn_pause.pack(fill=tk.X, pady=(8, 0))

        # --- Status ---
        status_frame = ttk.LabelFrame(body, text="  Status  ", padding=10)
        status_frame.pack(fill=tk.X, pady=(4, 10))
        self._status_lbl = tk.Label(
            status_frame, textvariable=self._status_var, font=("Segoe UI", 13, "bold"), fg="#333"
        )
        self._status_lbl.pack(anchor="w")
        ttk.Label(status_frame, textvariable=self._detail_var, wraplength=420).pack(anchor="w", pady=(4, 0))
        ttk.Label(status_frame, textvariable=self._camera_var, font=("Segoe UI", 9), foreground="#666").pack(
            anchor="w", pady=(6, 0)
        )
        ttk.Label(status_frame, textvariable=self._live_var, font=("Consolas", 10), foreground="#1a5fb4").pack(
            anchor="w", pady=(8, 0)
        )

        # --- Secondary actions ---
        tools = ttk.Frame(body)
        tools.pack(fill=tk.X, pady=(0, 8))
        for text, cmd in (
            ("Recenter", self._recenter),
            ("Settings", self._settings),
            ("Test camera", self._test_camera),
        ):
            ttk.Button(tools, text=text, command=cmd).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        ttk.Label(
            body,
            text="Shortcuts: Ctrl+Alt+H pause  |  Ctrl+Alt+C recenter  |  Ctrl+Alt+S settings",
            font=("Segoe UI", 8),
            foreground="#888",
        ).pack(anchor="w")

        ttk.Label(
            self.root,
            text="Tip: Quit eViacam before starting if the camera stays black.",
            font=("Segoe UI", 8),
            foreground="#999",
            padding=(12, 10),
        ).pack(fill=tk.X)

    def _show_alert(self, text: str | None):
        if text:
            self._alert_label.config(text=text)
            self._alert_frame.pack(fill=tk.X, pady=(0, 8), before=self._btn_main.master)
        else:
            self._alert_frame.pack_forget()

    def _refresh_checks(self):
        self._camera_var.set("Camera: checking...")
        self._show_alert(None)

        def work():
            eviacam = is_process_running("eviacam.exe")
            mean, mode = probe_camera(self.cfg.camera_index)
            self.root.after(0, lambda: self._apply_checks(eviacam, mean, mode))

        threading.Thread(target=work, name="CameraCheck", daemon=True).start()

    def _apply_checks(self, eviacam: bool, mean: float, mode: str | None):
        alerts = []
        if eviacam:
            alerts.append(
                "eViacam is running and usually blocks this app from using your webcam. "
                "Right-click eViacam in the system tray and choose Exit, then click Refresh."
            )
        if mode:
            self._camera_var.set(f"Camera: OK ({mode}, brightness {mean:.0f})")
        else:
            self._camera_var.set("Camera: not ready (black or busy)")
            if not eviacam:
                alerts.append(
                    "Webcam looks black or busy. Close other camera apps and allow python.exe "
                    "under Settings > Privacy > Camera, then Refresh."
                )

        self._show_alert("\n\n".join(alerts) if alerts else None)

    def _set_main_button_running(self, running: bool, paused: bool = False):
        self._tracking_active = running
        if running:
            self._btn_main.config(
                text="STOP TRACKING",
                bg=COLOR_STOP,
                activebackground=COLOR_STOP_H,
            )
            self._btn_pause.config(state=tk.NORMAL)
            self._btn_pause.config(text="Resume" if paused else "Pause")
        else:
            self._btn_main.config(
                text="START TRACKING",
                bg=COLOR_START,
                activebackground=COLOR_START_H,
            )
            self._btn_pause.config(state=tk.DISABLED, text="Pause")

    def _toggle_main(self):
        if self._tracking_active:
            self._stop()
        else:
            self._start()

    def _on_status(self, status: TrackingStatus):
        def update():
            if status.running:
                if status.paused:
                    self._status_var.set("Paused")
                    self._status_lbl.config(fg=COLOR_PAUSE)
                    self._detail_var.set("Tracking is paused. Click Resume or Ctrl+Alt+H.")
                else:
                    self._status_var.set("Tracking")
                    self._status_lbl.config(fg=COLOR_START)
                    self._detail_var.set("Turn your head toward a monitor to switch focus.")
            else:
                self._status_var.set("Stopped")
                self._status_lbl.config(fg="#333")
                self._detail_var.set("Press START TRACKING when your camera is ready.")

            yaw = f"{status.yaw:+.0f}" if status.yaw is not None else "--"
            zone = status.zone or "--"
            mon = status.target_monitor or "none"
            self._live_var.set(f"Yaw {yaw} deg  |  Zone {zone}  |  {mon}")
            if status.camera:
                self._camera_var.set(f"Camera: {status.camera}")

            self._set_main_button_running(status.running, status.paused)

        self.root.after(0, update)

    def _start(self):
        if is_process_running("eviacam.exe"):
            ok = messagebox.askyesno(
                "eViacam is running",
                "eViacam often blocks the webcam so Head Focus gets a black picture.\n\n"
                "Quit eViacam first (recommended).\n\n"
                "Start tracking anyway?",
                icon=messagebox.WARNING,
            )
            if not ok:
                return

        self.cfg = AppConfig.load()
        self.session = TrackingSession(self.cfg, on_status=self._on_status)
        if not self.session.start():
            self.session = None
            messagebox.showerror(
                "Cannot start",
                "Camera check failed.\n\nQuit eViacam, run Test camera, then try again.",
            )
            self._refresh_checks()
        else:
            self._set_main_button_running(True, False)

    def _stop(self):
        if self.session:
            self.session.stop()
            self.session = None
        self._set_main_button_running(False)
        self._status_var.set("Stopped")
        self._status_lbl.config(fg="#333")
        self._detail_var.set("Press START TRACKING to begin again.")
        self._refresh_checks()

    def _pause(self):
        if self.session and self.session.status.running:
            self.session.toggle_pause()

    def _recenter(self):
        if self.session and self.session.status.running:
            self.session.recenter()
        else:
            notify("Head Focus", "Start tracking first, then use Recenter.", self.cfg.show_toast_notifications)

    def _settings(self):
        subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(__file__), "settings_ui.py")],
            cwd=os.path.dirname(__file__),
        )

    def _test_camera(self):
        run_check_camera_script()
        self.root.after(2000, self._refresh_checks)

    def _on_close(self):
        if self.session:
            self.session.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    DashboardApp().run()


if __name__ == "__main__":
    main()
