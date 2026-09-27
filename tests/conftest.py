# -- coding: utf-8 --
"""公共测试夹具。"""

import sys
from pathlib import Path

import fitz
import pytest
from PIL import Image

from tests.mock_openai import MockOpenAIServer

# 保证可以从仓库根目录导入 ocrx 包
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _save_image(path: Path, mode: str, color, fmt: str) -> Path:
    img = Image.new(mode, (32, 24), color)
    img.save(path, fmt)
    return path


@pytest.fixture
def sample_png(tmp_path):
    return _save_image(tmp_path / "sample.png", "RGB", (200, 30, 30), "PNG")


@pytest.fixture
def sample_jpg(tmp_path):
    return _save_image(tmp_path / "sample.jpg", "RGB", (30, 200, 30), "JPEG")


@pytest.fixture
def sample_gif(tmp_path):
    return _save_image(tmp_path / "sample.gif", "P", 0, "GIF")


@pytest.fixture
def sample_rgba_png(tmp_path):
    return _save_image(tmp_path / "sample_rgba.png", "RGBA", (30, 30, 200, 128), "PNG")


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def mock_openai_server():
    """Local OpenAI-compatible mock; ``base_url`` ends with ``/v1``."""
    server = MockOpenAIServer().start()
    try:
        yield server
    finally:
        server.stop()
