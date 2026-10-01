# Head Focus

Head-tracked **monitor focus** for Windows. Turn your head left or right to move keyboard focus to the top window on that monitor. The mouse cursor is **not** moved.

Built with OpenCV, MediaPipe Face Landmarker, and the Windows API.

**Repository:** [github.com/Gokulsuresh1918/head-focus](https://github.com/Gokulsuresh1918/head-focus)

## Privacy

Head Focus runs **entirely on your machine**:

- Your webcam is used only for local head-pose tracking; frames are not sent to any Head Focus server.
- The only default network access is a **one-time download** of Google’s public MediaPipe model (`face_landmarker.task`) if it is not already on disk.
- Settings and calibration live in **`config.json`** on your PC (including `yaw_offset_deg` from Recenter). This file is **gitignored** and is never part of the public repository.
- **Test camera** in the app shows **live video only** — nothing is written to disk. The CLI `check_camera.py` does not save images unless you pass **`--save`** (optional `check_camera.jpg`, gitignored).

For contributors: see [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Requirements

- Windows 10/11
- Webcam
- **Python 3.10+** ([python.org/downloads](https://www.python.org/downloads/) — enable **Add python.exe to PATH**)
- Two or more monitors (optional; with one monitor the app runs but does not switch)

---

## Download and run (no Git)

For users who only want to **download and use** the app:

1. **Get the files**
   - **Recommended:** [Releases](https://github.com/Gokulsuresh1918/head-focus/releases) → download the latest `head-focus-….zip` (when published), **or**
   - On the repo page: **Code** → **Download ZIP**, then unzip to a folder (e.g. `C:\Apps\head-focus`).

2. **One-time setup** — double-click **`install_windows.bat`** (creates `.venv`, installs packages; needs internet once).

3. **Run** — double-click **`Launch Head Focus.bat`**. Use **Test camera**, then **Start**.

4. **Permissions** — allow **Camera** for `python.exe` / `pythonw.exe`. On first **Start**, the face model downloads once (~10 MB).

| File | Purpose |
|------|---------|
| `install_windows.bat` | First-time setup (run once) |
| `Launch Head Focus.bat` | Start the dashboard (daily use) |
| `start_head_focus.bat` | For Startup folder shortcuts |

On first run, `config.json` is created from `config.default.json` in your install folder (not in git).

---

## Developers: clone and install

```bash
git clone https://github.com/Gokulsuresh1918/head-focus.git
cd head-focus
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python head_focus.py
```

## Quick start (after setup)

1. Open the dashboard (`Launch Head Focus.bat` or `python head_focus.py`).
2. Click **Test camera** — live preview in the window (click again to stop).
3. Click **Start** — look at a monitor to move focus.
4. **Settings** (link or **Ctrl+Alt+S** while running) for sensitivity and camera index.

Terminal-only: `python head_focus.py --console` · Settings only: `python head_focus.py --settings`

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

## Host a download link (Vercel)

Head Focus **cannot run on Vercel** — it needs Windows, a webcam, and local Python. Vercel is only for a **landing page** with download buttons.

1. Push this repo to GitHub (includes the `website/` folder).
2. Sign in at [vercel.com](https://vercel.com) → **Add New Project** → import **head-focus**.
3. Set **Root Directory** to `website` (Framework Preset: **Other**, no build command).
4. Deploy. You get a URL like `https://head-focus.vercel.app` to share.

Point the green button at a real file: publish a ZIP under [GitHub Releases](https://github.com/Gokulsuresh1918/head-focus/releases) (see below). Until then, users can use the “Source ZIP” button on the landing page.

## Publishing a release (maintainers)

**Step-by-step guide:** [docs/RELEASE_GUIDE.md](docs/RELEASE_GUIDE.md)

**Quick path:** push tag `v1.0.0` → GitHub Actions builds `head-focus-1.0.0.zip` → appears on [Releases](https://github.com/Gokulsuresh1918/head-focus/releases).

```powershell
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

Manual ZIP: `powershell -ExecutionPolicy Bypass -File scripts\make_release_zip.ps1`

**Later:** `.exe` + winget + Store → [docs/PACKAGING.md](docs/PACKAGING.md), [docs/WINGET.md](docs/WINGET.md)

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. Report security concerns privately as described in [SECURITY.md](SECURITY.md).
