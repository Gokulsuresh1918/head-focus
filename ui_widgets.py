"""Rounded controls for Head Focus (tkinter)."""

from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes


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
