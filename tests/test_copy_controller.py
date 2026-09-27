# -- coding: utf-8 --
"""CopyController unit tests (fake service, no GUI)."""

from ocrx.gui.controllers.copy_controller import CopyController


class FakeService:
    def __init__(self, result=None, error=None):
        self.requested_cancel = False
        self.calls = []
        self.result = (True, "hello") if result is None else result
        self.error = error

    def process_and_copy(self, file_paths, prompt, page_range_str, example_images=None):
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


def test_copy_controller_run():
    ctrl = CopyController(FakeService(), logger=None)
    ok, content = ctrl.run(["a.png"], "p", "", None)
    assert ok is True
    assert content == "hello"


def test_copy_controller_delegates_kwargs():
    service = FakeService(result=(False, "no images"))
    ctrl = CopyController(service, logger=None)
    examples = [("sample text", b"img")]
    ok, content = ctrl.run(["a.png"], "prompt text", "1-2", examples)
    assert ok is False
    assert content == "no images"
    assert service.calls == [
        {
            "file_paths": ["a.png"],
            "prompt": "prompt text",
            "page_range_str": "1-2",
            "example_images": examples,
        }
    ]


def test_copy_controller_example_images_default_is_none():
    service = FakeService()
    ctrl = CopyController(service, logger=None)
    ctrl.run(["a.png"], "p", "")
    assert service.calls[0]["example_images"] is None


def test_copy_controller_cancel_requests_cancel():
    service = FakeService()
    ctrl = CopyController(service, logger=None)
    ctrl.cancel()
    assert service.requested_cancel is True


def test_copy_controller_run_surfaces_service_errors():
    service = FakeService(error=RuntimeError("worker failed"))
    logger = FakeLogger()
    ctrl = CopyController(service, logger=logger)
    ok, content = ctrl.run(["a.png"], "p", "", None)
    assert ok is False
    assert "worker failed" in content
    assert any(level == "error" for level, _msg, _comp in logger.messages)


VALID_CONFIG = {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"}


def test_copy_controller_rejects_empty_file_paths():
    service = FakeService()
    ctrl = CopyController(service, logger=None)
    ok, content = ctrl.run([], "p", "", None)
    assert ok is False
    assert content
    ok, content = ctrl.run([], "p", "", None, config=VALID_CONFIG)
    assert ok is False
    assert content
    assert service.calls == []


def test_copy_controller_skips_service_when_required_config_missing():
    service = FakeService()
    ctrl = CopyController(service, logger=None)
    for bad in (
        {"API_KEY": "", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        {"API_KEY": "k", "BASE_URL": "", "MODEL_NAME": "m"},
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": ""},
    ):
        ok, content = ctrl.run(["a.png"], "p", "", None, config=bad)
        assert ok is False
        assert content
    assert service.calls == []


def test_copy_controller_runs_service_when_config_valid():
    service = FakeService()
    ctrl = CopyController(service, logger=None)
    ok, content = ctrl.run(["a.png"], "p", "", None, config=VALID_CONFIG)
    assert ok is True
    assert content == "hello"
    assert len(service.calls) == 1
