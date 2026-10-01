"""App icon and shared paths."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(APP_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PNG_PATH = os.path.join(ASSETS_DIR, "icon.png")


def _png_to_ico() -> None:
    from PIL import Image

    img = Image.open(ICON_PNG_PATH).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    sizes = [256, 64, 48, 32, 16]
    icons = [img.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
    icons[0].save(ICON_PATH, format="ICO", sizes=[(s, s) for s in sizes])


def ensure_app_icon() -> str:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.isfile(ICON_PNG_PATH):
        if not os.path.isfile(ICON_PATH) or os.path.getmtime(ICON_PNG_PATH) > os.path.getmtime(ICON_PATH):
            _png_to_ico()
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
