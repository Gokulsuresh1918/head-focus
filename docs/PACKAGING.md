# Building a Windows `.exe` (future)

Goal: users **without Python** double-click **HeadFocus.exe** or **Setup.exe** from GitHub Releases.

## Approach

1. **PyInstaller** (one-folder or one-file) bundling:
   - `head_focus.py`, `dashboard.py`, dependencies (OpenCV, MediaPipe, pywin32, …)
   - `assets/`, `config.default.json`
2. **Inno Setup** or **WiX** — optional wrapper `HeadFocus-Setup-1.0.0.exe` for Start Menu shortcuts.
3. Upload to **GitHub Releases**; update **winget** manifest URL + SHA256.

## Rough PyInstaller command (experiment on your PC)

```powershell
cd "D:\gokul files\Projects\eye tracking"
.\.venv\Scripts\pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe --noconfirm --windowed --name HeadFocus `
  --add-data "assets;assets" --add-data "config.default.json;." `
  head_focus.py
```

MediaPipe + OpenCV often need **hidden imports** and **collect-all** hooks; expect trial and error. Test on a PC **without** Python installed.

## Code signing (recommended before Store/winget wide trust)

- **Cert:** Authenticode certificate (commercial CA) for `.exe` / `.msi`
- Reduces SmartScreen “Unknown publisher” warnings

When you have a working spec file, add `head_focus.spec` to the repo and a `scripts/build_exe.ps1` script.
