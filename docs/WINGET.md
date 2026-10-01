# winget & Microsoft Store (roadmap)

Use this **after** you ship a **signed or trusted `.exe`/`.msi`** on GitHub Releases. Until then, users install via ZIP + `install_windows.bat`.

---

## winget (Windows Package Manager)

**User experience (goal):**

```powershell
winget install Gokulsuresh1918.HeadFocus
```

### Steps (summary)

1. **Build an installer** — see [PACKAGING.md](PACKAGING.md) (PyInstaller + optional Inno Setup `.exe`).
2. **Host the installer** on a **stable URL** — usually GitHub Release asset, e.g.  
   `https://github.com/Gokulsuresh1918/head-focus/releases/download/v1.0.0/HeadFocus-Setup-1.0.0.exe`
3. **Compute SHA256** of the installer:

   ```powershell
   Get-FileHash .\HeadFocus-Setup-1.0.0.exe -Algorithm SHA256
   ```

4. **Submit a manifest** to the community repo [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs):
   - Fork → add folder `manifests/g/Gokulsuresh1918/HeadFocus/1.0.0/`
   - Files: `Gokulsuresh1918.HeadFocus.yaml`, locale YAML, installer YAML
   - Open PR; Microsoft validators must pass.

5. After merge, users can `winget search HeadFocus` and install.

### Manifest starter

Copy and edit `winget/manifests/Gokulsuresh1918.HeadFocus.installer.yaml` when you have a real installer URL and hash.

**Publisher ID:** use a stable identifier (`Gokulsuresh1918.HeadFocus`) and keep it forever.

---

## Microsoft Store roadmap

| Step | Notes |
|------|--------|
| [Partner Center account](https://partner.microsoft.com/dashboard) | One-time registration (~$19 for individual dev, varies) |
| Package as **MSIX** | Often built from same binaries as `.exe`; needs icons, identity |
| **Code signing** | Store signing or your cert for desktop bridge |
| Privacy policy URL | Required; can be GitHub `PRIVACY.md` on your repo |
| Store listing | Screenshots, description, age rating |
| Review | 1–7+ days; camera apps need clear privacy explanation |

Store builds **do not replace** GitHub Releases for open-source power users; many projects use **both** (Store for discovery, GitHub for ZIP/source).

---

## Order of operations (recommended)

1. **GitHub Releases ZIP** — live now  
2. **Portable or setup `.exe` on Releases**  
3. **winget** manifest pointing at Release URL  
4. **Microsoft Store** when you want billing/discovery and can maintain MSIX updates  
