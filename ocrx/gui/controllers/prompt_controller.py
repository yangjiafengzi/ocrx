# -- coding: utf-8 --
"""Prompt preset CRUD controller over ``ConfigManager.prompt_templates``.

Names in ``DEFAULT_PROMPT_TEMPLATES`` are protected: they cannot be created,
renamed, or deleted through this controller (their *body* may still be edited
via :meth:`update`, which is the intended way to customize a default preset).
Every successful mutation is persisted with ``config.save()``.

Mutations are mutate-then-commit: the template dict is updated in memory and
only kept when ``config.save()`` succeeds. When the save fails, the in-memory
change is rolled back so a rejected write is never visible to later reads.
If an unexpected exception escapes mid-mutation, rollback is best-effort.
"""

from ...prompt_templates import DEFAULT_PROMPT_TEMPLATES


class PromptController:
    def __init__(self, config):
        self.config = config

    def save_new(self, name: str, text: str) -> bool:
        templates = None
        mutated = False
        try:
            if not name or name in DEFAULT_PROMPT_TEMPLATES:
                return False
            templates = self.config.get_prompt_templates()
            if name in templates:
                return False
            self.config.add_prompt_template(name, text)
            mutated = True
            if self.config.save():
                return True
        except Exception:
            pass
        if mutated and templates is not None:
            templates.pop(name, None)
        return False

    def rename(self, old: str, new: str) -> bool:
        templates = None
        mutated = False
        try:
            if not new or new in DEFAULT_PROMPT_TEMPLATES or old in DEFAULT_PROMPT_TEMPLATES:
                return False
            templates = self.config.get_prompt_templates()
            if old not in templates:
                return False
            if new in templates:
                return False
            templates[new] = templates.pop(old)
            mutated = True
            self.config.config["prompt_templates"] = templates
            if self.config.save():
                return True
        except Exception:
            pass
        if mutated and templates is not None:
            templates[old] = templates.pop(new)
        return False

    def delete(self, name: str) -> bool:
        templates = None
        removed = None
        mutated = False
        try:
            if name in DEFAULT_PROMPT_TEMPLATES:
                return False
            templates = self.config.get_prompt_templates()
            if name not in templates:
                return False
            removed = templates.pop(name)
            mutated = True
            self.config.config["prompt_templates"] = templates
            if self.config.save():
                return True
        except Exception:
            pass
        if mutated and templates is not None:
            templates[name] = removed
        return False

    def update(self, name: str, text: str) -> bool:
        """Replace the body of an existing template, including defaults.

        Returns False when ``name`` is unknown or the change could not be
        persisted; the previous body is kept in that case.
        """
        templates = None
        previous = None
        mutated = False
        try:
            templates = self.config.get_prompt_templates()
            if name not in templates:
                return False
            previous = templates[name]
            templates[name] = text
            mutated = True
            self.config.config["prompt_templates"] = templates
            if self.config.save():
                return True
        except Exception:
            pass
        if mutated and templates is not None:
            templates[name] = previous
        return False

    def reset(self) -> None:
        try:
            self.config.reset_to_defaults(["prompt_templates"])
            self.config.save()
        except Exception:
            return None
