"""System tray icon for Head Focus."""

from __future__ import annotations

import threading
from typing import Callable

from PIL import Image, ImageDraw

from app_resources import ICON_PATH, ensure_app_icon

try:
    import pystray
except ImportError:
    pystray = None


def _make_icon_image(running: bool) -> Image.Image:
    ensure_app_icon()
    try:
        img = Image.open(ICON_PATH).convert("RGBA")
    except OSError:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((8, 8, 56, 56), fill=(46, 204, 113) if running else (231, 76, 60))
    if not running:
        overlay = Image.new("RGBA", img.size, (231, 76, 60, 120))
        img = Image.alpha_composite(img, overlay)
    return img


class TrayController:
    def __init__(
        self,
        get_paused: Callable[[], bool],
        on_toggle_pause: Callable[[], None],
        on_recenter: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        self._get_paused = get_paused
        self._on_toggle_pause = on_toggle_pause
        self._on_recenter = on_recenter
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit
        self._icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if pystray is None:
            print("Tray icon unavailable: install pystray and Pillow (pip install -r requirements.txt)")
            return False
        self._thread = threading.Thread(target=self._run, name="TrayIcon", daemon=True)
        self._thread.start()
        return True

    def refresh(self) -> None:
        if self._icon:
            paused = self._get_paused()
            self._icon.icon = _make_icon_image(not paused)
            self._icon.title = "Head Focus (paused)" if paused else "Head Focus (tracking)"

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()

    def _run(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Pause / Resume", self._toggle, default=True),
            pystray.MenuItem("Recenter", self._recenter),
            pystray.MenuItem("Settings", self._settings),
            pystray.MenuItem("Quit", self._quit),
        )
        self._icon = pystray.Icon(
            "head_focus",
            _make_icon_image(True),
            "Head Focus",
            menu,
        )
        self._icon.run()

    def _toggle(self, _icon, _item):
        self._on_toggle_pause()
        self.refresh()

    def _recenter(self, _icon, _item):
        self._on_recenter()

    def _settings(self, _icon, _item):
        self._on_open_settings()

    def _quit(self, _icon, _item):
        self._on_quit()
