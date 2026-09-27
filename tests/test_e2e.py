# -- coding: utf-8 --
"""
端到端测试：真实 PDF/图片 → 真实处理链 → 本地 OpenAI 兼容 Mock API。

覆盖：保存/复制模式、多页 PDF、页码范围、少样本、网络重试、业务重试、
API 全失败、取消，以及 GUI 控制器接入真实处理服务。
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import fitz
import pytest
from PIL import Image

import ocrx.ocr_client as oc
import ocrx.retry_utils as ru
from ocrx.gui.controllers.copy_controller import CopyController
from ocrx.gui.controllers.save_controller import SaveController
from ocrx.logger import StructuredLogger
from ocrx.processing_service import ProcessingService


class MockOpenAIServer:
    """本地 OpenAI 兼容 Mock 服务。"""

    def __init__(self, respond=None):
        self.requests = []
        self.lock = threading.Lock()
        self.respond = respond or self.default_respond
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def _make_handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                with outer.lock:
                    outer.requests.append({"path": self.path, "body": body})
                    call_index = len(outer.requests)
                status, payload = outer.respond(body, call_index)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))

            def log_message(self, *args):
                pass

        return Handler

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def wait_requests(self, count, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self.lock:
                if len(self.requests) >= count:
                    return True
            time.sleep(0.02)
        return False

    @staticmethod
    def default_respond(body, call_index):
        return 200, MockOpenAIServer.response(f"识别结果-{call_index}")

    @staticmethod
    def response(content):
        return {
            "id": "chatcmpl-e2e",
            "object": "chat.completion",
            "created": 1_700_000_000,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }


@pytest.fixture
def e2e_server():
    server = MockOpenAIServer().start()
    yield server
    server.stop()


@pytest.fixture
def make_pdf(tmp_path):
    def _make(name="doc.pdf", pages=3):
        path = tmp_path / name
        doc = fitz.open()
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"E2E Page {i + 1}")
        doc.save(path)
        doc.close()
        return path

    return _make


def make_png(tmp_path, name="pic.png", size=(400, 300)):
    path = tmp_path / name
    Image.new("RGB", size, (20, 80, 160)).save(path, "PNG")
    return path


def make_service(tmp_path, server, **kwargs):
    kwargs.setdefault("max_workers", 2)
    kwargs.setdefault("pdf_scale", 1.5)
    kwargs.setdefault("output_dir", str(tmp_path))
    return ProcessingService(
        api_key="test-key",
        base_url=f"http://127.0.0.1:{server.port}/v1",
        model_name="gpt-4o",
        logger_inst=StructuredLogger(str(tmp_path / "e2e.log")),
        **kwargs,
    )


def test_e2e_pdf_pipeline_saves_markdown(tmp_path, e2e_server, make_pdf):
    pdf = make_pdf(pages=3)
    service = make_service(tmp_path, e2e_server)
    results = service.process_files([str(pdf)], "识别文档")

    assert results["doc"][0] is True
    out_path = Path(results["doc"][1])
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    for i in range(1, 4):
        assert f"识别结果-{i}" in content

    assert e2e_server.wait_requests(3)
    body = e2e_server.requests[0]["body"]
    assert body["model"] == "gpt-4o"
    assert body["messages"][0]["role"] == "system"
    image_url = body["messages"][-1]["content"][0]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")


def test_e2e_image_pipeline_multi_files(tmp_path, e2e_server):
    png = make_png(tmp_path, "pic.png")
    jpg = tmp_path / "photo.jpg"
    Image.new("RGB", (200, 150), (200, 20, 20)).save(jpg, "JPEG")

    service = make_service(tmp_path, e2e_server)
    results = service.process_files([str(png), str(jpg)], "识别图片")

    assert results["pic"][0] is True
    assert results["photo"][0] is True
    assert (tmp_path / "pic_ocr.md").exists()
    assert (tmp_path / "photo_ocr.md").exists()
    assert e2e_server.wait_requests(2)
    pic_content = (tmp_path / "pic_ocr.md").read_text(encoding="utf-8").strip()
    photo_content = (tmp_path / "photo_ocr.md").read_text(encoding="utf-8").strip()
    # 并发请求下服务端返回顺序不固定，只验证两份文件各拿到一个结果
    assert {pic_content, photo_content} == {"识别结果-1", "识别结果-2"}


def test_e2e_few_shot_messages_flow(tmp_path, e2e_server):
    png = make_png(tmp_path)
    example_png = make_png(tmp_path, "example.png")
    example_images = [("示例正确文本", example_png.read_bytes())]

    service = make_service(tmp_path, e2e_server)
    results = service.process_files([str(png)], "识别", example_images=example_images)

    assert results["pic"][0] is True
    assert e2e_server.wait_requests(1)
    messages = e2e_server.requests[0]["body"]["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert messages[2]["content"] == "示例正确文本"


def test_e2e_page_range(tmp_path, e2e_server, make_pdf):
    pdf = make_pdf(pages=3)
    service = make_service(tmp_path, e2e_server)
    results = service.process_files([str(pdf)], "识别", page_range_str="1,3")

    assert results["doc"][0] is True
    assert e2e_server.wait_requests(2)
    content = (tmp_path / "doc_ocr.md").read_text(encoding="utf-8")
    assert {"识别结果-1", "识别结果-2"} == set(content.split())


def test_e2e_copy_mode_no_file(tmp_path, e2e_server):
    png = make_png(tmp_path)
    service = make_service(tmp_path, e2e_server)
    ok, content = service.process_and_copy([str(png)], "识别")

    assert ok is True
    assert content == "识别结果-1"
    assert not list(tmp_path.glob("*_ocr.md"))
    assert e2e_server.wait_requests(1)


def test_e2e_network_retry_then_success(tmp_path, e2e_server, monkeypatch):
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)

    def respond(body, call_index):
        if call_index == 1:
            return 500, {"error": {"message": "server boom"}}
        return 200, MockOpenAIServer.response("重试成功")

    server = MockOpenAIServer(respond=respond).start()
    try:
        service = make_service(tmp_path, server)
        png = make_png(tmp_path)
        results = service.process_files([str(png)], "识别")
        assert results["pic"][0] is True
        assert "重试成功" in (tmp_path / "pic_ocr.md").read_text(encoding="utf-8")
        assert server.wait_requests(2)
    finally:
        server.stop()


def test_e2e_business_retry_empty_then_success(tmp_path, e2e_server, monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)

    def respond(body, call_index):
        if call_index == 1:
            return 200, MockOpenAIServer.response("")
        return 200, MockOpenAIServer.response("最终内容")

    server = MockOpenAIServer(respond=respond).start()
    try:
        service = make_service(tmp_path, server)
        png = make_png(tmp_path)
        results = service.process_files([str(png)], "识别")
        assert results["pic"][0] is True
        assert "最终内容" in (tmp_path / "pic_ocr.md").read_text(encoding="utf-8")
        assert server.wait_requests(2)
    finally:
        server.stop()


def test_e2e_api_failure_records_note(tmp_path, e2e_server, monkeypatch):
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)

    def respond(body, call_index):
        return 500, {"error": {"message": "always down"}}

    server = MockOpenAIServer(respond=respond).start()
    try:
        service = make_service(tmp_path, server)
        png = make_png(tmp_path)
        results = service.process_files([str(png)], "识别")
        # 客户端默认重试 3 次：1 次请求 + 3 次重试 = 4 次
        assert server.wait_requests(4)
        content = (tmp_path / "pic_ocr.md").read_text(encoding="utf-8")
        assert "未识别到有效内容" in content
        assert "识别失败" in content
    finally:
        server.stop()


def test_e2e_cancel_stops_pipeline(tmp_path, e2e_server):
    first_seen = threading.Event()

    def respond(body, call_index):
        if call_index == 1:
            first_seen.set()
            time.sleep(0.4)
        return 200, MockOpenAIServer.response(f"内容-{call_index}")

    server = MockOpenAIServer(respond=respond).start()
    try:
        service = make_service(tmp_path, server, max_workers=1)
        pngs = [make_png(tmp_path, f"p{i}.png") for i in range(3)]
        result = {}

        def run():
            nonlocal result
            result = service.process_files([str(p) for p in pngs], "识别")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert first_seen.wait(timeout=10)
        service.request_cancel()
        thread.join(timeout=15)

        # 取消后应保存已完成的部分结果
        assert result, "取消后应返回已完成的部分结果"
        assert all(ok for ok, _ in result.values())
        saved = list(tmp_path.glob("*_ocr.md"))
        assert len(saved) == 1
        assert "内容-1" in saved[0].read_text(encoding="utf-8")
        with server.lock:
            assert len(server.requests) == 1
    finally:
        server.stop()


def test_e2e_gui_save_controller_with_real_service(tmp_path, e2e_server):
    service = make_service(tmp_path, e2e_server)
    controller = SaveController(service)
    png = make_png(tmp_path)

    result = controller.run([str(png)], "识别", "")
    assert result.ok is True
    assert result.error == ""
    assert result.results["pic"][0] is True
    assert (tmp_path / "pic_ocr.md").exists()
    assert e2e_server.wait_requests(1)


def test_e2e_gui_copy_controller_with_real_service(tmp_path, e2e_server):
    service = make_service(tmp_path, e2e_server)
    controller = CopyController(service)
    png = make_png(tmp_path)

    ok, content = controller.run([str(png)], "识别", "")
    assert ok is True
    assert content == "识别结果-1"
    assert e2e_server.wait_requests(1)
