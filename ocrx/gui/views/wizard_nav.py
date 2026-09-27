# -- coding: utf-8 --
"""四步向导导航条。"""

from typing import Callable

import customtkinter as ctk

from ..theme_tokens import COLORS


class WizardNav:
    """顶部步骤导航：点击按钮切换当前步骤。"""

    def __init__(
        self,
        parent,
        steps: list[str],
        on_change: Callable[[int], None],
    ):
        self.steps = list(steps)
        self.on_change = on_change
        self.frame = ctk.CTkFrame(parent)
        self.buttons: list[ctk.CTkButton] = []
        for index, title in enumerate(self.steps):
            btn = ctk.CTkButton(
                self.frame,
                text=f"{index + 1}. {title}",
                width=120,
                command=lambda i=index: self.set_current(i),
            )
            btn.pack(side="left", padx=4, pady=4)
            self.buttons.append(btn)
        self.current = 0

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def set_current(self, index: int) -> None:
        self.current = index
        for i, btn in enumerate(self.buttons):
            btn.configure(
                fg_color=COLORS["primary"] if i == index else COLORS["border"],
                text_color="#FFFFFF" if i == index else COLORS["text"],
            )
        self.on_change(index)
