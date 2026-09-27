# -- coding: utf-8 --
"""CopyController unit tests (fake service, no GUI)."""

from ocrx.gui.controllers.copy_controller import CopyController
from ocrx.gui.validation import COPY_MAX_PAGES, ERR_EMPTY_PROMPT


class FakeService:
    def __init__(self, result=None, error=None):
        self.requested_cancel = False
        self.calls = []
        self.result = (True, "hello") if result is None else result
        self.error = error
        self.pdf_processor = None

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


# -- copy page cap (restored product guard) --


class FakePdfProcessor:
    def __init__(self, counts):
        self.counts = counts

    def get_pdf_page_count(self, path):
        return self.counts[path]


def test_copy_controller_rejects_image_batch_over_max_pages():
    service = FakeService()
    ctrl = CopyController(service, logger=None)
    paths = [f"p{i}.png" for i in range(COPY_MAX_PAGES + 1)]
    ok, content = ctrl.run(paths, "p", "", None)
    assert ok is False
    assert "识别并保存" in content
    assert "页面范围" in content
    assert str(COPY_MAX_PAGES) in content
    assert service.calls == []


def test_copy_controller_rejects_pdf_over_max_pages():
    service = FakeService()
    service.pdf_processor = FakePdfProcessor({"big.pdf": 12})
    ctrl = CopyController(service, logger=None)
    ok, content = ctrl.run(["big.pdf"], "p", "", None)
    assert ok is False
    assert "12" in content
    assert "识别并保存" in content
    assert service.calls == []


def test_copy_controller_allows_exactly_max_pages():
    service = FakeService()
    service.pdf_processor = FakePdfProcessor({"doc.pdf": COPY_MAX_PAGES})
    ctrl = CopyController(service, logger=None)
    ok, content = ctrl.run(["doc.pdf"], "p", "", None)
    assert ok is True
    assert content == "hello"
    assert len(service.calls) == 1


def test_copy_controller_page_range_fits_under_cap():
    # A big PDF is allowed when the page range keeps the run at the cap.
    service = FakeService()
    service.pdf_processor = FakePdfProcessor({"big.pdf": 50})
    ctrl = CopyController(service, logger=None)
    ok, content = ctrl.run(["big.pdf"], "p", "1-10", None)
    assert ok is True
    assert len(service.calls) == 1
    ok, content = ctrl.run(["big.pdf"], "p", "1-11", None)
    assert ok is False
    assert "识别并保存" in content
    assert len(service.calls) == 1


def test_copy_controller_counts_mixed_files_toward_cap():
    service = FakeService()
    service.pdf_processor = FakePdfProcessor({"doc.pdf": 5})
    ctrl = CopyController(service, logger=None)
    paths = ["doc.pdf"] + [f"p{i}.png" for i in range(6)]
    ok, content = ctrl.run(paths, "p", "", None)
    assert ok is False
    assert "11" in content
    assert service.calls == []


def test_copy_controller_cap_applies_without_config():
    # run_copy_now calls run() without config; the cap must still fire.
    service = FakeService()
    service.pdf_processor = FakePdfProcessor({"big.pdf": 20})
    ctrl = CopyController(service, logger=None)
    ok, content = ctrl.run(["big.pdf"], "p", "1-20", None)
    assert ok is False
    assert service.calls == []


# -- empty prompt product guard (restored) --


def test_copy_controller_rejects_empty_prompt():
    service = FakeService()
    ctrl = CopyController(service, logger=None)
    for bad in ("", "   ", "\n\t"):
        ok, content = ctrl.run(["a.png"], bad, "", None)
        assert ok is False
        assert content == ERR_EMPTY_PROMPT == "请填写提示词"
    assert service.calls == []


def test_copy_controller_rejects_empty_prompt_before_page_check():
    service = FakeService()
    service.pdf_processor = FakePdfProcessor({"big.pdf": 99})
    ctrl = CopyController(service, logger=None)
    ok, content = ctrl.run(["big.pdf"], "", "", None)
    assert ok is False
    assert content == ERR_EMPTY_PROMPT
    assert service.calls == []
