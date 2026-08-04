# -- coding: utf-8 --
"""ImageProcessor 单元测试。"""

import io

from PIL import Image

from ocrx.image_processor import ImageProcessor


def make_proc():
    return ImageProcessor()


def test_is_supported_image():
    proc = make_proc()
    assert proc.is_supported_image("a.png")
    assert proc.is_supported_image("a.JPG")
    assert proc.is_supported_image("a.tiff")
    assert proc.is_supported_image("a.heic")
    assert not proc.is_supported_image("a.txt")
    assert not proc.is_supported_image("a.pdf")


def test_png_read(sample_png):
    data = make_proc().image_file_to_bytes(str(sample_png))
    assert data.startswith(b"\x89PNG")


def test_jpg_read(sample_jpg):
    data = make_proc().image_file_to_bytes(str(sample_jpg))
    # 统一转换为 PNG，保证发送给 API 的 MIME 类型正确
    assert data.startswith(b"\x89PNG")
    with Image.open(io.BytesIO(data)) as img:
        assert img.mode == "RGB"


def test_gif_converted_to_png(sample_gif):
    data = make_proc().image_file_to_bytes(str(sample_gif))
    assert data.startswith(b"\x89PNG")
    with Image.open(io.BytesIO(data)) as img:
        assert img.mode == "RGB"


def test_rgba_png_converted_to_rgb(sample_rgba_png):
    # RGBA 的透明通道用白色背景合成后转为 RGB PNG
    data = make_proc().image_file_to_bytes(str(sample_rgba_png))
    assert data.startswith(b"\x89PNG")
    with Image.open(io.BytesIO(data)) as img:
        assert img.mode == "RGB"


def test_large_image_downscaled(tmp_path):
    proc = make_proc()
    path = tmp_path / "large.png"
    Image.new("RGB", (4096, 2048), (10, 20, 30)).save(path, "PNG")
    data = proc.image_file_to_bytes(str(path))
    assert data is not None
    with Image.open(io.BytesIO(data)) as img:
        assert max(img.size) <= proc.DEFAULT_MAX_DIMENSION
        assert img.mode == "RGB"


def test_max_dimension_respected(tmp_path):
    proc = make_proc()
    path = tmp_path / "big.jpg"
    Image.new("RGB", (3000, 1000), (1, 2, 3)).save(path, "JPEG")
    data = proc.image_file_to_bytes(str(path), max_dimension=1000)
    with Image.open(io.BytesIO(data)) as img:
        assert max(img.size) == 1000


def test_missing_file_returns_none(tmp_path):
    assert make_proc().image_file_to_bytes(str(tmp_path / "nope.png")) is None


def test_corrupt_file_returns_none(tmp_path):
    path = tmp_path / "bad.png"
    path.write_bytes(b"not an image at all")
    assert make_proc().image_file_to_bytes(str(path)) is None


def test_validate_image(sample_png, tmp_path):
    proc = make_proc()
    ok, _ = proc.validate_image(str(sample_png))
    assert ok is True

    bad = tmp_path / "bad.png"
    bad.write_bytes(b"garbage")
    ok, msg = proc.validate_image(str(bad))
    assert ok is False
    assert "损坏" in msg


def test_load_image(sample_png):
    result = make_proc().load_image(str(sample_png))
    assert result is not None
    assert result[0][0] == 1
    assert result[0][1].startswith(b"\x89PNG")


def test_load_images_skips_invalid(tmp_path, sample_png):
    missing = tmp_path / "missing.png"
    images = make_proc().load_images([str(sample_png), str(missing)])
    assert len(images) == 1
    assert images[0][0] == "sample"
