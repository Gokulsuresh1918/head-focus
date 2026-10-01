"""Global hotkeys via Win32 RegisterHotKey (Ctrl+Alt+H/C/S)."""

from __future__ import annotations

import threading
from typing import Callable

import win32api
import win32con
import win32gui

# Message-only window: receives WM_HOTKEY without showing UI.
HWND_MESSAGE = -3

MOD = win32con.MOD_CONTROL | win32con.MOD_ALT
if hasattr(win32con, "MOD_NOREPEAT"):
    MOD |= win32con.MOD_NOREPEAT

WM_HOTKEY = win32con.WM_HOTKEY
HOTKEY_TOGGLE = 1
HOTKEY_RECENTER = 2
HOTKEY_SETTINGS = 3

_CLASS_NAME = "HeadFocusHotkeys_v2"
_INSTANCE: HotkeyService | None = None


def _static_wnd_proc(hwnd, msg, wparam, lparam):
    """Module-level proc required by pywin32 (bound methods break WM_HOTKEY)."""
    if _INSTANCE is not None:
        return _INSTANCE._wnd_proc(hwnd, msg, wparam, lparam)
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


class HotkeyService:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_recenter: Callable[[], None],
        on_settings: Callable[[], None],
        enable_toggle: bool = True,
        enable_recenter: bool = True,
        enable_settings: bool = True,
    ):
        self._on_toggle = on_toggle
        self._on_recenter = on_recenter
        self._on_settings = on_settings
        self._enable = (enable_toggle, enable_recenter, enable_settings)
        self._thread: threading.Thread | None = None
        self._hwnd = None
        self._ready = threading.Event()

    def start(self) -> None:
        global _INSTANCE
        if not any(self._enable):
            return
        _INSTANCE = self
        self._thread = threading.Thread(target=self._run, name="HotkeyService", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=3.0):
            print("WARNING: Hotkey service did not start in time.")

    def stop(self) -> None:
        global _INSTANCE
        if self._hwnd:
            try:
                win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
        _INSTANCE = None

    def _register(self, hotkey_id: int, vk: str) -> None:
        try:
            win32gui.RegisterHotKey(self._hwnd, hotkey_id, MOD, ord(vk.upper()))
        except win32gui.error as exc:
            print(
                f"WARNING: Could not register Ctrl+Alt+{vk.upper()}: {exc}. "
                "Another program may already use that shortcut."
            )

    def _run(self) -> None:
        hinst = win32api.GetModuleHandle(None)
        try:
            wc = win32gui.WNDCLASS()
            wc.hInstance = hinst
            wc.lpszClassName = _CLASS_NAME
            wc.lpfnWndProc = _static_wnd_proc
            win32gui.RegisterClass(wc)
        except win32gui.error:
            pass  # class already registered from a prior run

        self._hwnd = win32gui.CreateWindowEx(
            0,
            _CLASS_NAME,
            "HeadFocusHotkeys",
            0,
            0,
            0,
            0,
            0,
            HWND_MESSAGE,
            0,
            hinst,
            None,
        )
        if self._enable[0]:
            self._register(HOTKEY_TOGGLE, "H")
        if self._enable[1]:
            self._register(HOTKEY_RECENTER, "C")
        if self._enable[2]:
            self._register(HOTKEY_SETTINGS, "S")

        self._ready.set()
        print("Global shortcuts active: Ctrl+Alt+H (pause), Ctrl+Alt+C (recenter), Ctrl+Alt+S (settings).")

        try:
            while True:
                rc, msg = win32gui.GetMessage(0, 0, 0)
                if rc == 0 or rc == -1:
                    break
                win32gui.TranslateMessage(msg)
                win32gui.DispatchMessage(msg)
        finally:
            if self._hwnd:
                if self._enable[0]:
                    win32gui.UnregisterHotKey(self._hwnd, HOTKEY_TOGGLE)
                if self._enable[1]:
                    win32gui.UnregisterHotKey(self._hwnd, HOTKEY_RECENTER)
                if self._enable[2]:
                    win32gui.UnregisterHotKey(self._hwnd, HOTKEY_SETTINGS)
                win32gui.DestroyWindow(self._hwnd)
                self._hwnd = None

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_HOTKEY:
            if wparam == HOTKEY_TOGGLE:
                self._on_toggle()
            elif wparam == HOTKEY_RECENTER:
                self._on_recenter()
            elif wparam == HOTKEY_SETTINGS:
                self._on_settings()
            return 0
        if msg == win32con.WM_CLOSE:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
