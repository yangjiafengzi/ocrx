# -- coding: utf-8 --
"""Prompt preset CRUD controller over ``ConfigManager.prompt_templates``.

Names in ``DEFAULT_PROMPT_TEMPLATES`` are protected: they cannot be created,
renamed, or deleted through this controller. Every successful mutation is
persisted with ``config.save()``.
"""

from ...prompt_templates import DEFAULT_PROMPT_TEMPLATES


class PromptController:
    def __init__(self, config):
        self.config = config

    def save_new(self, name: str, text: str) -> bool:
        try:
            if not name or name in DEFAULT_PROMPT_TEMPLATES:
                return False
            if name in self.config.get_prompt_templates():
                return False
            self.config.add_prompt_template(name, text)
            return bool(self.config.save())
        except Exception:
            return False

    def rename(self, old: str, new: str) -> bool:
        try:
            if not new or new in DEFAULT_PROMPT_TEMPLATES or old in DEFAULT_PROMPT_TEMPLATES:
                return False
            templates = self.config.get_prompt_templates()
            if old not in templates:
                return False
            if new in templates:
                return False
            templates[new] = templates.pop(old)
            self.config.config["prompt_templates"] = templates
            return bool(self.config.save())
        except Exception:
            return False

    def delete(self, name: str) -> bool:
        try:
            if name in DEFAULT_PROMPT_TEMPLATES:
                return False
            templates = self.config.get_prompt_templates()
            if name not in templates:
                return False
            templates.pop(name, None)
            self.config.config["prompt_templates"] = templates
            return bool(self.config.save())
        except Exception:
            return False

    def reset(self) -> None:
        try:
            self.config.reset_to_defaults(["prompt_templates"])
            self.config.save()
        except Exception:
            return None
