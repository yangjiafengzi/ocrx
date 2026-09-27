# -- coding: utf-8 --
"""主窗口外壳（wizard shell）。

MainWindow 只负责组装外壳、导航与生命周期；识别工作流由
SaveController / CopyController 实现，视图只回传用户意图。
工作线程绝不触碰 Tk：进度经 ProgressController 合并上屏，
任务结果经队列 + after 泵回到主线程。
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from .. import __version__
from .app_context import AppContext
from .controllers.copy_controller import CopyController
from .controllers.progress_controller import ProgressController
from .controllers.prompt_controller import PromptController
from .controllers.save_controller import SaveController, SaveResult
from .theme_tokens import apply_appearance
from .validation import validate_preflight
from .views.config_step import ConfigStep
from .views.files_step import FilesStep
from .views.prompt_step import PromptStep
from .views.run_step import RunStep
from .views.wizard_nav import WizardNav
from .views.clipboard_view import ClipboardView
from .views.examples_view import ExamplesView
from .views.logs_view import LogsView


STEP_TITLES = ["配置", "文件", "提示词", "执行"]
SECONDARY_TABS = ["示例库", "剪贴板", "运行日志"]
_PUMP_MS = 50


class MainWindow:
    """OCRX 主窗口：外壳、导航、生命周期 + 任务编排。"""

    def __init__(self, root, context: AppContext | None = None):
        self.root = root
        self.context = context or AppContext(root=root)
        self.session = self.context.session_state
        apply_appearance()

        self.current_step = 0
        self._running = False
        self._job_thread: Optional[threading.Thread] = None
        self._outcome_queue: queue.Queue = queue.Queue()
        self._log_queue: queue.Queue = queue.Queue()
        self._closed = False
        self._pump_after_id: Optional[str] = None
        self._main_ident = threading.get_ident()

        self._build_shell()
        self._build_wizard()
        self._build_secondary()

        self.progress = ProgressController(
            self.root,
            on_progress=self._on_progress,
            on_status=self._on_status,
        )
        self._wire_service_progress()
        self.context.logger.gui_callback = self._on_log_entry

        self._schedule_pump()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # -- shell / wizard / secondary ------------------------------------

    def _build_shell(self) -> None:
        self.root.title(f"OCRX-智能文字识别 v{__version__}")
        self.root.geometry("1100x820")
        self.root.minsize(900, 680)
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(
            header, text=f"OCRX 智能文字识别  ·  v{__version__}"
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            header, text="保存配置", width=90, command=self.save_config
        ).pack(side="right", padx=4)

    def _build_wizard(self) -> None:
        self.wizard = WizardNav(
            self.root, STEP_TITLES, on_change=self._show_step
        )
        self.wizard.pack(fill="x", padx=12, pady=8)
        self.container = ctk.CTkFrame(self.root)
        self.container.pack(fill="both", expand=True, padx=12, pady=4)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.config_step = ConfigStep()
        self.files_step = FilesStep()
        self.prompt_step = PromptStep(
            prompt_controller=PromptController(self.context.config),
            examples=self.context.examples,
        )
        self.run_step = RunStep()
        self.steps = [self.config_step, self.files_step, self.prompt_step, self.run_step]
        for step in self.steps:
            step.build(self.container).grid(row=0, column=0, sticky="nsew")

        self.run_step.set_on_save(self.run_save_now)
        self.run_step.set_on_copy(self.run_copy_now)
        self.run_step.set_on_stop(self.stop_now)
        self.run_step.set_running(False)  # 空闲：启用保存/复制，禁用停止
        self._show_step(0)

    def _build_secondary(self) -> None:
        self.secondary = ctk.CTkTabview(self.root, height=230)
        self.secondary.pack(fill="x", padx=12, pady=(0, 8))
        for title in SECONDARY_TABS:
            self.secondary.add(title)

        self.examples_view = ExamplesView(self.context.examples)
        self.examples_view.build(self.secondary.tab(SECONDARY_TABS[0]))
        self.examples_view.set_on_selection_change(self._on_example_selection)

        self.clipboard_view = ClipboardView(self.context.clipboard)
        self.clipboard_view.build(self.secondary.tab(SECONDARY_TABS[1]))
        self.clipboard_view.set_on_copy(self._copy_history_entry)
        self.clipboard_view.set_on_clear(self._clear_history)

        self.logs_view = LogsView()
        self.logs_view.build(self.secondary.tab(SECONDARY_TABS[2]))

    def _show_step(self, index: int) -> None:
        self._collect_state()
        self.current_step = index
        for i, step in enumerate(self.steps):
            if i == index:
                step.frame.tkraise()
                step.load_state(self.session, self.context.config)

    def _collect_state(self) -> None:
        for step in self.steps:
            try:
                step.collect(self.session, self.context.config)
            except Exception:
                pass

    # -- progress / status / logs -------------------------------------

    def _wire_service_progress(self) -> None:
        service = self.context.service
        if service is None:
            return
        service.set_progress_callback(self.progress.handle_progress)
        service.set_status_callback(self.progress.handle_status)

    def _on_progress(self, current, total, percent, phase) -> None:
        self.run_step.set_progress(current, total, percent, phase)

    def _on_status(self, status: str) -> None:
        self.run_step.set_status(status)

    def _on_log_entry(self, entry) -> None:
        try:
            self._log_queue.put(entry)
        except Exception:
            pass

    def _drain_logs(self) -> None:
        while True:
            try:
                entry = self._log_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break
            try:
                self.logs_view.append(entry)
            except Exception:
                pass

    # -- job orchestration --------------------------------------------

    def run_save_now(self) -> None:
        """识别并保存（按钮与测试助手共用同一代码路径）。"""
        self._start_job("save")

    def run_copy_now(self) -> None:
        """识别并复制（按钮与测试助手共用同一代码路径）。"""
        self._start_job("copy")

    def _start_job(self, mode: str) -> None:
        if self._running:
            return
        self._collect_state()
        config = dict(self.context.config.config)
        file_paths = list(self.session.file_paths)
        page_range = self.session.page_range
        prompt = self.session.prompt_text

        errors = validate_preflight(config, file_paths, page_range)
        if errors:
            self._show_run_error("\n".join(errors))
            return

        example_images = self.context.load_example_images(
            self.session.selected_example_ids
        )
        self._sync_service_config()

        self._running = True
        self.run_step.set_running(True)
        self.run_step.set_status("任务启动中...")
        self._job_thread = threading.Thread(
            target=self._run_job,
            args=(mode, file_paths, prompt, page_range, example_images),
            daemon=True,
            name=f"ocrx-job-{mode}",
        )
        self._job_thread.start()

    def _sync_service_config(self) -> None:
        service = self.context.service
        if service is None:
            return
        cfg = self.context.config.config
        try:
            max_workers = int(str(cfg.get("MAX_WORKERS", "10")).strip() or "10")
        except (TypeError, ValueError):
            max_workers = 10
        try:
            pdf_scale = float(str(cfg.get("PDF_SCALE_FACTOR", "3.0")).strip() or "3.0")
        except (TypeError, ValueError):
            pdf_scale = 3.0
        service.update_config(
            api_key=str(cfg.get("API_KEY", "")),
            base_url=str(cfg.get("BASE_URL", "")),
            model_name=str(cfg.get("MODEL_NAME", "")),
            output_dir=str(cfg.get("OUTPUT_DIR", "") or (Path.home() / "Documents")),
            max_workers=max_workers,
            pdf_scale=pdf_scale,
        )
        self._wire_service_progress()

    def _run_job(self, mode, file_paths, prompt, page_range, example_images) -> None:
        """工作线程体：绝不触碰 Tk，结果只入队。"""
        outcome = ("error", "未知错误")
        try:
            service = self.context.service
            if service is None:
                outcome = ("error", "处理服务未初始化")
            else:
                service.reset_cancel()
                if mode == "save":
                    result: SaveResult = SaveController(
                        service, logger=self.context.logger
                    ).run(file_paths, prompt, page_range, example_images)
                    if result.ok:
                        outcome = ("save_ok", self._collect_saved_text(result.results))
                    else:
                        outcome = ("error", result.error or "识别并保存失败")
                else:
                    ok, content = CopyController(
                        service, logger=self.context.logger
                    ).run(file_paths, prompt, page_range, example_images)
                    if ok:
                        outcome = ("copy_ok", content or "")
                    else:
                        outcome = ("error", content or "识别并复制失败")
        except Exception as exc:  # never crash the mainloop
            try:
                self.context.logger.error(f"任务执行失败: {exc}", "MainWindow")
            except Exception:
                pass
            outcome = ("error", str(exc))
        try:
            self._outcome_queue.put(outcome)
        except Exception:
            pass

    def _drain_outcome(self) -> None:
        while True:
            try:
                outcome = self._outcome_queue.get_nowait()
            except queue.Empty:
                return
            except Exception:
                return
            self._finish_job(outcome)

    def _finish_job(self, outcome) -> None:
        kind, payload = outcome
        if kind == "save_ok":
            text = payload or "识别并保存完成"
            self.session.last_result = text
            self.run_step.set_result(text)
            self.run_step.set_status("识别并保存完成")
        elif kind == "copy_ok":
            text = payload or ""
            self.session.last_result = text
            self.run_step.set_result(text)
            copied = False
            try:
                copied = bool(self.context.clipboard.copy_to_clipboard(text))
            except Exception:
                copied = False
            self.run_step.set_status(
                "已复制到剪贴板" if copied else "自动复制失败，结果已显示，请手动复制"
            )
            self.clipboard_view.refresh()
        else:
            message = str(payload or "任务失败")
            self.run_step.set_status(message)
            self.run_step.set_result(message)
        self._running = False
        self._job_thread = None
        self.run_step.set_running(False)  # 取消/失败后解锁控件（S7）

    def _show_run_error(self, message: str) -> None:
        self.run_step.set_status(message)
        self.run_step.set_result(message)
        self.run_step.set_running(False)

    def stop_now(self) -> None:
        """请求取消当前任务（协作式取消）。"""
        if not self._running:
            return
        service = self.context.service
        if service is not None:
            try:
                service.request_cancel()
            except Exception:
                pass
        self.run_step.set_status("已请求停止，正在保存/输出已完成的结果...")

    def wait_idle(self, timeout: float = 20.0) -> bool:
        """泵事件直到任务结束；超时返回 False。"""
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                self.root.update()
            except Exception:
                return not self._running
            self._drain_logs()
            self._drain_outcome()
            if not self._running:
                try:
                    self.root.update()
                except Exception:
                    pass
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)

    @staticmethod
    def _collect_saved_text(results: dict) -> str:
        """从保存产物读取文本用于结果预览（save 成功路径）。"""
        parts = []
        for stem, (ok, output_path) in results.items():
            if not ok or not output_path:
                continue
            try:
                content = Path(output_path).read_text(encoding="utf-8")
            except Exception:
                continue
            parts.append(f"=== {stem} ===\n{content}")
        if parts:
            return "\n\n".join(parts)
        ok_count = sum(1 for ok, _ in results.values() if ok)
        return f"处理完成：成功 {ok_count}/{len(results)} 个文件"

    # -- secondary view intents ---------------------------------------

    def _on_example_selection(self, selected_ids) -> None:
        try:
            self.context.logger.debug(
                f"示例库选择变化：{len(selected_ids)} 个", "FewShot"
            )
        except Exception:
            pass

    def _copy_history_entry(self, content) -> None:
        if not content:
            self.run_step.set_status("未选中可复制的记录")
            return
        ok = False
        try:
            ok = bool(self.context.clipboard.copy_to_clipboard(content))
        except Exception:
            ok = False
        self.run_step.set_status("已复制到剪贴板" if ok else "复制到剪贴板失败")

    def _clear_history(self) -> None:
        try:
            self.context.clipboard.clear_history()
        except Exception:
            pass
        self.clipboard_view.refresh()

    # -- lifecycle -----------------------------------------------------

    def save_config(self) -> None:
        """显式保存配置（配置文件只在显式保存/退出时写入）。"""
        self._collect_state()
        try:
            self.context.config.save()
        except Exception:
            pass

    def on_closing(self) -> None:
        """窗口关闭：取消任务、保存配置、停止泵并销毁。"""
        if self._running:
            service = self.context.service
            if service is not None:
                try:
                    service.request_cancel()
                except Exception:
                    pass
            self._running = False
        try:
            self.save_config()
        except Exception:
            pass
        self._closed = True
        if self._pump_after_id is not None:
            try:
                self.root.after_cancel(self._pump_after_id)
            except Exception:
                pass
            self._pump_after_id = None
        try:
            self.progress.close()
        except Exception:
            pass
        try:
            self.context.logger.close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # -- thread-safe after pump ----------------------------------------

    def _schedule_pump(self) -> None:
        if self._closed or self._pump_after_id is not None:
            return
        try:
            self._pump_after_id = self.root.after(_PUMP_MS, self._pump_ui)
        except Exception:
            self._closed = True

    def _pump_ui(self) -> None:
        self._pump_after_id = None
        if self._closed:
            return
        try:
            if not self.root.winfo_exists():
                self._closed = True
                return
            self._drain_logs()
            self._drain_outcome()
            self._schedule_pump()
        except tk.TclError:
            self._closed = True
