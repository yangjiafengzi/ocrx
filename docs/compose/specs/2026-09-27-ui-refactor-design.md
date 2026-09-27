# OCRX UI Refactor Design

## [S1] Problem

OCRX 2.1 works, but the GUI layer blocks further product and performance work:

- `ocrx/gui/main_window.py` is a god object (~730 lines): widget construction,
  validation, service wiring, file dialogs, save/copy flows, and config IO.
- Handlers reach back into `MainWindow` for widgets, config, service, and
  status updates, so UI, business, and I/O remain tightly coupled.
- The current notebook layout dumps API config, few-shot examples, logs,
  clipboard history, and results into sibling tabs. The primary OCR workflow
  is not guided and the config page is dense.
- Visual language is hand-styled ttk (`ocrx/gui/theme.py`). The product needs
  a modern CustomTkinter look without abandoning the Windows desktop target.
- Performance is UI-bound under load: frequent progress callbacks, large
  result text, and eager example-image loading can stall the main thread.
- Existing GUI tests cover pieces, but not a complete user workflow from
  configuration through save/copy verification.

Goal: redesign the UI and refactor the GUI architecture while preserving the
existing processing core (`ProcessingService`, OCR/PDF/image modules), and
prove the result with full GUI end-to-end tests using only tiny generated
fixtures.

## [S2] Solution overview

Replace the notebook-centered GUI with a Workflow Wizard and a layered GUI
architecture.

```text
MainWindow (shell)
  ├── WizardNav
  ├── views/
  │     ├── config_step.py
  │     ├── files_step.py
  │     ├── prompt_step.py
  │     ├── run_step.py
  │     ├── examples_view.py
  │     ├── clipboard_view.py
  │     └── logs_view.py
  ├── controllers/
  │     ├── save_controller.py
  │     ├── copy_controller.py
  │     ├── prompt_controller.py
  │     └── progress_controller.py
  └── app_context.py
```

- `AppContext` owns `ConfigManager`, `ProcessingService`, `ExampleLibrary`,
  `ClipboardHistory`, and `StructuredLogger`, with injectable constructors.
- `MainWindow` only builds the shell, navigation, and lifecycle.
- Views render and emit semantic callbacks. They do not call OCR APIs or
  perform file IO.
- Controllers implement workflows and publish UI updates via `root.after`.
- Processing stays in `ocrx/processing_service.py` and related modules.

## [S3] Workflow Wizard

Primary path is four steps:

1. **Config** — Base URL, API key, model, output directory, workers, PDF scale.
2. **Files** — multi-select PDF/image files, page range, selected-file list.
3. **Prompt** — prompt preset editor plus few-shot example selection.
4. **Run** — save/copy actions, progress, result preview, stop/cancel.

Secondary surfaces stay available without interrupting the wizard:

- Example library manager
- Clipboard history
- Run logs

Navigation state and previously entered values persist across step changes
for the current session. Save Config remains explicit.

## [S4] Components

### [S4.1] AppContext

Fields/services:

- `config: ConfigManager`
- `service: ProcessingService | None` (recreated when credentials change)
- `examples: ExampleLibrary`
- `clipboard: ClipboardHistory`
- `logger: StructuredLogger`
- `session_state` for selected files, page range, selected example ids,
  current prompt text, and last result

### [S4.2] Views

Each view is a CustomTkinter frame factory/class with:

- `build(parent) -> widget`
- `read() -> dict` / `write(state)`
- callback registration for user intent

No view imports OpenAI, PyMuPDF, or writes config files.

### [S4.3] Controllers

- `SaveController` / `CopyController`: validate, call `ProcessingService`,
  handle cancel, emit progress/result/error events.
- `PromptController`: preset CRUD against `ConfigManager.prompt_templates`.
- `ProgressController`: coalesce progress callbacks onto the UI thread.

### [S4.4] Theme

CustomTkinter appearance/theme plus a small token module (colors, spacing,
typography). Remove large hand-rolled ttk style trees once widgets migrate.

## [S5] Data flow

```text
User action
  -> view callback
  -> controller
  -> ProcessingService (worker threads)
  -> progress/status/result events
  -> ProgressController (throttle/coalesce)
  -> root.after(...)
  -> view update
```

- API key stays encrypted at rest via existing `secret_store.py` DPAPI path.
- Prompt templates continue to originate in `ocrx/prompt_templates.py`.
- Example library remains under `~/.ocrx/example_library/`.
- Config file remains `~/.ocrx_gui_config.json`.

## [S6] Performance

- Throttle progress UI updates to at most ~10 Hz (or only on percent change).
- Cap result preview length; full content stays available to copy/save.
- Lazy-load example thumbnails; cache decoded preview images.
- Avoid rebuilding whole views when only lists/status change.
- Keep worker cancellation checks responsive; stop button clears running state.
- Do not use large binary fixtures in tests; generate tiny PNG/JPG/PDF.

## [S7] Error handling

- Preflight validation for missing API key/base URL/model, empty file list,
  unsupported extensions, and invalid page ranges.
- Unified error presenter: status bar short message + optional detail dialog.
- Background exceptions become error events; they never crash `mainloop`.
- After cancel or failure, controls unlock and the wizard returns to a stable
  state ready for retry.

## [S8] Testing

- Unit tests for AppContext wiring, validation, controllers, throttling.
- Component tests for individual views with real widgets where display is
  available, otherwise headless fakes consistent with existing tests.
- Full GUI E2E (`tests/test_gui_e2e.py` or similar):
  1. Start app with temp config/example paths and mock OpenAI server.
  2. Walk wizard: config -> files -> prompt -> run.
  3. Execute save mode and assert markdown output.
  4. Execute copy mode and assert clipboard content.
  5. Cover cancel/failure path without external network.
- Fixtures must be generated in-test: small RGB PNG and 1-3 page PDF.
- Target: individual tests < 2s, full GUI e2e suite < 60s.

## [S9] Compatibility and packaging

- Add `customtkinter` to `requirements.txt`.
- Update `build_package.bat` hidden imports/collect for customtkinter.
- Keep public processing APIs stable; GUI import path remains
  `ocrx.gui.main_window.MainWindow` for `main.py`.
- Preserve UTF-8 source convention and Chinese UI copy unless a string is
  being deliberately rewritten.

## [S10] Out of scope

- Rewriting OCR/PDF/image processing algorithms.
- Non-Windows GUI backends.
- Cloud packaging/signing pipeline changes.
- Broad style-only cleanup outside GUI modules touched by this work.
