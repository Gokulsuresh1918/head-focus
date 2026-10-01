# Head Focus

Head-tracked **monitor focus** for Windows. Turn your head left or right to move keyboard focus to the top window on that monitor. The mouse cursor is **not** moved.

Built with OpenCV, MediaPipe Face Landmarker, and the Windows API.

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

Create `start_head_focus.bat`:

```bat
@echo off
cd /d "%~dp0"
start "" /min ".venv\Scripts\pythonw.exe" head_focus.py
```

Press `Win+R`, type `shell:startup`, and place a shortcut to that batch file in the folder that opens.

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
```

**Not in git (local only):** `config.json`, `face_landmarker.task`, `check_camera.jpg`, `.venv/`

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Pull requests welcome. Open an issue for bugs or feature ideas.
