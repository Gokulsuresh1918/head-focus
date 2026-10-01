"""Quick webcam check — run this before head_focus.py.

Prints whether frames look usable. Does not save images unless you pass --save.
"""

import argparse
import os
import sys

import cv2
import numpy as np

from startup_checks import MIN_FRAME_MEAN

ATTEMPTS = (
    ("YUY2 1920x1080", {"fourcc": None, "w": 1920, "h": 1080}),
    ("YUY2 640x480", {"fourcc": None, "w": 640, "h": 480}),
    ("MJPG 640x480", {"fourcc": "MJPG", "w": 640, "h": 480}),
)


def _parent_hint():
    if any("cursor" in (os.environ.get(k) or "").lower() for k in ("CURSOR", "VSCODE", "TERM_PROGRAM")):
        return "Cursor"
    return "python.exe"


def try_capture(index=0):
    for label, opts in ATTEMPTS:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            continue
        if opts["fourcc"]:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*opts["fourcc"]))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, opts["w"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, opts["h"])
        frame = None
        for _ in range(40):
            ok, frame = cap.read()
            if not ok:
                break
        cap.release()
        if frame is None:
            continue
        mean = float(frame.mean())
        print(f"  {label}: shape={frame.shape} brightness={mean:.1f} max={frame.max()}")
        if mean >= MIN_FRAME_MEAN:
            return frame, label
    return None, None


def main():
    parser = argparse.ArgumentParser(description="Test webcam without saving unless --save is used.")
    parser.add_argument("--save", action="store_true", help="Write check_camera.jpg (optional diagnostic)")
    args = parser.parse_args()

    exe = _parent_hint()
    print(f"Testing camera index 0 (allow camera for {exe} in Windows Settings).\n")
    frame, label = try_capture(0)
    if frame is None:
        print("\nNo usable video - all attempts were black or failed.")
        print("1. Open the Windows Camera app — if that is black too, fix the driver/USB/lens.")
        print(f"2. Settings > Privacy & security > Camera > enable for {exe} and desktop apps.")
        print("3. Quit Zoom, Teams, and other apps that might hold the camera.")
        try:
            os.startfile("ms-settings:privacy-webcam")
            print("   (Opened Camera privacy settings.)")
        except OSError:
            pass
        sys.exit(1)

    ok_label = label or "OK"
    print(f"\nOK ({ok_label}). Use Test camera in Head Focus for a live preview (nothing is saved).")
    if args.save and frame is not None:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_camera.jpg")
        cv2.imwrite(out, frame)
        print(f"Saved {out} (--save). Delete this file when done if you do not want a local snapshot.")


if __name__ == "__main__":
    main()
