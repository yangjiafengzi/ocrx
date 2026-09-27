# AGENTS.md

Windows desktop OCR app (customtkinter wizard GUI on tkinter) that sends
PDF/pages as images to an OpenAI-compatible vision API. Single Python
package, no monorepo.

## Commands

```bash
pip install -r requirements.txt -r requirements-dev.txt
python main.py
python -m pytest
python -m pytest tests/test_config.py
python -m pytest tests/test_config.py::test_defaults
python -m ruff check ocrx tests
python -m coverage run -m pytest
python -m coverage report --include="ocrx/*"
```

- CI (`.github/workflows/ci.yml`) runs only `python -m pytest` on
  `windows-latest` / Python 3.12. Ruff and coverage are not in CI.
- `pytest.ini` already sets `testpaths = tests` and `pythonpath = .`.
- Runtime deps live in `requirements.txt`; `requirements-dev.txt` adds
  pytest, coverage, and ruff. There is no ruff config file.
- Ruff is not a clean gate today (`python -m ruff check ocrx tests` reports
  hundreds of existing style findings). Do not block a change on making the
  whole tree ruff-clean unless that is the actual task.

## Architecture

- Flow: wizard views (`ocrx/gui/views/*`, driven by `MainWindow` as the
  wizard shell) and `ocrx/gui/controllers/*` -> `ProcessingService` ->
  `OCREngine` -> `OCRClient` (OpenAI SDK, created lazily). There is no
  `ocrx/gui/handlers/` anymore.
- `import ocrx` must not load PyMuPDF/`fitz`. PDF support goes through
  `ocrx.get_pdf_processor()`; `tests/test_lazy_import.py` enforces this.
- Default prompt templates are defined only in `ocrx/prompt_templates.py`.
- User data (never write these into the repo in tests):
  - config: `~/.ocrx_gui_config.json` (README/older docs say
    `.ocrx_config.json` - that is stale)
  - API key: stored as `API_KEY_ENC` via Windows DPAPI in
    `ocrx/secret_store.py`
  - few-shot examples: `~/.ocrx/example_library/`
  - log: `~/.ocrx_gui.log`

## Testing

- Fixtures in `tests/conftest.py`: `sample_png`, `sample_jpg`, `sample_gif`,
  `sample_rgba_png`, `sample_pdf`.
- `tests/test_e2e.py` starts a local mock OpenAI-compatible HTTP server; no
  external network or real API key.
- GUI tests skip when Tcl/Tk cannot open a display. `tests/test_ui_window.py`
  is intended for a full-Tcl/Tk Python (e.g. Miniconda), not a bare embed.
- `tests/test_secret_store.py` skips the real DPAPI round-trip off Windows.
- Prefer `tmp_path` / monkeypatched `ConfigManager` and `ExampleLibrary`
  paths so tests never touch the real home-directory files above.

## Build / release

- `build_package.bat` is the real packaging entrypoint (PyInstaller onefile
  -> optional Inno Setup). It strips a WinGet Poppler `Library\bin` entry
  from `PATH` so `libexpat.dll` does not get bundled by accident, and it
  passes `--hidden-import=customtkinter` plus `--collect-all=customtkinter`
  so the wizard UI ships inside the onefile exe.
- `clean.bat` deletes `build/`, `dist/`, `installer/`, `*.spec`, root-level
  `test_*.py`, logs, and some generated markdown. Do not run it blindly
  while keeping local scratch files.
- Version is duplicated in `ocrx/__init__.py`, `installer.iss`, and
  `CHANGELOG.md` (and often README). Keep them in sync on release.

## Conventions / gotchas

- Sources are UTF-8 with Chinese UI strings and comments; keep file encoding
  and add the existing `# -- coding: utf-8 --` header on new modules.
- Trust executable config over prose. `docs/DEVELOPMENT.md` and
  `VERSION_MANAGEMENT.md` still mention Black/Flake8/MyPy, `build_all.bat`,
  and `setup.py`; the repo actually uses ruff + `build_package.bat` and has
  no setuptools packaging.
- `requirements.txt` includes `pyinstaller` even though it is packaging-only.
- Top-level `*.spec` files are packaging artifacts; do not hand-edit them
  unless investigating the PyInstaller build.
