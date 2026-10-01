"""On-screen toast notifications for Head Focus."""

from __future__ import annotations

import threading

from app_resources import ICON_PATH, ensure_app_icon

_toast_lock = threading.Lock()


def notify(title: str, message: str, enabled: bool = True) -> None:
    if not enabled:
        return
    threading.Thread(
        target=_show_toast,
        args=(title, message),
        name="HeadFocusToast",
        daemon=True,
    ).start()


def _show_toast(title: str, message: str) -> None:
    with _toast_lock:
        icon = ensure_app_icon()
        try:
            from winotify import Notification

            toast = Notification(app_id="Head Focus", title=title, msg=message, icon=icon)
            toast.set_duration("short")
            toast.show()
            return
        except Exception:
            pass
        _tk_toast(title, message)


def _tk_toast(title: str, message: str) -> None:
    try:
        import tkinter as tk
    except ImportError:
        print(f"{title}: {message}")
        return

    root = tk.Tk()
    root.withdraw()
    toast = tk.Toplevel(root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.configure(bg="#1a5fb4", padx=16, pady=12)
    tk.Label(toast, text=title, fg="white", bg="#1a5fb4", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    tk.Label(toast, text=message, fg="#dce8f5", bg="#1a5fb4", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
    toast.update_idletasks()
    sw = toast.winfo_screenwidth()
    tw = toast.winfo_width()
    toast.geometry(f"+{sw - tw - 24}+24")
    toast.after(2800, lambda: (toast.destroy(), root.destroy()))
    root.mainloop()
