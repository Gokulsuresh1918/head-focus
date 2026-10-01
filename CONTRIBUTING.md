# Contributing to Head Focus

Thank you for helping improve Head Focus. This project is open source under the [MIT License](LICENSE).

## Ways to contribute

- **Bug reports** — Open an issue with steps to reproduce, Windows version, monitor setup, and camera model if relevant.
- **Feature ideas** — Open an issue describing the use case before large changes.
- **Pull requests** — Fix bugs, improve docs, or add features that fit the project scope (Windows head-tracked **monitor focus**, not mouse/eye-pointer control).

## Development setup

```bash
git clone https://github.com/Gokulsuresh1918/head-focus.git
cd head-focus
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python check_camera.py
python head_focus.py
```

On first run, `config.json` and `face_landmarker.task` are created locally and are **not** committed (see `.gitignore`).

## Code guidelines

- Match existing style: type hints where used, small focused changes, minimal scope per PR.
- Do **not** commit personal or machine-specific data (`config.json`, webcam snapshots, `.venv/`, secrets).
- Test on Windows with a webcam when touching camera, tracking, or focus-switching code.
- Update `README.md` if user-facing behavior or configuration changes.

## Pull request checklist

- [ ] Change is limited to the described problem or feature
- [ ] No secrets, tokens, or local paths in the diff
- [ ] No `config.json`, `check_camera.jpg`, or `face_landmarker.task` in the commit
- [ ] README or comments updated if behavior changed

## Reporting security issues

Do **not** open public issues for security vulnerabilities. See [SECURITY.md](SECURITY.md).

## Questions

Open a [GitHub Discussion](https://github.com/Gokulsuresh1918/head-focus/discussions) or an issue if Discussions are not enabled.
