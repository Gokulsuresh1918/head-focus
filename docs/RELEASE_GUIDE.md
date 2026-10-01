# Head Focus — release & distribution guide

This doc is for **you (maintainer)** publishing downloads and **users** installing from GitHub Releases.

**Download page for users:** https://github.com/Gokulsuresh1918/head-focus/releases

---

## Part 1 — Publish a release (maintainer)

### Prerequisites

- Code merged on **`main`** (or the branch you treat as stable).
- [Git](https://git-scm.com/) installed; repo remote `origin` → GitHub.
- Optional: [GitHub CLI (`gh`)](https://cli.github.com/) for releases from the terminal.

### Option A — Automatic (recommended)

When you push a **version tag**, GitHub Actions builds `head-focus-<version>.zip` and attaches it to a Release.

1. **Commit and push** your latest changes:

   ```powershell
   cd "D:\gokul files\Projects\eye tracking"
   git status
   git add -A
   git commit -m "Prepare release v1.0.0"
   git push origin main
   ```

2. **Create and push a tag** (use [semver](https://semver.org/): `v1.0.0`, `v1.0.1`, …):

   ```powershell
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. Open **GitHub → Actions** → wait for **Release** workflow (green).

4. Open **Releases** — you should see **v1.0.0** with **`head-focus-1.0.0.zip`** attached.

5. **Edit the release** (optional): add screenshots, copy the user steps from [Part 2](#part-2--install-for-users) into the description.

### Option B — Manual ZIP + upload

1. On a clean checkout (no personal `config.json` in the folder you zip):

   ```powershell
   git checkout main
   git pull
   git tag v1.0.0   # if not already tagged
   powershell -ExecutionPolicy Bypass -File scripts\make_release_zip.ps1
   ```

2. GitHub → **Releases** → **Draft a new release**  
   - Tag: `v1.0.0`  
   - Title: `Head Focus 1.0.0`  
   - Attach: `dist\head-focus-1.0.0.zip` (or `head-focus-snapshot.zip` if untagged)

3. **Publish release**.

### Using GitHub CLI (manual release)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_release_zip.ps1
gh release create v1.0.0 dist/head-focus-1.0.0.zip --title "Head Focus 1.0.0" --notes-file docs/RELEASE_NOTES_TEMPLATE.md
```

### Checklist before each release

- [ ] README “Download and run” steps still match the batch files.
- [ ] `requirements.txt` installs on a fresh Windows VM or second PC.
- [ ] Version tag matches zip name (`v1.0.0` → `head-focus-1.0.0.zip`).
- [ ] No secrets in the zip (`config.json`, `.env`, camera test images).

---

## Part 2 — Install (users)

Share this link: **https://github.com/Gokulsuresh1918/head-focus/releases/latest**

1. Download **`head-focus-X.Y.Z.zip`** from the latest release (not “Source code” unless they use Git).
2. Unzip to a folder, e.g. `C:\Apps\head-focus`.
3. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/) — check **Add python.exe to PATH**.
4. Double-click **`install_windows.bat`** once (internet required).
5. Double-click **`Launch Head Focus.bat`**.
6. Allow **Camera** for `python.exe` / `pythonw.exe` when Windows asks.
7. In the app: **Test camera** → **Start**. Look at a monitor to move focus.

**Recenter:** look at the centre monitor → **Ctrl+Alt+C** or **Recenter** in the app.

---

## Part 3 — Later: `.exe`, winget, Microsoft Store

Today’s release is **Python + ZIP**. For “no Python” and **`winget install`**, ship a **Windows installer or portable `.exe`** first.

| Stage | What | Doc |
|-------|------|-----|
| Now | GitHub Releases ZIP | This file, Part 1–2 |
| Next | PyInstaller (or similar) `.exe` on Releases | [PACKAGING.md](PACKAGING.md) |
| Then | **winget** community package | [WINGET.md](WINGET.md) |
| Later | **Microsoft Store** (MSIX + partner account) | [WINGET.md](WINGET.md#microsoft-store-roadmap) |

You do **not** need the Store or winget to start sharing; Releases are enough for open source.

---

## Troubleshooting releases

| Issue | Fix |
|-------|-----|
| Action failed on tag push | Repo → **Settings → Actions → General** → allow workflows; check **Actions** tab log. |
| Zip is `snapshot` | Tag the commit (`git tag v1.0.0`) before running the script, or push the tag for CI. |
| Users download “Source code” | Point them to the **Assets** section and `head-focus-*.zip`. |
| Duplicate Python apps running | Use only **`Launch Head Focus.bat`** (`.venv`), not global `python head_focus.py`. |
