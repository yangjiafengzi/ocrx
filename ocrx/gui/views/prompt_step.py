# -- coding: utf-8 --
"""向导第 3 步：提示词预设编辑与少样本示例选择。"""

from tkinter import simpledialog

import customtkinter as ctk


def _normalize_examples(examples) -> list[tuple[str, str]]:
    """把 examples 源规范成 ``(id, 描述)`` 列表。

    支持 :class:`ExampleLibrary`（``get_all_examples``）、
    id 字符串列表、dict 列表以及带 ``id``/``description`` 属性的对象。
    """
    if examples is None:
        return []
    if hasattr(examples, "get_all_examples"):
        items = list(examples.get_all_examples())
    else:
        try:
            items = list(examples)
        except TypeError:
            items = [examples]
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, str):
            ex_id, desc = item, item
        elif isinstance(item, dict):
            ex_id = str(item.get("id", "") or "")
            desc = str(item.get("description", "") or "") or ex_id
        else:
            ex_id = str(getattr(item, "id", "") or "")
            desc = str(getattr(item, "description", "") or "") or ex_id
        if not ex_id or ex_id in seen:
            continue
        seen.add(ex_id)
        result.append((ex_id, desc))
    return result


class PromptStep:
    """提示词预设下拉 + 正文编辑框 + 少样本示例选择。

    预设的增删改走 :class:`PromptController`（构造时可选传入），
    视图自身不读写配置文件。
    ``examples`` 可传 :class:`ExampleLibrary` 或示例列表（或不传）；
    无论是否提供示例库，都维护 ``selected_example_ids``。
    """

    def __init__(self, prompt_controller=None, examples=None):
        self.prompt_controller = prompt_controller
        self.examples = examples
        self.frame = None
        self.preset = None
        self.textbox = None
        self.status = None
        self.shots_label = None
        self.examples_frame = None
        self.example_items: list[tuple[str, str]] = []
        self.example_checks: dict[str, ctk.CTkCheckBox] = {}
        self._extra_selected: list[str] = []
        self._config = None

    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        top = ctk.CTkFrame(self.frame)
        top.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(top, text="预设").pack(side="left", padx=4)
        self.preset = ctk.CTkComboBox(
            top,
            values=[""],
            width=180,
            state="readonly",
            command=self._on_preset_selected,
        )
        self.preset.pack(side="left", padx=4)
        ctk.CTkButton(top, text="保存", width=64, command=self._on_save).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="另存为", width=64, command=self._on_save_new).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="重命名", width=64, command=self._on_rename).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="删除", width=64, command=self._on_delete).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="重置", width=64, command=self.reset).pack(
            side="left", padx=4
        )
        self.textbox = ctk.CTkTextbox(self.frame, height=170)
        self.textbox.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        shots = ctk.CTkFrame(self.frame)
        shots.pack(fill="x", padx=8, pady=2)
        self.shots_label = ctk.CTkLabel(shots, text="少样本示例")
        self.shots_label.pack(anchor="w", padx=4)
        self.examples_frame = ctk.CTkScrollableFrame(shots, height=110)
        self.examples_frame.pack(fill="x", padx=4, pady=(0, 4))
        self.example_items = _normalize_examples(self.examples)
        self._rebuild_example_checks()
        self.status = ctk.CTkLabel(self.frame, text="")
        self.status.pack(anchor="w", padx=8, pady=(0, 6))
        return self.frame

    # ---- 少样本示例选择 ----

    def set_examples(self, examples) -> None:
        """替换示例源（列表或 :class:`ExampleLibrary`）并重建勾选列表。"""
        keep = self.get_selected_example_ids()
        self.examples = examples
        self.example_items = _normalize_examples(examples)
        self._rebuild_example_checks()
        self.set_selected_example_ids(keep)

    def refresh_examples(self) -> None:
        """按当前示例源重新读取列表（示例库变更后调用）。"""
        self.set_examples(self.examples)

    def get_selected_example_ids(self) -> list[str]:
        """返回当前勾选的示例 id（按列表顺序）。"""
        selected = [
            ex_id
            for ex_id, _ in self.example_items
            if self.example_checks.get(ex_id) is not None
            and self.example_checks[ex_id].get()
        ]
        known = set(self.example_checks)
        selected.extend(x for x in self._extra_selected if x not in known)
        return selected

    def set_selected_example_ids(self, ids) -> None:
        """按 id 列表恢复勾选；不在列表中的 id 也会被保留。"""
        wanted: list[str] = []
        for raw in ids or []:
            ex_id = str(raw)
            if ex_id and ex_id not in wanted:
                wanted.append(ex_id)
        wanted_set = set(wanted)
        self._extra_selected = []
        for ex_id, _ in self.example_items:
            chk = self.example_checks.get(ex_id)
            if chk is None:
                continue
            if ex_id in wanted_set:
                chk.select()
            else:
                chk.deselect()
        for ex_id in wanted:
            if ex_id not in self.example_checks:
                self._extra_selected.append(ex_id)

    def _rebuild_example_checks(self) -> None:
        if self.examples_frame is None:
            return
        for child in self.examples_frame.winfo_children():
            child.destroy()
        self.example_checks = {}
        for ex_id, desc in self.example_items:
            text = ex_id if not desc or desc == ex_id else f"{ex_id}  {desc}"
            chk = ctk.CTkCheckBox(self.examples_frame, text=text)
            chk.pack(anchor="w", padx=4, pady=2)
            self.example_checks[ex_id] = chk

    # ---- PromptController 委托（可选）----

    def save(self, name: str, text: str) -> bool:
        """保存到已存在的预设；名称不存在时转新建。"""
        if self.prompt_controller is None:
            return False
        if self.update(name, text):
            return True
        return self.save_new(name, text)

    def save_new(self, name: str, text: str) -> bool:
        if self.prompt_controller is None:
            return False
        ok = bool(self.prompt_controller.save_new(name, text))
        if ok:
            self._refresh_from_config(select_name=name)
        return ok

    def update(self, name: str, text: str) -> bool:
        if self.prompt_controller is None:
            return False
        return bool(self.prompt_controller.update(name, text))

    def rename(self, old: str, new: str) -> bool:
        if self.prompt_controller is None:
            return False
        ok = bool(self.prompt_controller.rename(old, new))
        if ok:
            self._refresh_from_config(select_name=new, keep_text=True)
        return ok

    def delete(self, name: str) -> bool:
        if self.prompt_controller is None:
            return False
        ok = bool(self.prompt_controller.delete(name))
        if ok:
            self._refresh_from_config()
        return ok

    def reset(self) -> None:
        if self.prompt_controller is None:
            return
        self.prompt_controller.reset()
        self._refresh_from_config()

    # ---- 控件事件 ----

    def _current_text(self) -> str:
        return self.textbox.get("1.0", "end-1c")

    def _on_preset_selected(self, name: str) -> None:
        """下拉里选中预设时，把该预设正文载入编辑框。"""
        self._load_preset_body(name)

    def _load_preset_body(self, name: str) -> None:
        config = self._resolve_config()
        if config is None or self.textbox is None:
            return
        templates = config.get_prompt_templates()
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", templates.get(name, ""))

    def _on_save(self):
        name = self.preset.get().strip()
        ok = self.save(name, self._current_text())
        self.status.configure(text="已保存" if ok else "保存失败")

    def _on_save_new(self):
        name = simpledialog.askstring("另存为", "请输入新的提示词预设名称:")
        if not name:
            return
        ok = self.save_new(name.strip(), self._current_text())
        self.status.configure(text="已保存" if ok else "保存失败")

    def _on_rename(self):
        old = self.preset.get().strip()
        if not old:
            self.status.configure(text="重命名失败")
            return
        new = simpledialog.askstring("重命名", "请输入新的提示词预设名称:", initialvalue=old)
        if new is None:
            return
        new = new.strip()
        if not new or new == old:
            return
        ok = self.rename(old, new)
        self.status.configure(text="已重命名" if ok else "重命名失败")

    def _on_delete(self):
        name = self.preset.get().strip()
        ok = self.delete(name)
        self.status.configure(text="已删除" if ok else "删除失败")

    # ---- 状态同步 ----

    def _resolve_config(self):
        if self._config is not None:
            return self._config
        if self.prompt_controller is not None:
            return getattr(self.prompt_controller, "config", None)
        return None

    def _refresh_from_config(
        self, select_name: str | None = None, keep_text: bool = False
    ) -> None:
        """让下拉与正文与配置里的模板保持一致。"""
        config = self._resolve_config()
        if config is None or self.preset is None or self.textbox is None:
            return
        current_text = self._current_text() if keep_text else ""
        templates = config.get_prompt_templates()
        names = list(templates.keys())
        self.preset.configure(values=names or [""])
        if select_name and select_name in names:
            self.preset.set(select_name)
        else:
            current = self.preset.get()
            if current not in names:
                self.preset.set(names[0] if names else "")
        self.textbox.delete("1.0", "end")
        if keep_text:
            self.textbox.insert("1.0", current_text)
        else:
            self.textbox.insert("1.0", templates.get(self.preset.get(), ""))

    def load_state(self, state, config) -> None:
        if config is not None:
            self._config = config
        names: list[str] = []
        templates = {}
        resolved = self._resolve_config()
        if resolved is not None:
            templates = resolved.get_prompt_templates()
            names = list(templates.keys())
        saved_name = ""
        saved_text = ""
        if state is not None:
            saved_name = getattr(state, "prompt_preset_name", "") or ""
            saved_text = getattr(state, "prompt_text", "") or ""
        selected = ""
        if self.preset is not None:
            self.preset.configure(values=names or [""])
            if saved_name and saved_name in names:
                selected = saved_name
            else:
                current = self.preset.get()
                if current in names:
                    selected = current
                elif names:
                    selected = names[0]
            self.preset.set(selected)
        if selected and saved_text and (not saved_name or saved_name == selected):
            text = saved_text
        elif selected:
            text = templates.get(selected, "")
        else:
            text = saved_text
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        if state is not None:
            self.set_selected_example_ids(
                getattr(state, "selected_example_ids", []) or []
            )

    def collect(self, state, config=None) -> None:
        if state is not None:
            state.prompt_text = self._current_text()
            if self.preset is not None:
                state.prompt_preset_name = self.preset.get()
            state.selected_example_ids = self.get_selected_example_ids()
