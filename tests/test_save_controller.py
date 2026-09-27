# -- coding: utf-8 --
"""SaveController unit tests (fake service, no GUI)."""

from ocrx.gui.controllers.copy_controller import CopyController
from ocrx.gui.controllers.save_controller import SaveController, SaveResult
from ocrx.gui.validation import ERR_EMPTY_PROMPT, ERR_NO_FILES, validate_preflight


class FakeService:
    def __init__(self, result=None, error=None):
        self.requested_cancel = False
        self.calls = []
        self.result = {"a.png": (True, "out/a.md")} if result is None else result
        self.error = error

    def process_files(self, file_paths, prompt, page_range_str, example_images=None):
        self.calls.append(
            {
                "file_paths": file_paths,
                "prompt": prompt,
                "page_range_str": page_range_str,
                "example_images": example_images,
            }
        )
        if self.error is not None:
            raise self.error
        return self.result

    def request_cancel(self):
        self.requested_cancel = True


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message, component="General"):
        self.messages.append(("info", message, component))

    def warning(self, message, component="General"):
        self.messages.append(("warning", message, component))

    def error(self, message, component="General"):
        self.messages.append(("error", message, component))


def test_save_controller_run_returns_save_result():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    result = ctrl.run(["a.png"], "p", "", None)
    assert isinstance(result, SaveResult)
    assert result.ok is True
    assert result.error == ""
    assert result.results["a.png"][0] is True


def test_save_controller_delegates_kwargs():
    service = FakeService(result={"a.png": (False, None), "b.png": (True, "out/b.md")})
    ctrl = SaveController(service, logger=None)
    examples = [("sample text", b"img")]
    result = ctrl.run(["a.png", "b.png"], "prompt text", "1-2", examples)
    assert result.ok is True
    assert result.error == ""
    assert result.results == {"a.png": (False, None), "b.png": (True, "out/b.md")}
    assert service.calls == [
        {
            "file_paths": ["a.png", "b.png"],
            "prompt": "prompt text",
            "page_range_str": "1-2",
            "example_images": examples,
        }
    ]


def test_save_controller_example_images_default_is_none():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    ctrl.run(["a.png"], "p", "3")
    assert service.calls[0]["example_images"] is None


def test_save_controller_cancel_requests_cancel():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    ctrl.cancel()
    assert service.requested_cancel is True


def test_save_controller_run_surfaces_service_errors():
    service = FakeService(error=RuntimeError("worker failed"))
    logger = FakeLogger()
    ctrl = SaveController(service, logger=logger)
    result = ctrl.run(["a.png"], "p", "", None)
    assert result.ok is False
    assert result.results == {}
    assert "worker failed" in result.error
    assert any(level == "error" for level, _msg, _comp in logger.messages)


VALID_CONFIG = {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"}


def test_save_controller_rejects_empty_file_paths():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    for config in (None, VALID_CONFIG):
        result = ctrl.run([], "p", "", None, config=config)
        assert result.ok is False
        assert result.results == {}
        assert result.error == ERR_NO_FILES
    assert service.calls == []


def test_save_controller_skips_service_when_required_config_missing():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    for bad in (
        {"API_KEY": "", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        {"API_KEY": "k", "BASE_URL": "", "MODEL_NAME": "m"},
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": ""},
    ):
        result = ctrl.run(["a.png"], "p", "", None, config=bad)
        assert result.ok is False
        assert result.results == {}
        assert result.error == "\n".join(validate_preflight(bad, ["a.png"], ""))
    assert service.calls == []


def test_save_controller_runs_service_when_config_valid():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    result = ctrl.run(["a.png"], "p", "", None, config=VALID_CONFIG)
    assert result.ok is True
    assert result.results["a.png"][0] is True
    assert result.error == ""
    assert len(service.calls) == 1


def test_save_controller_error_text_matches_copy_controller():
    """Empty-file and preflight failures must match CopyController wording."""
    save = SaveController(FakeService(), logger=None)
    copy = CopyController(FakeService(), logger=None)

    empty = save.run([], "p", "", None)
    _, copy_error = copy.run([], "p", "", None)
    assert empty.error == copy_error

    bad_config = {"API_KEY": "", "BASE_URL": "https://x", "MODEL_NAME": "m"}
    preflight = save.run(["a.png"], "p", "", None, config=bad_config)
    _, copy_error = copy.run(["a.png"], "p", "", None, config=bad_config)
    assert preflight.error == copy_error
    assert preflight.error


def test_save_controller_rejects_empty_prompt():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    for bad in ("", "   ", "\n\t"):
        result = ctrl.run(["a.png"], bad, "", None)
        assert result.ok is False
        assert result.results == {}
        assert result.error == ERR_EMPTY_PROMPT == "请填写提示词"
    assert service.calls == []


def test_save_controller_empty_prompt_matches_copy_controller():
    save = SaveController(FakeService(), logger=None)
    copy = CopyController(FakeService(), logger=None)
    save_result = save.run(["a.png"], "", "", None)
    _, copy_error = copy.run(["a.png"], "", "", None)
    assert save_result.error == copy_error == ERR_EMPTY_PROMPT
