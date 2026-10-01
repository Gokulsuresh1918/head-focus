"""User-friendly settings window for Head Focus."""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from action_feedback import ActionNotice
from config import DEFAULT_CONFIG_PATH, USER_CONFIG_PATH, AppConfig, ensure_user_config
from camera_preview import LiveCameraPreview
from startup_checks import camera_warning_message
from ui_widgets import ActionBanner, RoundedButton, apply_round_window

# ---------------------------------------------------------------------------
# Copy shown in the UI (plain language for end users)
# ---------------------------------------------------------------------------
FIELD_HELP = {
    "debug_preview": (
        "Show live webcam preview",
        "Opens a small video window with head angle and target monitor. "
        "Turn off for everyday use (tray icon only).",
    ),
    "show_tray_icon": (
        "Run in the system tray",
        "Green icon = tracking on. Right-click or use the menu to pause, recenter, or quit.",
    ),
    "camera_index": (
        "Which webcam to use",
        "Usually 0. If the wrong camera opens, try 1 or 2 after running Test camera.",
    ),
    "target_fps": (
        "Tracking speed",
        "Lower values use less CPU. 10–15 is fine for most PCs.",
    ),
    "yaw_threshold_deg": (
        "How far to turn your head",
        "Degrees left/right before switching monitors. Increase if it switches too easily.",
    ),
    "hysteresis_deg": (
        "Stability (anti-jitter)",
        "Must turn back this much before leaving a zone. Helps stop flickering at the boundary.",
    ),
    "dwell_seconds": (
        "Hold time before switch",
        "Seconds you must look at a monitor before focus moves. Increase to avoid accidents.",
    ),
    "yaw_offset_deg": (
        "Calibration offset",
        "Normally set with Recenter (Ctrl+Alt+C). Advanced: edit manually if needed.",
    ),
    "smoothing": (
        "Motion smoothing",
        "Higher = smoother but slower to react. 0.25–0.4 works well.",
    ),
    "check_camera_on_start": (
        "Test webcam on startup",
        "Quick check that the camera is not black before tracking starts.",
    ),
    "warn_if_eviacam_running": (
        "Log camera conflict warnings",
        "Print a console warning at startup if the webcam probe fails.",
    ),
    "exit_on_black_camera": (
        "Quit if camera fails check",
        "If the startup test fails, exit instead of running with a black feed.",
    ),
    "hotkey_toggle_pause": (
        "Pause / resume",
        "Ctrl + Alt + H",
    ),
    "hotkey_recenter": (
        "Recenter (save straight-ahead)",
        "Ctrl + Alt + C — look at the centre monitor first.",
    ),
    "hotkey_open_settings": (
        "Open settings",
        "Ctrl + Alt + S",
    ),
    "show_toast_notifications": (
        "Show toast notifications",
        "Windows notifications when you pause, recenter, start/stop, etc.",
    ),
    "notify_on_monitor_switch": (
        "Notify on every monitor switch",
        "Can be frequent; leave off unless you want a toast each time focus moves.",
    ),
}

SENSITIVITY_PRESETS = {
    "Easy": {"yaw_threshold_deg": 12.0, "dwell_seconds": 0.15, "hysteresis_deg": 3.0},
    "Balanced": {"yaw_threshold_deg": 15.0, "dwell_seconds": 0.25, "hysteresis_deg": 4.0},
    "Strict": {"yaw_threshold_deg": 22.0, "dwell_seconds": 0.45, "hysteresis_deg": 6.0},
}


class SettingsApp:
    def __init__(self, on_saved=None):
        ensure_user_config()
        self.cfg = AppConfig.load()
        self.on_saved = on_saved
        self._vars: dict[str, tk.Variable] = {}
        self._cam_photo: ImageTk.PhotoImage | None = None
        self._test_preview = LiveCameraPreview()

        self.root = tk.Tk()
        self.root.title("Head Focus - Settings")
        self.root.minsize(560, 520)
        self.root.geometry("620x580")
        self._setup_theme()
        self._build()
        self._center_window()
        apply_round_window(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(80, self._tick_cam_preview)

    def _setup_theme(self):
        try:
            self.root.tk.call("source", "azure.tcl")
        except tk.TclError:
            pass
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
        self.font_title = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.font_sub = tkfont.Font(family="Segoe UI", size=9)
        self.font_body = tkfont.Font(family="Segoe UI", size=10)
        self.font_hint = tkfont.Font(family="Segoe UI", size=9)
        self.root.configure(bg="#eef1f5")

    def _center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

    def _scrollable_tab(self, parent) -> ttk.Frame:
        outer = ttk.Frame(parent)
        canvas = tk.Canvas(outer, highlightthickness=0, bg="#f5f5f5")
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, padding=12)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _wheel)
        outer._inner = inner  # type: ignore[attr-defined]
        return outer

    def _section(self, parent, title: str) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text=f"  {title}  ", padding=(12, 10))
        frame.pack(fill=tk.X, pady=(0, 12))
        return frame

    def _add_bool_row(self, parent, key: str):
        title, desc = FIELD_HELP[key]
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=6)
        var = tk.BooleanVar(value=getattr(self.cfg, key))
        self._vars[key] = var
        cb = ttk.Checkbutton(row, text=title, variable=var)
        cb.pack(anchor="w")
        ttk.Label(row, text=desc, wraplength=520, font=self.font_hint, foreground="#555").pack(
            anchor="w", padx=(22, 0), pady=(2, 0)
        )

    def _add_int_row(self, parent, key: str, from_, to):
        title, desc = FIELD_HELP[key]
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=6)
        top = ttk.Frame(row)
        top.pack(fill=tk.X)
        ttk.Label(top, text=title, font=self.font_body).pack(side=tk.LEFT)
        var = tk.IntVar(value=getattr(self.cfg, key))
        self._vars[key] = var
        ttk.Spinbox(top, textvariable=var, from_=from_, to=to, width=8).pack(side=tk.RIGHT)
        ttk.Label(row, text=desc, wraplength=520, font=self.font_hint, foreground="#555").pack(
            anchor="w", pady=(2, 0)
        )

    def _add_float_row(self, parent, key: str, from_, to, increment=0.5):
        title, desc = FIELD_HELP[key]
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=6)
        top = ttk.Frame(row)
        top.pack(fill=tk.X)
        ttk.Label(top, text=title, font=self.font_body).pack(side=tk.LEFT)
        var = tk.DoubleVar(value=getattr(self.cfg, key))
        self._vars[key] = var
        ttk.Spinbox(
            top, textvariable=var, from_=from_, to=to, increment=increment, width=8
        ).pack(side=tk.RIGHT)
        ttk.Label(row, text=desc, wraplength=520, font=self.font_hint, foreground="#555").pack(
            anchor="w", pady=(2, 0)
        )

    def _add_hotkey_row(self, parent, key: str):
        title, shortcut = FIELD_HELP[key]
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=8)
        var = tk.BooleanVar(value=getattr(self.cfg, key))
        self._vars[key] = var
        left = ttk.Frame(row)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Checkbutton(left, text=title, variable=var).pack(anchor="w")
        ttk.Label(
            row, text=shortcut, font=("Consolas", 10), foreground="#0066aa"
        ).pack(side=tk.RIGHT, padx=(8, 0))

    def _apply_preset(self, name: str):
        preset = SENSITIVITY_PRESETS[name]
        for k, v in preset.items():
            if k in self._vars:
                self._vars[k].set(v)
        self._status.set(f"Applied '{name}' preset - click Save to keep changes.")
        self._banner.show_notice(
            ActionNotice.custom(
                f"{name} preset applied",
                "Values updated on the Tracking tab. Click Save at the bottom to keep them.",
            ),
            duration_ms=10000,
        )

    def _build(self):
        head = tk.Frame(self.root, bg="#eef1f5", padx=16, pady=12)
        head.pack(fill=tk.X)
        tk.Label(head, text="Settings", font=("Segoe UI", 18, "bold"), bg="#eef1f5", fg="#222").pack(anchor="w")
        self._banner = ActionBanner(head, wraplength=560)

        nb = ttk.Notebook(self.root, padding=(8, 4))
        nb.pack(fill=tk.BOTH, expand=True)

        tab_general = self._scrollable_tab(nb)
        tab_tracking = self._scrollable_tab(nb)
        tab_startup = self._scrollable_tab(nb)
        tab_hotkeys = self._scrollable_tab(nb)
        nb.add(tab_general, text="  General  ")
        nb.add(tab_tracking, text="  Tracking  ")
        nb.add(tab_startup, text="  Startup  ")
        nb.add(tab_hotkeys, text="  Shortcuts  ")

        g = tab_general._inner
        t = tab_tracking._inner
        s = tab_startup._inner
        h = tab_hotkeys._inner

        sec = self._section(g, "Appearance")
        self._add_bool_row(sec, "debug_preview")
        self._add_bool_row(sec, "show_tray_icon")

        sec = self._section(g, "Camera & performance")
        self._add_int_row(sec, "camera_index", 0, 9)
        self._add_int_row(sec, "target_fps", 5, 30)

        cam_box = self._section(g, "Camera test preview")
        ttk.Label(
            cam_box,
            text="Click Test camera for a live preview here. Video is not saved to disk.",
            wraplength=520,
            font=self.font_hint,
            foreground="#555",
        ).pack(anchor="w", pady=(0, 6))
        self._cam_preview = tk.Label(
            cam_box,
            text="No preview yet",
            bg="#2c3e50",
            fg="#95a5a6",
            font=("Segoe UI", 9),
            height=10,
        )
        self._cam_preview.pack(fill=tk.X)
        sec = self._section(g, "Notifications")
        self._add_bool_row(sec, "show_toast_notifications")
        self._add_bool_row(sec, "notify_on_monitor_switch")

        info = ttk.Frame(g, padding=(0, 4))
        info.pack(fill=tk.X)
        ttk.Label(
            info,
            text="After changing settings, restart Head Focus or use Save and relaunch.",
            font=self.font_hint,
            foreground="#666",
        ).pack(anchor="w")

        sec = self._section(t, "Quick presets")
        preset_row = ttk.Frame(sec)
        preset_row.pack(fill=tk.X, pady=4)
        ttk.Label(preset_row, text="Sensitivity:", font=self.font_body).pack(side=tk.LEFT)
        for name in SENSITIVITY_PRESETS:
            ttk.Button(preset_row, text=name, width=10, command=lambda n=name: self._apply_preset(n)).pack(
                side=tk.LEFT, padx=4
            )

        sec = self._section(t, "Fine tuning")
        self._add_float_row(sec, "yaw_threshold_deg", 5, 45)
        self._add_float_row(sec, "hysteresis_deg", 0, 20)
        self._add_float_row(sec, "dwell_seconds", 0.05, 2.0, increment=0.05)
        self._add_float_row(sec, "smoothing", 0.05, 1.0, increment=0.05)
        self._add_float_row(sec, "yaw_offset_deg", -90, 90)

        tip = ttk.Frame(t, padding=(4, 0))
        tip.pack(fill=tk.X)
        ttk.Label(
            tip,
            text="Tip: Look at your centre monitor and press Ctrl+Alt+C (or tray → Recenter) to set straight-ahead.",
            wraplength=540,
            font=self.font_hint,
            foreground="#1a5fb4",
        ).pack(anchor="w")

        sec = self._section(s, "When the app starts")
        self._add_bool_row(sec, "check_camera_on_start")
        self._add_bool_row(sec, "warn_if_eviacam_running")
        self._add_bool_row(sec, "exit_on_black_camera")

        sec = self._section(h, "Keyboard shortcuts (global)")
        ttk.Label(
            sec,
            text="Work while Head Focus runs in the background. Uncheck to disable a shortcut.",
            wraplength=520,
            font=self.font_hint,
            foreground="#555",
        ).pack(anchor="w", pady=(0, 8))
        self._add_hotkey_row(sec, "hotkey_toggle_pause")
        self._add_hotkey_row(sec, "hotkey_recenter")
        self._add_hotkey_row(sec, "hotkey_open_settings")

        footer = tk.Frame(self.root, bg="#eef1f5", padx=16, pady=12)
        footer.pack(fill=tk.X)

        self._status = tk.StringVar(value="Tap Save to apply changes.")
        tk.Label(footer, textvariable=self._status, font=self.font_hint, fg="#666", bg="#eef1f5").pack(
            anchor="w", pady=(0, 8)
        )

        RoundedButton(
            footer,
            text="Save",
            command=self._save,
            fill="#1a5fb4",
            fill_hover="#15539e",
            height=44,
            bg="#eef1f5",
        ).pack(fill=tk.X, pady=(0, 8))

        links = tk.Frame(footer, bg="#eef1f5")
        links.pack(fill=tk.X)
        for text, cmd in (
            ("Test camera", self._test_camera),
            ("Defaults", self._restore_defaults),
            ("Open folder", self._open_folder),
        ):
            tk.Button(
                links,
                text=text,
                command=cmd,
                relief=tk.FLAT,
                bg="#eef1f5",
                fg="#1a5fb4",
                font=("Segoe UI", 10),
                cursor="hand2",
            ).pack(side=tk.LEFT, padx=(0, 12))

    def _apply_vars(self) -> AppConfig:
        cfg = AppConfig.defaults()
        for key, var in self._vars.items():
            setattr(cfg, key, var.get())
        return cfg

    def _save(self):
        self.cfg = self._apply_vars()
        self.cfg.save()
        if self.on_saved:
            self.on_saved(self.cfg)
        self._status.set("Saved. Restart Head Focus for all changes to take effect.")
        self._banner.show_notice(
            ActionNotice.custom(
                "Settings saved",
                "Your choices are written to config.json. Restart Head Focus if it is already running.",
            ),
            duration_ms=12000,
        )
        messagebox.showinfo(
            "Head Focus",
            "Settings saved.\n\nRestart Head Focus if it is already running.",
        )

    def _restore_defaults(self):
        if os.path.isfile(DEFAULT_CONFIG_PATH):
            with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as f:
                self.cfg = AppConfig.from_dict(json.load(f))
        else:
            self.cfg = AppConfig.defaults()
        for key, var in self._vars.items():
            var.set(getattr(self.cfg, key))
        self._status.set("Defaults loaded into the form - click Save to apply.")
        self._banner.show_notice(
            ActionNotice.custom(
                "Defaults loaded",
                "Form reset to factory values. Click Save to write them to config.json.",
            ),
            duration_ms=10000,
        )
        messagebox.showinfo("Head Focus", "Defaults restored. Click Save to write config.json.")

    def _tick_cam_preview(self):
        live = self._test_preview.latest_rgb()
        if live is not None:
            self._cam_photo = ImageTk.PhotoImage(Image.fromarray(live))
            self._cam_preview.config(image=self._cam_photo, text="")
        self.root.after(80, self._tick_cam_preview)

    def _test_camera(self):
        if self._test_preview.running:
            self._test_preview.stop()
            self._cam_preview.config(image="", text="No preview yet", bg="#2c3e50")
            self._status.set("Live preview stopped.")
            self._banner.show_text(
                "Preview stopped",
                "Click Test camera again to start live video.",
                duration_ms=8000,
            )
            return
        self._status.set("Starting live preview…")
        self._banner.show_notice(ActionNotice.from_key("test_camera_busy"), duration_ms=0)
        self._cam_preview.config(image="", text="Opening camera…", bg="#2c3e50")
        idx = int(self._vars["camera_index"].get())

        def work():
            ok, mode = self._test_preview.start(idx)

            def done():
                if ok:
                    self._status.set(f"Live preview ({mode})")
                    self._banner.show_text(
                        "Live preview",
                        f"{mode or 'Camera'} — video stays in this window only. Click Test camera to stop.",
                        duration_ms=12000,
                    )
                else:
                    self._cam_preview.config(image="", text="Camera test failed", bg="#2c3e50")
                    self._status.set("Camera test failed")
                    hint = camera_warning_message(0.0, None) or ""
                    self._banner.show_text(
                        "Camera test failed",
                        hint or "Close other apps using the webcam and check Camera privacy for python.exe.",
                        duration_ms=14000,
                    )

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _on_close(self):
        self._test_preview.stop()
        self.root.destroy()

    def _open_folder(self):
        os.startfile(os.path.dirname(USER_CONFIG_PATH))
        self._banner.show_text(
            "Folder opened",
            f"Config folder: {os.path.dirname(USER_CONFIG_PATH)}",
            duration_ms=8000,
        )

    def run(self):
        self.root.mainloop()


def main():
    SettingsApp().run()


if __name__ == "__main__":
    main()
