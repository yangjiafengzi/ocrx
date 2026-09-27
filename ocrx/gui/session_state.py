# -- coding: utf-8 --
"""Wizard session state shared across views."""

from dataclasses import dataclass, field


@dataclass
class SessionState:
    file_paths: list[str] = field(default_factory=list)
    page_range: str = ""
    selected_example_ids: list[str] = field(default_factory=list)
    prompt_text: str = ""
    prompt_preset_name: str = ""
    output_dir: str = ""
    last_result: str = ""
