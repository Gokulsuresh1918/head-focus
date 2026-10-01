"""Rounded controls for Head Focus (tkinter)."""

from __future__ import annotations

import ctypes
import math
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk


def apply_round_window(root: tk.Tk | tk.Toplevel) -> None:
    """Prefer rounded corners on Windows 11+."""
    try:
        root.update_idletasks()
        hwnd = wintypes.HWND(root.winfo_id())
        preference = wintypes.DWORD(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, wintypes.DWORD(33), ctypes.byref(preference), ctypes.sizeof(preference)
        )
    except (AttributeError, OSError, ValueError):
        pass


class RoundedButton(tk.Canvas):
    """Flat button with rounded corners."""

    def __init__(
        self,
        master,
        text: str,
        command,
        fill: str,
        fill_hover: str,
        fg: str = "white",
        font=("Segoe UI", 12, "bold"),
        radius: int = 14,
        height: int = 48,
        **kwargs,
    ):
        super().__init__(
            master,
            height=height,
            highlightthickness=0,
            borderwidth=0,
            bg=kwargs.pop("bg", master.cget("bg") if hasattr(master, "cget") else "#f0f0f0"),
            **kwargs,
        )
        self._command = command
        self._fill = fill
        self._fill_hover = fill_hover
        self._fg = fg
        self._font = font
        self._radius = radius
        self._text = text
        self._enabled = True
        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._current = fill

    def configure(self, cnf=None, **kw):
        if cnf:
            kw.update(cnf)
        if "text" in kw:
            self._text = kw.pop("text")
        if "state" in kw:
            self._enabled = kw.pop("state") != tk.DISABLED
            if not self._enabled:
                self._current = "#bdc3c7"
            else:
                self._current = self._fill
        if "fill" in kw:
            self._fill = kw.pop("fill")
            self._current = self._fill if self._enabled else "#bdc3c7"
        if "fill_hover" in kw:
            self._fill_hover = kw.pop("fill_hover")
        super().configure(**kw)
        self._redraw()

    config = configure

    def _redraw(self, _event=None):
        w = max(self.winfo_width(), 10)
        h = max(self.winfo_height(), 10)
        self.delete("all")
        r = min(self._radius, h // 2, w // 2)
        self._round_rect(2, 2, w - 2, h - 2, r, fill=self._current, outline="")
        self.create_text(w // 2, h // 2, text=self._text, fill=self._fg if self._enabled else "#eee", font=self._font)

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, _):
        if self._enabled:
            self._current = self._fill_hover
            self._redraw()

    def _on_leave(self, _):
        if self._enabled:
            self._current = self._fill
            self._redraw()

    def _on_click(self, _):
        if self._enabled and self._command:
            self._command()


class RoundedPanel(tk.Frame):
    """White card with subtle border (rounded feel via padding)."""

    def __init__(self, master, **kwargs):
        bg = kwargs.pop("panel_bg", "#ffffff")
        super().__init__(master, bg=bg, highlightbackground="#e0e0e0", highlightthickness=1, **kwargs)


class CameraPreviewBox(tk.Frame):
    """Fixed-size camera area with optional loading overlay."""

    PREVIEW_W = 320
    PREVIEW_H = 240

    def __init__(self, master, **kwargs):
        bg = kwargs.pop("bg", "#2c3e50")
        super().__init__(master, bg=bg, width=self.PREVIEW_W, height=self.PREVIEW_H, **kwargs)
        self.pack_propagate(False)
        self._video = tk.Label(self, bg=bg, fg="#95a5a6", font=("Segoe UI", 9), text="Camera preview")
        self._video.place(x=0, y=0, width=self.PREVIEW_W, height=self.PREVIEW_H)
        self._overlay = tk.Frame(self, bg="#1a252f")
        self._overlay.place(x=0, y=0, width=self.PREVIEW_W, height=self.PREVIEW_H)
        self._overlay.place_forget()
        self._loader_canvas = tk.Canvas(
            self._overlay, width=48, height=48, bg="#1a252f", highlightthickness=0, bd=0
        )
        self._loader_canvas.pack(pady=(72, 8))
        self._loader_text = tk.StringVar(value="Preparing camera…")
        tk.Label(
            self._overlay,
            textvariable=self._loader_text,
            bg="#1a252f",
            fg="#ecf0f1",
            font=("Segoe UI", 10),
        ).pack()
        self._progress = ttk.Progressbar(self._overlay, length=220, mode="determinate", maximum=100)
        self._progress.pack(pady=(10, 0))
        self._spinner_angle = 0
        self._spinner_job: str | None = None

    def set_video_image(self, photo: tk.PhotoImage | None) -> None:
        if photo is None:
            self._video.config(image="", text="")
        else:
            self._video.config(image=photo, text="")

    def set_placeholder(self, text: str) -> None:
        self._video.config(image="", text=text)

    def show_loader(self, message: str, percent: int) -> None:
        if not self._overlay.winfo_ismapped():
            self._overlay.place(x=0, y=0, width=self.PREVIEW_W, height=self.PREVIEW_H)
        self._loader_text.set(message)
        self._progress["value"] = max(0, min(100, percent))
        self._animate_spinner()

    def hide_loader(self) -> None:
        if self._spinner_job:
            self.winfo_toplevel().after_cancel(self._spinner_job)
            self._spinner_job = None
        self._overlay.place_forget()

    def _animate_spinner(self) -> None:
        self._loader_canvas.delete("all")
        cx, cy, r = 24, 24, 18
        self._spinner_angle = (self._spinner_angle + 24) % 360
        colors = ("#1a5276", "#21618c", "#2874a6", "#2e86c1", "#3498db", "#5dade2", "#85c1e9", "#aed6f1")
        for i in range(8):
            a = math.radians(self._spinner_angle + i * 45)
            x1 = cx + r * 0.55 * math.cos(a)
            y1 = cy + r * 0.55 * math.sin(a)
            x2 = cx + r * math.cos(a)
            y2 = cy + r * math.sin(a)
            self._loader_canvas.create_line(
                x1, y1, x2, y2, fill=colors[i], width=3, capstyle=tk.ROUND
            )
        self._spinner_job = self.winfo_toplevel().after(80, self._animate_spinner)


class ActionBanner(tk.Frame):
    """Blue info panel: what the user just did and what to expect."""

    def __init__(self, master, wraplength: int = 340, **kwargs):
        bg = "#dbeafe"
        super().__init__(master, bg=bg, highlightbackground="#93c5fd", highlightthickness=1, **kwargs)
        self._title = tk.StringVar(value="")
        self._detail = tk.StringVar(value="")
        self._after: str | None = None
        tk.Label(
            self,
            textvariable=self._title,
            font=("Segoe UI", 10, "bold"),
            bg=bg,
            fg="#1e3a8a",
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(8, 2))
        tk.Label(
            self,
            textvariable=self._detail,
            font=("Segoe UI", 9),
            bg=bg,
            fg="#1e40af",
            wraplength=wraplength,
            justify=tk.LEFT,
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(0, 8))
        self.pack_forget()

    def show_text(
        self,
        title: str,
        detail: str,
        duration_ms: int = 8000,
        *,
        pack_before: tk.Widget | None = None,
    ) -> None:
        self._title.set(title)
        self._detail.set(detail)
        if not self.winfo_ismapped():
            if pack_before is not None:
                self.pack(fill=tk.X, pady=(0, 10), before=pack_before)
            else:
                self.pack(fill=tk.X, pady=(0, 10))
        root = self.winfo_toplevel()
        if self._after:
            root.after_cancel(self._after)
            self._after = None
        if duration_ms > 0:
            self._after = root.after(duration_ms, self.hide)

    def show_notice(self, notice, duration_ms: int = 8000, *, pack_before: tk.Widget | None = None) -> None:
        undo = notice.undo
        detail = notice.detail if not undo else f"{notice.detail}\n{undo}"
        self.show_text(notice.title, detail, duration_ms, pack_before=pack_before)

    def hide(self) -> None:
        root = self.winfo_toplevel()
        if self._after:
            root.after_cancel(self._after)
            self._after = None
        self.pack_forget()
