"""App icon and shared paths."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(APP_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "icon.ico")


def ensure_app_icon() -> str:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.isfile(ICON_PATH):
        return ICON_PATH
    sizes = [(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    for size in sizes:
        s = size[0]
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = max(2, s // 16)
        draw.ellipse((margin, margin, s - margin, s - margin), fill="#1a5fb4")
        eye_y = s // 3
        draw.ellipse((s // 4, eye_y, s // 2, eye_y + s // 6), fill="white")
        draw.ellipse((s // 2 + s // 16, eye_y, 3 * s // 4, eye_y + s // 6), fill="white")
        draw.rounded_rectangle(
            (s // 4, 2 * s // 3, 3 * s // 4, s - margin),
            radius=max(2, s // 20),
            fill="#3584e4",
        )
        images.append(img)
    images[0].save(ICON_PATH, format="ICO", sizes=[(im.width, im.height) for im in images])
    return ICON_PATH
