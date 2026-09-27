# -- coding: utf-8 --
"""SaveController unit tests (fake service, no GUI)."""

from ocrx.gui.controllers.save_controller import SaveController


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


def test_save_controller_run():
    service = FakeService()
    ctrl = SaveController(service, logger=None)
    results = ctrl.run(["a.png"], "p", "", None)
    assert results["a.png"][0] is True


def test_save_controller_delegates_kwargs():
    service = FakeService(result={"a.png": (False, None), "b.png": (True, "out/b.md")})
    ctrl = SaveController(service, logger=None)
    examples = [("sample text", b"img")]
    results = ctrl.run(["a.png", "b.png"], "prompt text", "1-2", examples)
    assert results == {"a.png": (False, None), "b.png": (True, "out/b.md")}
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
    results = ctrl.run(["a.png"], "p", "", None)
    assert results == {}
    assert any(level == "error" for level, _msg, _comp in logger.messages)
