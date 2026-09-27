# -- coding: utf-8 --
"""Shared local OpenAI-compatible mock server for e2e tests."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockOpenAIServer:
    """本地 OpenAI 兼容 Mock 服务。"""

    def __init__(self, respond=None):
        self.requests = []
        self.lock = threading.Lock()
        self.respond = respond or self.default_respond
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self):
        """OpenAI client base URL (must end with ``/v1``)."""
        return f"http://127.0.0.1:{self.port}/v1"

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
