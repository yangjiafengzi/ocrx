# -- coding: utf-8 --
"""PDFProcessor 单元测试。"""

import pytest

from ocrx.pdf_processor import PDFProcessor


def make_proc():
    return PDFProcessor(scale_factor=1.0)


def test_parse_page_range_all_variants():
    proc = make_proc()
    assert proc._parse_page_range(None, 5) == [1, 2, 3, 4, 5]
    assert proc._parse_page_range("", 5) == [1, 2, 3, 4, 5]
    assert proc._parse_page_range("   ", 5) == [1, 2, 3, 4, 5]


def test_parse_page_range_specific():
    proc = make_proc()
    assert proc._parse_page_range("1,3,5-7", 10) == [1, 3, 5, 6, 7]


def test_parse_page_range_invalid_parts_ignored():
    proc = make_proc()
    assert proc._parse_page_range("1,abc,-3,2-,5-10", 10) == [1, 5, 6, 7, 8, 9, 10]


def test_parse_page_range_reversed_is_empty():
    proc = make_proc()
    assert proc._parse_page_range("10-5", 10) == []


def test_pdf_to_images(sample_pdf):
    images = make_proc().pdf_to_images(str(sample_pdf))
    assert [page for page, _ in images] == [1, 2, 3]
    for _, data in images:
        assert data.startswith(b"\x89PNG")


def test_pdf_to_images_with_range(sample_pdf):
    images = make_proc().pdf_to_images(str(sample_pdf), "1,3")
    assert [page for page, _ in images] == [1, 3]


def test_pdf_to_images_filters_out_of_range(sample_pdf):
    images = make_proc().pdf_to_images(str(sample_pdf), "1,99")
    assert [page for page, _ in images] == [1]


def test_pdf_to_images_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        make_proc().pdf_to_images(str(tmp_path / "missing.pdf"))


def test_get_pdf_info(sample_pdf):
    info = make_proc().get_pdf_info(str(sample_pdf))
    assert info["page_count"] == 3
    assert info["file_size"] > 0
    assert "metadata" in info


def test_get_pdf_page_count(sample_pdf):
    # 回归测试：copy_handler 曾调用不存在的 get_pdf_page_count 方法
    assert make_proc().get_pdf_page_count(str(sample_pdf)) == 3
