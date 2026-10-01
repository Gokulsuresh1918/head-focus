# Head Focus

Head-tracked **monitor focus** for Windows. Turn your head left or right to move keyboard focus to the top window on that monitor. The mouse cursor is **not** moved.

Built with OpenCV, MediaPipe Face Landmarker, and the Windows API.

**Repository:** [github.com/Gokulsuresh1918/head-focus](https://github.com/Gokulsuresh1918/head-focus)

## Privacy

Head Focus runs **entirely on your machine**:

- Your webcam is used only for local head-pose tracking; frames are not sent to any Head Focus server.
- The only default network access is a **one-time download** of Google’s public MediaPipe model (`face_landmarker.task`) if it is not already on disk.
- Settings and calibration live in **`config.json`** on your PC (including `yaw_offset_deg` from Recenter). This file is **gitignored** and is never part of the public repository.
- **`check_camera.py`** can save `check_camera.jpg` locally for troubleshooting; that image is gitignored and may show your face—do not share or commit it.

For contributors: see [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Requirements

- Windows 10/11
- Python 3.10+
- Webcam
- Two or more monitors (optional; with one monitor the app runs but does not switch)

## Install

```bash
git clone https://github.com/Gokulsuresh1918/head-focus.git
cd head-focus
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On first run, `config.json` is created from `config.default.json` (this file stays on your machine and is not in git). The face model `face_landmarker.task` is downloaded automatically on first run and is also gitignored.

## Quick start

1. **Test the camera** (quit eViacam and other camera apps first):

   ```bash
   python check_camera.py
   ```

2. **Configure** (optional):

   ```bash
   python head_focus.py --settings
   ```

   Or open **Settings** from the system tray while the app is running.

3. **Run the app** (opens the dashboard with icon and controls):

   ```bash
   python head_focus.py
   ```

   Terminal-only mode: `python head_focus.py --console`

## Configuration

Settings are stored in **`config.json`** next to the application.

| Setting | Description |
|--------|-------------|
| `debug_preview` | Show live webcam overlay window |
| `show_tray_icon` | System tray icon (pause, recenter, settings, quit) |
| `camera_index` | Webcam device index (usually `0`) |
| `target_fps` | Tracking rate; lower uses less CPU |
| `yaw_threshold_deg` | Head turn angle to select side monitors |
| `hysteresis_deg` | Prevents flicker at zone boundaries |
| `dwell_seconds` | How long to hold a pose before switching |
| `yaw_offset_deg` | Calibration offset (updated by Recenter) |
| `smoothing` | Yaw smoothing (0–1) |
| `check_camera_on_start` | Run a quick camera test at startup |
| `warn_if_eviacam_running` | Warn when eViacam may block the webcam |

### Hotkeys (global)

- **Ctrl+Alt+H** — Pause / resume tracking  
- **Ctrl+Alt+C** — Recenter (save `yaw_offset_deg` to config)  
- **Ctrl+Alt+S** — Open settings  

## Run at Windows login

After `install_windows.bat`, press `Win+R`, type `shell:startup`, and put a shortcut to **`start_head_focus.bat`** (or **`Launch Head Focus.bat`**) in the folder that opens.

Use **Task Scheduler** with a 30-second delay if the camera is not ready immediately at login.

## Calibration

Look at your **centre monitor** (straight ahead) and press **Ctrl+Alt+C** or choose **Recenter** in the tray. The offset is saved to `config.json`.

## Troubleshooting

| Problem | What to try |
|--------|-------------|
| Black camera | Quit **eViacam**; run `check_camera.py`; allow **python.exe** / **pythonw.exe** in Settings → Privacy → Camera |
| Focus does not switch | Run terminal or app as administrator if the target app is elevated |
| Wrong monitor | Adjust `yaw_threshold_deg` and recenter |

## Project layout

```
head_focus.py        CLI entry, vision, focus switching
dashboard.py         GUI dashboard (default when run with no args)
tracking_engine.py   Background tracking session (tray, hotkeys)
settings_ui.py       Configuration window
ui_widgets.py        Shared Tkinter UI helpers
action_feedback.py   User action messages / toasts
config.py            Load/save config.json
config.default.json  Shipped defaults (no personal data)
check_camera.py      Camera diagnostic
startup_checks.py    Startup camera / eViacam checks
tray_ui.py           System tray
hotkeys.py           Global hotkeys
notifications.py     Windows toast notifications
app_resources.py     Icon paths and asset helpers
assets/icon.ico      Application icon
start_head_focus.bat Optional Windows startup helper
install_windows.bat   One-time setup for ZIP download users
Launch Head Focus.bat Double-click to run the dashboard
scripts/              Maintainer tools (release ZIP)
```

**Not in git (local only):** `config.json`, `face_landmarker.task`, `check_camera.jpg`, `.venv/`

## Publishing a release (maintainers)

So download-only users get a clean ZIP without cloning:

```powershell
cd head-focus
git tag v1.0.0
powershell -ExecutionPolicy Bypass -File scripts\make_release_zip.ps1
```

Upload `dist\head-focus-1.0.0.zip` (or `snapshot`) to **GitHub → Releases → New release**, attach the ZIP, and paste the “Download and run” steps from this README into the release notes.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. Report security concerns privately as described in [SECURITY.md](SECURITY.md).
