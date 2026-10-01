"""Messages shown when the user triggers an action or shortcut."""

from __future__ import annotations

from dataclasses import dataclass

# key -> (title, what happens, how to undo)
ACTION_TEXT: dict[str, tuple[str, str, str]] = {
    "start": (
        "Tracking started",
        "Head focus will move to the window on the monitor you look at.",
        "Undo: click Stop or close this window.",
    ),
    "stop": (
        "Tracking stopped",
        "Your head will no longer change monitor focus.",
        "Undo: click Start.",
    ),
    "pause": (
        "Paused",
        "Focus will stay where it is; your head is ignored for now.",
        "Undo: press Ctrl+Alt+H or click Resume.",
    ),
    "resume": (
        "Resumed",
        "Head tracking is active again.",
        "Undo: press Ctrl+Alt+H to pause again.",
    ),
    "recenter": (
        "Recentered",
        "This head pose is now straight-ahead (0 degrees).",
        "Undo: look at centre monitor and press Ctrl+Alt+C again, or edit Yaw offset in Settings.",
    ),
    "settings": (
        "Settings opened",
        "Change options there, then Save.",
        "Restart tracking if you changed camera or speed settings.",
    ),
    "recenter_need_start": (
        "Recenter",
        "Start tracking first, then look at the centre monitor and press Ctrl+Alt+C.",
        "",
    ),
}


@dataclass
class ActionNotice:
    key: str
    title: str
    detail: str
    undo: str

    @classmethod
    def from_key(cls, key: str) -> ActionNotice:
        title, detail, undo = ACTION_TEXT[key]
        return cls(key=key, title=title, detail=detail, undo=undo)

    def toast_body(self) -> str:
        if self.undo:
            return f"{self.detail}\n\nUndo: {self.undo.replace('Undo: ', '')}"
        return self.detail

    def window_lines(self) -> str:
        if self.undo:
            return f"{self.detail}\n{self.undo}"
        return self.detail
