"""Load and save Head Focus user settings (JSON next to the app)."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, fields
from typing import Any

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(APP_DIR, "config.default.json")
USER_CONFIG_PATH = os.path.join(APP_DIR, "config.json")


@dataclass
class AppConfig:
    # General
    debug_preview: bool = False
    show_tray_icon: bool = True
    camera_index: int = 0
    target_fps: int = 15

    # Head tracking
    yaw_threshold_deg: float = 15.0
    hysteresis_deg: float = 4.0
    dwell_seconds: float = 0.25
    yaw_offset_deg: float = 0.0
    smoothing: float = 0.35

    # Startup / safety
    check_camera_on_start: bool = True
    warn_if_eviacam_running: bool = True
    exit_on_black_camera: bool = False

    # Hotkeys (Ctrl+Alt + letter); set enabled=false to disable
    hotkey_toggle_pause: bool = True
    hotkey_recenter: bool = True
    hotkey_open_settings: bool = True

    show_toast_notifications: bool = True
    notify_on_monitor_switch: bool = False

    @classmethod
    def defaults(cls) -> AppConfig:
        return cls()

    @classmethod
    def load(cls, path: str | None = None) -> AppConfig:
        path = path or USER_CONFIG_PATH
        if not os.path.isfile(path):
            ensure_user_config()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        cfg = cls.defaults()
        for key, value in filtered.items():
            setattr(cfg, key, value)
        return cfg

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str | None = None) -> None:
        path = path or USER_CONFIG_PATH
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
            f.write("\n")

    def save_yaw_offset(self) -> None:
        """Persist recentered yaw offset to config.json."""
        self.save()


def ensure_user_config() -> str:
    """Create config.json from config.default.json if missing."""
    if os.path.isfile(USER_CONFIG_PATH):
        return USER_CONFIG_PATH
    if os.path.isfile(DEFAULT_CONFIG_PATH):
        shutil.copy(DEFAULT_CONFIG_PATH, USER_CONFIG_PATH)
    else:
        AppConfig.defaults().save(USER_CONFIG_PATH)
    return USER_CONFIG_PATH
