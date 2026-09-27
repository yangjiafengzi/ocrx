# OCRX UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the OCRX GUI as a CustomTkinter Workflow Wizard with layered views/controllers, then prove save/copy flows with full GUI end-to-end tests using tiny generated fixtures.

**Architecture:** Thin `MainWindow` shell + wizard views + controllers over `AppContext`. Processing APIs in `ocrx/processing_service.py` stay stable. UI updates from workers are marshalled through a throttled `ProgressController` using `root.after`.

**Tech Stack:** Python 3.12/3.13, tkinter, CustomTkinter, pytest, existing openai/PyMuPDF/Pillow stack.

## Global Constraints

- Preserve processing APIs: `ProcessingService.process_files`, `process_and_copy`, `request_cancel`, progress/status callbacks.
- Config path remains `~/.ocrx_gui_config.json`; example library remains `~/.ocrx/example_library/`.
- API key stays encrypted as `API_KEY_ENC` via `ocrx/secret_store.py`.
- Default prompt source of truth: `ocrx/prompt_templates.py`.
- `import ocrx` must not import `fitz`/`PyMuPDF` (lazy PDF import preserved).
- Tests must generate tiny fixtures in-process (small PNG/JPG, 1-3 page PDF). Never add large binaries.
- Target: single test < 2s; GUI e2e suite < 60s.
- Keep UTF-8 Chinese UI copy; new Python modules start with `# -- coding: utf-8 --`.
- Windows is the supported platform for GUI e2e and DPAPI.

---

### Task 1: Add CustomTkinter dependency and theme tokens

**Covers:** S2, S4.4, S9

**Files:**
- Modify: `requirements.txt`
- Create: `ocrx/gui/theme_tokens.py`
- Test: `tests/test_theme_tokens.py`

**Interfaces:**
- Produces: `theme_tokens.COLORS: dict[str, str]`, `theme_tokens.SPACING: dict[str, int]`, `theme_tokens.FONT`, `theme_tokens.apply_appearance()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_theme_tokens.py
# -- coding: utf-8 --
from ocrx.gui import theme_tokens as tt


def test_color_tokens_are_hex():
    for value in tt.COLORS.values():
        assert value.startswith("#") and len(value) == 7


def test_apply_appearance_is_idempotent():
    tt.apply_appearance()
    tt.apply_appearance()
    assert tt.FONT[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_theme_tokens.py -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Write implementation**

```python
# requirements.txt
openai>=1.0.0
PyMuPDF>=1.23.0
Pillow>=10.0.0
customtkinter>=5.2.0
pyinstaller>=5.0.0
```

```python
# ocrx/gui/theme_tokens.py
# -- coding: utf-8 --
"""CustomTkinter visual tokens."""

import customtkinter as ctk

COLORS = {
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "bg": "#F1F5F9",
    "surface": "#FFFFFF",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "success": "#16A34A",
    "danger": "#DC2626",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
FONT = ("Microsoft YaHei UI", 12)


def apply_appearance() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_theme_tokens.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt ocrx/gui/theme_tokens.py tests/test_theme_tokens.py
git commit -m "feat(gui): add customtkinter and theme tokens"
```

---

### Task 2: Session state and preflight validation

**Covers:** S2, S4.1, S7

**Files:**
- Create: `ocrx/gui/session_state.py`
- Create: `ocrx/gui/validation.py`
- Test: `tests/test_session_state.py`
- Test: `tests/test_validation.py`

**Interfaces:**
- Produces:
  - `SessionState` dataclass fields: `file_paths: list[str]`, `page_range: str`, `selected_example_ids: list[str]`, `prompt_text: str`, `output_dir: str`, `last_result: str`.
  - `validate_preflight(config: dict, file_paths: list[str], page_range: str) -> list[str]`.
  - `parse_page_range(page_range: str, total_pages: int) -> list[int] | None`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_session_state.py
# -- coding: utf-8 --
from ocrx.gui.session_state import SessionState


def test_session_state_defaults():
    state = SessionState()
    assert state.file_paths == []
    assert state.page_range == ""
    assert state.selected_example_ids == []
    assert state.last_result == ""
```

```python
# tests/test_validation.py
# -- coding: utf-8 --
from ocrx.gui.validation import parse_page_range, validate_preflight


def test_validate_preflight_missing_fields():
    errors = validate_preflight({"API_KEY": "", "BASE_URL": "", "MODEL_NAME": ""}, [], "")
    assert any("API" in e or "Base" in e or "Model" in e for e in errors)
    assert any("文件" in e for e in errors)


def test_parse_page_range_ok():
    assert parse_page_range("1,3", 5) == [1, 3]
    assert parse_page_range("2-3", 5) == [2, 3]


def test_parse_page_range_invalid():
    assert parse_page_range("9", 3) is None
    assert parse_page_range("abc", 3) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_session_state.py tests/test_validation.py -v`
Expected: FAIL (modules missing)

- [ ] **Step 3: Write implementation**

```python
# ocrx/gui/session_state.py
# -- coding: utf-8 --
"""Wizard session state shared across views."""

from dataclasses import dataclass, field


@dataclass
class SessionState:
    file_paths: list[str] = field(default_factory=list)
    page_range: str = ""
    selected_example_ids: list[str] = field(default_factory=list)
    prompt_text: str = ""
    output_dir: str = ""
    last_result: str = ""
```

```python
# ocrx/gui/validation.py
# -- coding: utf-8 --
"""Preflight validation helpers for wizard run step."""

from pathlib import Path

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def parse_page_range(page_range: str, total_pages: int) -> list[int] | None:
    text = (page_range or "").strip()
    if not text:
        return list(range(1, total_pages + 1))
    pages: set[int] = set()
    try:
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                start, end = int(start_s), int(end_s)
                if start > end:
                    return None
                pages.update(range(start, end + 1))
            else:
                pages.add(int(part))
    except ValueError:
        return None
    ordered = sorted(pages)
    if not ordered or ordered[0] < 1 or ordered[-1] > total_pages:
        return None
    return ordered


def validate_preflight(config: dict, file_paths: list[str], page_range: str) -> list[str]:
    errors: list[str] = []
    if not (config.get("API_KEY") or "").strip():
        errors.append("请填写 API Key")
    if not (config.get("BASE_URL") or "").strip():
        errors.append("请填写 Base URL")
    if not (config.get("MODEL_NAME") or "").strip():
        errors.append("请填写 Model Name")
    if not file_paths:
        errors.append("请至少选择一个文件")
    for path in file_paths:
        if Path(path).suffix.lower() not in SUPPORTED_SUFFIXES:
            errors.append(f"不支持的文件类型：{Path(path).name}")
    if (page_range or "").strip():
        # full page-count check happens after opening the PDF in controllers
        for part in page_range.replace("-", ",").split(","):
            if part.strip() and not part.strip().isdigit():
                errors.append("页码范围格式应如 1,3,5-10")
                break
    return errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_session_state.py tests/test_validation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ocrx/gui/session_state.py ocrx/gui/validation.py tests/test_session_state.py tests/test_validation.py
git commit -m "feat(gui): add session state and preflight validation"
```

---

### Task 3: Throttled progress controller

**Covers:** S5, S6

**Files:**
- Create: `ocrx/gui/controllers/__init__.py`
- Create: `ocrx/gui/controllers/progress_controller.py`
- Test: `tests/test_progress_controller.py`

**Interfaces:**
- Produces: `ProgressController(root, on_progress, on_status, min_interval_ms=100)`.
  Methods: `handle_progress(current, total, percent, phase)`, `handle_status(status)`, `flush()`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_progress_controller.py
# -- coding: utf-8 --
import tkinter as tk

from ocrx.gui.controllers.progress_controller import ProgressController


def test_progress_is_coalesced():
    root = tk.Tk()
    root.withdraw()
    seen = []
    ctrl = ProgressController(root, on_progress=lambda *a: seen.append(a), on_status=lambda s: None)
    ctrl.handle_progress(1, 10, 10, "ocr")
    ctrl.handle_progress(2, 10, 20, "ocr")
    ctrl.flush()
    root.update()
    assert seen
    assert seen[-1][2] in (10, 20)
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_progress_controller.py -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Write implementation**

```python
# ocrx/gui/controllers/__init__.py
# -- coding: utf-8 --
"""GUI controllers."""
```

```python
# ocrx/gui/controllers/progress_controller.py
# -- coding: utf-8 --
"""Coalesce progress/status events onto the Tk main thread."""

from typing import Callable


class ProgressController:
    def __init__(
        self,
        root,
        on_progress: Callable[[int, int, float, str], None],
        on_status: Callable[[str], None],
        min_interval_ms: int = 100,
    ):
        self.root = root
        self.on_progress = on_progress
        self.on_status = on_status
        self.min_interval_ms = min_interval_ms
        self._pending_progress = None
        self._pending_status = None
        self._scheduled = False
        self._last_emit = 0.0

    def handle_progress(self, current: int, total: int, percent: float, phase: str) -> None:
        self._pending_progress = (current, total, percent, phase)
        self._schedule()

    def handle_status(self, status: str) -> None:
        self._pending_status = status
        self._schedule()

    def _schedule(self) -> None:
        if self._scheduled:
            return
        self._scheduled = True
        self.root.after(self.min_interval_ms, self._emit)

    def _emit(self) -> None:
        import time

        self._scheduled = False
        now = time.monotonic() * 1000
        if now - self._last_emit < self.min_interval_ms:
            self._schedule()
            return
        self._last_emit = now
        if self._pending_progress is not None:
            self.on_progress(*self._pending_progress)
            self._pending_progress = None
        if self._pending_status is not None:
            self.on_status(self._pending_status)
            self._pending_status = None
        if self._pending_progress is not None or self._pending_status is not None:
            self._schedule()

    def flush(self) -> None:
        self.root.update_idletasks()
        self._emit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_progress_controller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ocrx/gui/controllers tests/test_progress_controller.py
git commit -m "feat(gui): add throttled progress controller"
```

---

### Task 4: Save/Copy/Prompt controllers

**Covers:** S2, S5, S7

**Files:**
- Create: `ocrx/gui/controllers/save_controller.py`
- Create: `ocrx/gui/controllers/copy_controller.py`
- Create: `ocrx/gui/controllers/prompt_controller.py`
- Test: `tests/test_save_controller.py`
- Test: `tests/test_copy_controller.py`
- Test: `tests/test_prompt_controller.py`

**Interfaces:**
- Consumes: `ProcessingService.process_files/process_and_copy/request_cancel`, `SessionState`.
- Produces:
  - `SaveController(service, logger).run(file_paths, prompt, page_range, example_images) -> dict`
  - `CopyController(service, logger).run(file_paths, prompt, page_range, example_images) -> tuple[bool, str]`
  - `PromptController(config).save_new(name, text) -> bool`, `.rename(old, new) -> bool`, `.delete(name) -> bool`, `.reset() -> None`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_save_controller.py
# -- coding: utf-8 --
from ocrx.gui.controllers.save_controller import SaveController


class FakeService:
    def __init__(self):
        self.requested_cancel = False

    def process_files(self, file_paths, prompt, page_range_str, example_images=None):
        return {"a.png": (True, "out/a.md")}

    def request_cancel(self):
        self.requested_cancel = True


def test_save_controller_run():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    results = ctrl.run(["a.png"], "p", "", None)
    assert results["a.png"][0] is True
```

```python
# tests/test_copy_controller.py
# -- coding: utf-8 --
from ocrx.gui.controllers.copy_controller import CopyController


class FakeService:
    def process_and_copy(self, file_paths, prompt, page_range_str, example_images=None):
        return True, "hello"


def test_copy_controller_run():
    ctrl = CopyController(FakeService(), logger=None)
    ok, content = ctrl.run(["a.png"], "p", "", None)
    assert ok is True
    assert content == "hello"
```

```python
# tests/test_prompt_controller.py
# -- coding: utf-8 --
from ocrx.config import ConfigManager
from ocrx.gui.controllers.prompt_controller import PromptController


def test_prompt_controller_crud(tmp_path):
    cfg = ConfigManager(str(tmp_path / "cfg.json"))
    cfg.load()
    ctrl = PromptController(cfg)
    assert ctrl.save_new("自定义", "内容") is True
    assert ctrl.rename("自定义", "新名字") is True
    assert ctrl.delete("新名字") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_save_controller.py tests/test_copy_controller.py tests/test_prompt_controller.py -v`
Expected: FAIL (modules missing)

- [ ] **Step 3: Write implementation**

```python
# ocrx/gui/controllers/save_controller.py
# -- coding: utf-8 --
from typing import Dict, List, Optional, Tuple


class SaveController:
    def __init__(self, service, logger=None):
        self.service = service
        self.logger = logger

    def run(
        self,
        file_paths: List[str],
        prompt: str,
        page_range: str,
        example_images: Optional[List[Tuple[str, bytes]]] = None,
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        return self.service.process_files(
            file_paths=file_paths,
            prompt=prompt,
            page_range_str=page_range,
            example_images=example_images,
        )

    def cancel(self) -> None:
        self.service.request_cancel()
```

```python
# ocrx/gui/controllers/copy_controller.py
# -- coding: utf-8 --
from typing import List, Optional, Tuple


class CopyController:
    def __init__(self, service, logger=None):
        self.service = service
        self.logger = logger

    def run(
        self,
        file_paths: List[str],
        prompt: str,
        page_range: str,
        example_images: Optional[List[Tuple[str, bytes]]] = None,
    ) -> Tuple[bool, str]:
        return self.service.process_and_copy(
            file_paths=file_paths,
            prompt=prompt,
            page_range_str=page_range,
            example_images=example_images,
        )

    def cancel(self) -> None:
        self.service.request_cancel()
```

```python
# ocrx/gui/controllers/prompt_controller.py
# -- coding: utf-8 --
from ocrx.prompt_templates import DEFAULT_PROMPT_TEMPLATES


class PromptController:
    def __init__(self, config):
        self.config = config

    def save_new(self, name: str, text: str) -> bool:
        if not name or name in DEFAULT_PROMPT_TEMPLATES:
            return False
        return self.config.add_prompt_template(name, text)

    def rename(self, old: str, new: str) -> bool:
        if old in DEFAULT_PROMPT_TEMPLATES or not new:
            return False
        templates = self.config.get_prompt_templates()
        if old not in templates:
            return False
        templates[new] = templates.pop(old)
        self.config.config["prompt_templates"] = templates
        return self.config.save()

    def delete(self, name: str) -> bool:
        if name in DEFAULT_PROMPT_TEMPLATES:
            return False
        templates = self.config.get_prompt_templates()
        if name not in templates:
            return False
        templates.pop(name, None)
        self.config.config["prompt_templates"] = templates
        return self.config.save()

    def reset(self) -> None:
        self.config.reset_to_defaults()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_save_controller.py tests/test_copy_controller.py tests/test_prompt_controller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ocrx/gui/controllers tests/test_save_controller.py tests/test_copy_controller.py tests/test_prompt_controller.py
git commit -m "feat(gui): add save/copy/prompt controllers"
```

---

### Task 5: AppContext

**Covers:** S2, S4.1, S5

**Files:**
- Create: `ocrx/gui/app_context.py`
- Test: `tests/test_app_context.py`

**Interfaces:**
- Produces: `AppContext(config_path=None, example_path=None, log_path=None)`.
  Attributes: `config`, `service`, `examples`, `clipboard`, `logger`, `state`.
  Methods: `rebuild_service() -> None`, `load_example_images(ids) -> list[tuple[str, bytes]]`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_app_context.py
# -- coding: utf-8 --
from ocrx.gui.app_context import AppContext


def test_app_context_uses_injected_paths(tmp_path):
    ctx = AppContext(
        config_path=str(tmp_path / "cfg.json"),
        example_path=str(tmp_path / "examples"),
        log_path=str(tmp_path / "app.log"),
    )
    assert ctx.state.file_paths == []
    assert ctx.config.config["MAX_WORKERS"] == "10"
    ctx.config.set("API_KEY", "k")
    ctx.config.set("BASE_URL", "http://127.0.0.1")
    ctx.config.set("MODEL_NAME", "m")
    ctx.rebuild_service()
    assert ctx.service is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app_context.py -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Write implementation**

```python
# ocrx/gui/app_context.py
# -- coding: utf-8 --
"""Shared application services for GUI layers."""

from pathlib import Path

from ..clipboard import ClipboardHistory
from ..config import ConfigManager
from ..example_library import ExampleLibrary
from ..logger import StructuredLogger
from ..processing_service import ProcessingService
from .session_state import SessionState


class AppContext:
    def __init__(self, config_path=None, example_path=None, log_path=None, root=None):
        self.config = ConfigManager(config_path)
        self.config.load()
        self.examples = ExampleLibrary(example_path)
        self.logger = StructuredLogger(log_file_path=log_path)
        self.clipboard = ClipboardHistory(root=root)
        self.state = SessionState()
        self.service = None
        self.rebuild_service()

    def rebuild_service(self) -> None:
        cfg = self.config.config
        self.service = ProcessingService(
            api_key=cfg.get("API_KEY", ""),
            base_url=cfg.get("BASE_URL", ""),
            model_name=cfg.get("MODEL_NAME", ""),
            output_dir=cfg.get("OUTPUT_DIR", ""),
            max_workers=int(cfg.get("MAX_WORKERS", "10")),
            pdf_scale=float(cfg.get("PDF_SCALE_FACTOR", "3.0")),
            logger_inst=self.logger,
        )

    def load_example_images(self, example_ids: list[str]) -> list[tuple[str, bytes]]:
        loaded = []
        for ex_id in example_ids:
            example = self.examples.get_example(ex_id)
            if not example:
                continue
            path = Path(example.image_path)
            if path.exists():
                loaded.append((example.text, path.read_bytes()))
        return loaded
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_app_context.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ocrx/gui/app_context.py tests/test_app_context.py
git commit -m "feat(gui): add AppContext"
```

---

### Task 6: Wizard shell and primary views

**Covers:** S2, S3, S4.2

**Files:**
- Create: `ocrx/gui/views/__init__.py`
- Create: `ocrx/gui/views/wizard_nav.py`
- Create: `ocrx/gui/views/config_step.py`
- Create: `ocrx/gui/views/files_step.py`
- Create: `ocrx/gui/views/prompt_step.py`
- Create: `ocrx/gui/views/run_step.py`
- Test: `tests/test_wizard_views.py`

**Interfaces:**
- Produces:
  - `WizardNav(parent, steps: list[str], on_change: Callable[[int], None])`
  - Each step view: `build(parent)`, `load_state(state, config)`, `collect(state, config)`.
  - `RunStep` exposes `set_running(bool)`, `set_progress(...)`, `set_result(text)`, callbacks `on_save`, `on_copy`, `on_stop`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_wizard_views.py
# -- coding: utf-8 --
import tkinter as tk

from ocrx.gui.session_state import SessionState
from ocrx.gui.views.files_step import FilesStep
from ocrx.gui.views.wizard_nav import WizardNav


def test_wizard_nav_selects_steps():
    root = tk.Tk(); root.withdraw()
    seen = []
    nav = WizardNav(root, ["配置", "文件", "提示词", "执行"], on_change=seen.append)
    nav.set_current(1)
    assert seen[-1] == 1
    root.destroy()


def test_files_step_collect(monkeypatch):
    root = tk.Tk(); root.withdraw()
    state = SessionState()
    step = FilesStep()
    step.build(root)
    monkeypatch.setattr(step, "pick_files", lambda: ["a.png"])
    step.add_files()
    step.collect(state)
    assert state.file_paths == ["a.png"]
    root.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_wizard_views.py -v`
Expected: FAIL (modules missing)

- [ ] **Step 3: Write implementation**

Create compact CustomTkinter view classes. Each view must keep widget handles on `self` and implement `build`/`load_state`/`collect` exactly as named above.

```python
# ocrx/gui/views/wizard_nav.py
# -- coding: utf-8 --
import customtkinter as ctk


class WizardNav:
    def __init__(self, parent, steps, on_change):
        self.steps = steps
        self.on_change = on_change
        self.frame = ctk.CTkFrame(parent)
        self.buttons = []
        for index, title in enumerate(steps):
            btn = ctk.CTkButton(self.frame, text=f"{index + 1}. {title}", width=120)
            btn.configure(command=lambda i=index: self.set_current(i))
            btn.pack(side="left", padx=4, pady=4)
            self.buttons.append(btn)
        self.current = 0

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def set_current(self, index: int) -> None:
        self.current = index
        for i, btn in enumerate(self.buttons):
            btn.configure(fg_color="#2563EB" if i == index else "#E2E8F0")
        self.on_change(index)
```

```python
# ocrx/gui/views/files_step.py
# -- coding: utf-8 --
from tkinter import filedialog

import customtkinter as ctk


class FilesStep:
    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.listbox = ctk.CTkTextbox(self.frame, height=180)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.page_range = ctk.CTkEntry(self.frame, placeholder_text="页码范围，如 1,3,5-10")
        self.page_range.pack(fill="x", padx=8, pady=4)
        btns = ctk.CTkFrame(self.frame)
        btns.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(btns, text="添加文件", command=self.add_files).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="清空", command=self.clear_files).pack(side="left", padx=4)
        self._paths = []
        return self.frame

    def pick_files(self):
        return filedialog.askopenfilenames(
            filetypes=[
                ("支持的文件", "*.pdf *.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("所有文件", "*.*"),
            ]
        )

    def add_files(self):
        for path in self.pick_files() or []:
            if path not in self._paths:
                self._paths.append(path)
        self.listbox.delete("1.0", "end")
        self.listbox.insert("1.0", "\n".join(self._paths))

    def clear_files(self):
        self._paths.clear()
        self.listbox.delete("1.0", "end")

    def load_state(self, state, config):
        self._paths = list(state.file_paths)
        self.page_range.delete(0, "end")
        self.page_range.insert(0, state.page_range)
        self.listbox.delete("1.0", "end")
        self.listbox.insert("1.0", "\n".join(self._paths))

    def collect(self, state, config=None):
        state.file_paths = list(self._paths)
        state.page_range = self.page_range.get().strip()
```

`ConfigStep` exposes `self.fields` as `dict[str, ctk.CTkEntry]` for keys
`BASE_URL`, `API_KEY`, `MODEL_NAME`, `OUTPUT_DIR`, `MAX_WORKERS`,
`PDF_SCALE_FACTOR`; `collect` writes those keys into `config.config`.
`PromptStep` uses `ctk.CTkComboBox` + `ctk.CTkTextbox` and calls
`PromptController.save_new/rename/delete/reset` from buttons.
`RunStep` layout:

```python
class RunStep:
    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.actions = ctk.CTkFrame(self.frame)
        self.save_btn = ctk.CTkButton(self.actions, text="识别并保存")
        self.copy_btn = ctk.CTkButton(self.actions, text="识别并复制")
        self.stop_btn = ctk.CTkButton(self.actions, text="停止", fg_color="#DC2626")
        self.progress = ctk.CTkProgressBar(self.frame)
        self.status = ctk.CTkLabel(self.frame, text="就绪")
        self.result = ctk.CTkTextbox(self.frame, height=260)
        for w in (self.save_btn, self.copy_btn, self.stop_btn):
            w.pack(side="left", padx=4)
        self.actions.pack(fill="x", padx=8, pady=8)
        self.progress.pack(fill="x", padx=8, pady=4)
        self.status.pack(anchor="w", padx=8)
        self.result.pack(fill="both", expand=True, padx=8, pady=8)
        return self.frame

    def set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.save_btn.configure(state=state)
        self.copy_btn.configure(state=state)
        self.stop_btn.configure(state="normal" if running else "disabled")

    def set_progress(self, current, total, percent, phase):
        value = 0 if total <= 0 else current / total
        self.progress.set(value)
        self.status.configure(text=f"{phase} {current}/{total} ({percent:.0f}%)")

    def set_result(self, text: str):
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text[:5000])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_wizard_views.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ocrx/gui/views tests/test_wizard_views.py
git commit -m "feat(gui): add wizard shell and primary views"
```

---

### Task 7: Secondary views and MainWindow shell

**Covers:** S2, S3, S4.2

**Files:**
- Create: `ocrx/gui/views/examples_view.py`
- Create: `ocrx/gui/views/clipboard_view.py`
- Create: `ocrx/gui/views/logs_view.py`
- Modify: `ocrx/gui/main_window.py`
- Test: `tests/test_main_window_shell.py`

**Interfaces:**
- Consumes: `AppContext`, `WizardNav`, step views, controllers.
- Produces: `MainWindow(root, context: AppContext | None = None)` with `on_closing()`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_main_window_shell.py
# -- coding: utf-8 --
import tkinter as tk

from ocrx.gui.app_context import AppContext
from ocrx.gui.main_window import MainWindow


def test_main_window_builds_wizard(tmp_path):
    root = tk.Tk(); root.withdraw()
    ctx = AppContext(
        config_path=str(tmp_path / "cfg.json"),
        example_path=str(tmp_path / "ex"),
        log_path=str(tmp_path / "log"),
    )
    win = MainWindow(root, context=ctx)
    assert win.wizard is not None
    assert win.current_step == 0
    win.on_closing()
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main_window_shell.py -v`
Expected: FAIL (`MainWindow` does not accept context/wizard)

- [ ] **Step 3: Rewrite MainWindow**

```python
# ocrx/gui/main_window.py (core shell)
# -- coding: utf-8 --
import customtkinter as ctk

from .. import __version__
from .app_context import AppContext
from .theme_tokens import apply_appearance
from .views.wizard_nav import WizardNav
from .views.config_step import ConfigStep
from .views.files_step import FilesStep
from .views.prompt_step import PromptStep
from .views.run_step import RunStep


class MainWindow:
    def __init__(self, root, context: AppContext | None = None):
        self.root = root
        self.context = context or AppContext(root=root)
        apply_appearance()
        self.current_step = 0
        self._build_shell()
        self._build_wizard()

    def _build_shell(self):
        self.root.title(f"OCRX-智能文字识别 v{__version__}")
        self.root.geometry("1100x780")
        self.root.minsize(900, 680)

    def _build_wizard(self):
        self.steps = [ConfigStep(), FilesStep(), PromptStep(), RunStep()]
        self.wizard = WizardNav(
            self.root,
            ["配置", "文件", "提示词", "执行"],
            on_change=self._show_step,
        )
        self.wizard.pack(fill="x", padx=12, pady=8)
        self.container = ctk.CTkFrame(self.root)
        self.container.pack(fill="both", expand=True, padx=12, pady=8)
        for step in self.steps:
            step.build(self.container)
        self._show_step(0)

    def _show_step(self, index: int):
        self.current_step = index
        for i, step in enumerate(self.steps):
            if i == index:
                step.frame.tkraise()
                step.load_state(self.context.state, self.context.config)

    def on_closing(self):
        self.context.config.save()
        self.root.destroy()
```

Wire `RunStep` callbacks to `SaveController`/`CopyController` in worker
threads started with `threading.Thread(..., daemon=True)`. Publish progress
via `ProgressController.handle_progress/handle_status`. On completion call
`self.context.clipboard.copy_to_clipboard(content)` for copy mode and
`run_step.set_result(content)` for both modes.

Keep `on_closing` saving config and destroying widgets. Delete unused notebook
construction once wizard is wired. Obsolete handler tests that construct the
old notebook API should be updated to the new views or removed in this task.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main_window_shell.py tests/test_gui_handlers.py tests/test_gui_more.py -v`
Expected: PASS or migrate/delete obsolete handler tests in the same task if APIs were replaced.

- [ ] **Step 5: Commit**

```bash
git add ocrx/gui/views ocrx/gui/main_window.py tests/test_main_window_shell.py
git commit -m "feat(gui): rewrite MainWindow around wizard shell"
```

---

### Task 8: Full GUI end-to-end tests

**Covers:** S8, S6

**Files:**
- Create: `tests/test_gui_e2e.py`
- Modify: `tests/conftest.py` (optional tiny fixtures only)

**Interfaces:**
- Consumes: mock OpenAI server pattern from `tests/test_e2e.py`, `MainWindow`, temp `AppContext` paths.

- [ ] **Step 1: Write failing e2e tests**

```python
# tests/test_gui_e2e.py
# -- coding: utf-8 --
"""Full wizard GUI e2e with tiny generated fixtures and mock OpenAI."""

import time

import pytest

from ocrx.gui.app_context import AppContext
from ocrx.gui.main_window import MainWindow


pytestmark = pytest.mark.skipif(
    not __import__("os").environ.get("OCRX_ALLOW_GUI", "1") == "1",
    reason="GUI e2e disabled",
)


def _tiny_png(path):
    from PIL import Image

    Image.new("RGB", (32, 24), (200, 30, 30)).save(path, "PNG")
    return path


def _tiny_pdf(path):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Page 1")
    doc.save(path)
    doc.close()
    return path


def test_wizard_save_and_copy(tmp_path, mock_openai_server):
    root = __import__("tkinter").Tk()
    root.withdraw()
    png = _tiny_png(tmp_path / "a.png")
    pdf = _tiny_pdf(tmp_path / "a.pdf")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    ctx = AppContext(
        config_path=str(tmp_path / "cfg.json"),
        example_path=str(tmp_path / "examples"),
        log_path=str(tmp_path / "gui.log"),
        root=root,
    )
    ctx.config.set("BASE_URL", mock_openai_server.base_url)
    ctx.config.set("API_KEY", "test-key")
    ctx.config.set("MODEL_NAME", "test-model")
    ctx.config.set("OUTPUT_DIR", str(out_dir))
    ctx.rebuild_service()
    ctx.state.file_paths = [str(png), str(pdf)]

    win = MainWindow(root, context=ctx)
    # Drive RunStep callbacks directly or via helper method:
    win.run_save_now()
    deadline = time.time() + 20
    while win.context.state.last_result == "" and time.time() < deadline:
        root.update()
        time.sleep(0.02)
    assert win.context.state.last_result
    assert any(out_dir.glob("*.md"))

    win.run_copy_now()
    deadline = time.time() + 20
    while time.time() < deadline:
        root.update()
        time.sleep(0.02)
    assert win.context.clipboard.get_history()
    win.on_closing()
    root.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gui_e2e.py -v`
Expected: FAIL (missing implementation or wiring)

- [ ] **Step 3: Implement wiring gaps exposed by e2e**

Add only the glue required by tests: example image loading, save output verification, clipboard write through `ClipboardHistory`, and cancel/reset.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gui_e2e.py -v`
Expected: PASS on Windows with Tk available; SKIP with clear reason if no display.

Run: `python -m pytest tests/test_gui_e2e.py -v --durations=10`
Expected: suite well under 60s.

- [ ] **Step 5: Commit**

```bash
git add tests/test_gui_e2e.py tests/conftest.py tests/mock_openai.py
git commit -m "test: add full GUI e2e for wizard save/copy flows"
```

---

### Task 9: Packaging and regression sweep

**Covers:** S6, S9

**Files:**
- Modify: `build_package.bat`
- Modify: `AGENTS.md` (commands/architecture notes only if needed)

- [ ] **Step 1: Update PyInstaller flags**

Add `--hidden-import=customtkinter --collect-all=customtkinter` to the existing PyInstaller command in `build_package.bat`.

- [ ] **Step 2: Full test suite**

Run: `python -m pytest`
Expected: all tests pass (GUI e2e may skip only when display unavailable).

Run: `python -m coverage run -m pytest`
Run: `python -m coverage report --include="ocrx/gui/*"`
Expected: gui package coverage reported; no requirement to hit 100%.

- [ ] **Step 3: Commit**

```bash
git add build_package.bat AGENTS.md
git commit -m "build: package customtkinter with PyInstaller"
```

---

## Self-Review

1. **Spec coverage:** S1 goals map to Tasks 6-8; S2 architecture Tasks 2-7; S3 wizard Task 6-7; S4 components Tasks 1-7; S5 flow Tasks 3-4, 7; S6 performance Tasks 3, 6, 8-9; S7 errors Tasks 2, 4, 8; S8 testing Task 8; S9 packaging Tasks 1, 9. S10 out of scope not tasked.
2. **Placeholder scan:** Task 6 intentionally names methods and contracts; implementers must keep those exact names. No "TBD" remains.
3. **Type consistency:** `SessionState`, `AppContext.load_example_images`, controller `run` signatures, and `ProgressController.handle_progress` are consistent across tasks.

## Execution Handoff

Plan is ready for compose:subagent or compose:execute after execution-style preference is confirmed.
