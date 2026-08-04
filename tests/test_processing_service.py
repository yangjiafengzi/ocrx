# -- coding: utf-8 --
"""ProcessingService 单元测试（全部组件使用假实现）。"""

from pathlib import Path
import threading
import time

import pytest

import ocrx.processing_service as ps
import ocrx.pdf_processor as pdf_processor_module


class FakePDFProcessor:
    def __init__(self, scale_factor=3.0):
        self.scale_factor = scale_factor

    def pdf_to_images(self, pdf_path, page_range=None):
        return [(1, b"pdf-page-1"), (2, b"pdf-page-2")]


class FakeImageProcessor:
    SUPPORTED = {".png", ".jpg", ".jpeg"}

    def is_supported_image(self, file_path):
        return Path(file_path).suffix.lower() in self.SUPPORTED

    def image_file_to_bytes(self, image_path):
        return b"image-data"


class FakeResultMerger:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir or ".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def merge_contents_to_markdown(self, results):
        return "\n\n".join(content for _, content in results)

    def save_to_file(self, content, file_stem, output_dir=None):
        out_dir = Path(output_dir or self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{file_stem}_ocr.md"
        path.write_text(content, encoding="utf-8")
        return str(path)


class FakeOCREngine:
    def __init__(self, **kwargs):
        self.max_workers = kwargs.get("max_workers", 10)
        self.calls = 0
        self.last_examples = None
        self.last_max_retries = None

    def process_single_image(self, prompt, identifier, img_data, max_retries=5, example_images=None, cancel_check=None):
        self.calls += 1
        self.last_examples = example_images
        self.last_max_retries = max_retries
        return (identifier, f"内容-{identifier[1]}")


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_processor_module, "PDFProcessor", FakePDFProcessor)
    monkeypatch.setattr(ps, "ImageProcessor", FakeImageProcessor)
    monkeypatch.setattr(ps, "ResultMerger", FakeResultMerger)
    monkeypatch.setattr(ps, "OCREngine", FakeOCREngine)
    return ps.ProcessingService(
        api_key="k",
        base_url="http://x",
        model_name="m",
        output_dir=str(tmp_path),
        max_workers=4,
        pdf_scale=1.0,
    )


def test_prepare_images_mixed(tmp_path, service):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")
    txt = tmp_path / "note.txt"
    txt.write_text("x", encoding="utf-8")

    pages, failed = service._prepare_images(
        [str(pdf), str(png), str(txt), str(tmp_path / "missing.png")]
    )
    assert len(pages) == 3
    assert failed.keys() == {"note", "missing"}


def test_recognize_pages(service):
    pages = [("a", 1, b"1"), ("a", 2, b"2"), ("b", 1, b"3")]
    results = service._recognize_pages(pages, "prompt", example_images=[("示例", b"img")])
    assert len(results) == 3
    assert service.ocr_engine.calls == 3
    assert service.ocr_engine.last_examples == [("示例", b"img")]
    assert service.ocr_engine.last_max_retries == 3, "业务重试次数应限制为 3"
    assert {r[1] for r in results} == {"内容-1", "内容-2", "内容-1"}


def test_merge_results_saves_per_file(tmp_path, service):
    results = [
        (("a", 1), "A1"),
        (("a", 2), "A2"),
        (("b", 1), "B1"),
    ]
    content, outputs = service._merge_results(results, save_to_file=True)
    assert set(outputs) == {"a", "b"}
    assert outputs["a"][0] is True
    assert outputs["b"][0] is True
    assert Path(outputs["a"][1]).exists()
    assert Path(outputs["b"][1]).exists()
    assert "A1" in content and "B1" in content


def test_merge_results_without_save(tmp_path, service):
    results = [(("a", 1), "A1")]
    content, outputs = service._merge_results(results, save_to_file=False)
    assert outputs["a"] == (True, None)
    assert content == "A1"


def test_merge_results_split_large_file(tmp_path, service):
    results = [(("big", i), f"P{i}") for i in range(12)]
    content, outputs = service._merge_results(results, save_to_file=True)
    assert outputs["big"][0] is True
    assert Path(outputs["big"][1]).exists()


def test_process_files_end_to_end(tmp_path, service):
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")
    results = service.process_files([str(png)], "提示词")
    assert results["pic"] == (True, str(tmp_path / "pic_ocr.md"))
    assert (tmp_path / "pic_ocr.md").read_text(encoding="utf-8") == "内容-1"


def test_process_files_no_pages_returns_failures(tmp_path, service):
    txt = tmp_path / "note.txt"
    txt.write_text("x", encoding="utf-8")
    results = service.process_files([str(txt)], "p")
    assert results["note"][0] is False
    assert "不支持的文件类型" in results["note"][1]


def test_prepare_images_records_failure_reason(tmp_path, service):
    missing = tmp_path / "missing.png"
    pages, failed = service._prepare_images([str(missing)])
    assert pages == []
    assert failed["missing"] == (False, "文件不存在")


def test_process_file_passes_examples(tmp_path, service):
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")
    ok, out_path, stem = service.process_file(
        str(png), "p", example_images=[("示例", b"img")]
    )
    assert ok is True
    assert service.ocr_engine.last_examples == [("示例", b"img")]


def test_process_file_success(tmp_path, service):
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")
    ok, out_path, stem = service.process_file(str(png), "p")
    assert ok is True
    assert stem == "pic"
    assert Path(out_path).exists()


def test_process_file_missing(tmp_path, service):
    ok, out_path, stem = service.process_file(str(tmp_path / "nope.png"), "p")
    assert ok is False
    assert stem == "nope"


def test_process_and_copy(tmp_path, service):
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")
    ok, content = service.process_and_copy([str(png)], "p")
    assert ok is True
    assert content == "内容-1"
    assert not list(tmp_path.glob("*_ocr.md"))


def test_process_and_copy_no_pages(tmp_path, service):
    ok, msg = service.process_and_copy([str(tmp_path / "x.txt")], "p")
    assert ok is False
    assert "没有可处理的图像" in msg


def test_update_config_recreates_components(tmp_path, service, monkeypatch):
    pdf_instances = []
    merger_instances = []
    engine_instances = []

    monkeypatch.setattr(
        pdf_processor_module,
        "PDFProcessor",
        lambda scale_factor: pdf_instances.append(scale_factor) or FakePDFProcessor(scale_factor),
    )
    monkeypatch.setattr(ps, "ResultMerger", lambda output_dir: merger_instances.append(output_dir) or FakeResultMerger(output_dir))
    monkeypatch.setattr(ps, "OCREngine", lambda **kw: engine_instances.append(kw) or FakeOCREngine(**kw))

    service.update_config(api_key="new", output_dir=str(tmp_path / "out"), max_workers=2)
    assert service.api_key == "new"
    assert service.max_workers == 2
    assert len(pdf_instances) == 1
    assert len(merger_instances) == 1
    assert len(engine_instances) == 1


def test_update_config_clears_values(tmp_path, service):
    """回归测试：清空配置字段（空字符串/0）也应生效。"""
    service.update_config(api_key="", base_url="", model_name="", output_dir="", max_workers=0, pdf_scale=0)
    assert service.api_key == ""
    assert service.base_url == ""
    assert service.model_name == ""
    assert service.output_dir == ""
    assert service.max_workers == 0
    assert service.pdf_scale == 0


def test_cancel_before_start_stops_processing(tmp_path, service):
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")
    service.request_cancel()
    results = service.process_files([str(png)], "p")
    assert results == {}


def test_cancel_during_recognize_stops_submitting(tmp_path, service):
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")

    def fake_engine(prompt, identifier, img_data, max_retries=5, example_images=None, cancel_check=None):
        return (identifier, "部分")

    service.ocr_engine.process_single_image = fake_engine
    output = {}

    def run():
        output.update(service.process_files([str(png)] * 3, "p"))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    # 等第一批任务真正完成后请求取消
    deadline = time.time() + 5
    while service.ocr_engine.calls < 1 and time.time() < deadline:
        time.sleep(0.01)
    time.sleep(0.05)
    service.request_cancel()
    thread.join(timeout=5)

    # 分批提交：取消后不应再提交新一批页面（首批最多 max_workers 个）
    assert service.ocr_engine.calls <= service.max_workers
    # 取消后应保存已完成的部分结果
    results = output
    assert results["pic"][0] is True
    assert Path(results["pic"][1]).exists()
    assert "部分" in Path(results["pic"][1]).read_text(encoding="utf-8")


def test_process_and_copy_cancel(tmp_path, service):
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")
    service.request_cancel()
    ok, msg = service.process_and_copy([str(png)], "p")
    assert ok is False
    assert "取消" in msg


def test_process_and_copy_cancel_during_recognize_returns_partial(tmp_path, service):
    """取消发生在识别过程中时，应返回已完成的部分结果供复制。"""
    png = tmp_path / "pic.png"
    png.write_bytes(b"png")

    def fake_engine(prompt, identifier, img_data, max_retries=5, example_images=None, cancel_check=None):
        return (identifier, "部分内容")

    service.ocr_engine.process_single_image = fake_engine
    output = {}

    def run():
        output["result"] = service.process_and_copy([str(png)] * 3, "p")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    deadline = time.time() + 5
    while service.ocr_engine.calls < 1 and time.time() < deadline:
        time.sleep(0.01)
    time.sleep(0.05)
    service.request_cancel()
    thread.join(timeout=5)

    ok, content = output["result"]
    assert ok is True
    assert "部分内容" in content
