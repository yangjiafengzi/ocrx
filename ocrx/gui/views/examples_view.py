# -- coding: utf-8 --
"""示例库管理次级视图。

包装现有 :class:`ExampleManagerUI`，只负责渲染与回传用户意图，
识别流程本身不在此视图内执行。
"""

from typing import Callable, List, Optional

from ..example_manager_ui import ExampleManagerUI


class ExamplesView:
    """少样本示例库管理（增删改、预览），作为向导外的次级表面。"""

    def __init__(self, examples=None):
        self.examples = examples
        self.frame = None
        self.manager: Optional[ExampleManagerUI] = None
        self._on_selection_change: Optional[Callable[[List[str]], None]] = None

    def build(self, parent):
        self.frame = parent
        self.manager = ExampleManagerUI(parent, self.examples)
        self.manager.set_selection_change_callback(self._emit_selection)
        return self.frame

    def refresh(self) -> None:
        """示例库变更后刷新列表。"""
        if self.manager is not None:
            self.manager.refresh_list()

    def get_selected_ids(self) -> List[str]:
        if self.manager is None:
            return []
        return list(self.manager.get_selected_examples())

    # ---- 回调（可选 setter）----

    @property
    def on_selection_change(self):
        return self._on_selection_change

    @on_selection_change.setter
    def on_selection_change(self, callback):
        self._on_selection_change = callback

    def set_on_selection_change(self, callback) -> None:
        self.on_selection_change = callback

    def _emit_selection(self, selected_ids: List[str]) -> None:
        if self._on_selection_change is not None:
            self._on_selection_change(list(selected_ids))
