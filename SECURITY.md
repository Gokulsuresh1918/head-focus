# Security Policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch. There are no long-term support branches yet.

| Version | Supported |
| ------- | --------- |
| Latest `main` | Yes |
| Older commits | Best effort |

## Reporting a vulnerability

If you believe you have found a security issue in Head Focus:

1. **Do not** open a public GitHub issue with exploit details.
2. Email or contact the maintainer via GitHub (profile: [Gokulsuresh1918](https://github.com/Gokulsuresh1918)) with:
   - Description of the issue
   - Steps to reproduce
   - Impact assessment
   - Optional patch or fix suggestion

We will acknowledge receipt and work on a fix as soon as practical.

## Privacy and webcam data

Head Focus is designed to process video **locally on your PC**:

- Webcam frames are used for head-pose estimation (MediaPipe Face Landmarker + OpenCV).
- Video is **not** uploaded to Head Focus servers — there are no project-owned backend services.
- The only routine network fetch is downloading the public MediaPipe model file (`face_landmarker.task`) from Google storage on first run, if the file is missing.

**Local data that may contain sensitive information:**

| File | Risk | In git? |
|------|------|--------|
| `config.json` | Calibration (`yaw_offset_deg`) and preferences | No (gitignored) |
| `check_camera.jpg` | Snapshot from your webcam during diagnostics | No (gitignored) |
| Debug preview window | Live video on screen when enabled | User-controlled setting |

**Contributors:** Never commit `config.json`, diagnostic images, or recordings. See [CONTRIBUTING.md](CONTRIBUTING.md).

**Users:** Grant camera access only to Python/`pythonw.exe` you trust. Review Windows **Settings → Privacy & security → Camera**. Quit other apps that exclusive-lock the webcam (e.g. some assistive tools).

## Permissions and Windows integration

The app uses Win32 APIs to:

- Switch keyboard focus between top-level windows on different monitors
- Register global hotkeys (Ctrl+Alt+H/C/S)
- Show system tray and toast notifications

Running as **Administrator** may be required to focus windows that are elevated. Only elevate if you understand the trust implications.

## Dependencies

Keep dependencies updated via `pip install -r requirements.txt` and report issues in upstream packages (OpenCV, MediaPipe, pywin32) when appropriate.
