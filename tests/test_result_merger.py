# -- coding: utf-8 --
"""ResultMerger 单元测试。"""

import pytest

from ocrx.result_merger import ResultMerger


def make_merger(tmp_path):
    return ResultMerger(str(tmp_path))


def test_merge_sorted_and_joined(tmp_path):
    merger = make_merger(tmp_path)
    results = [
        (("a", 2), "第二页"),
        (("a", 1), "第一页"),
        (("b", 1), "B文件"),
    ]
    out = merger.merge_contents_to_markdown(results)
    assert out == "第一页\n\n第二页\n\nB文件"


def test_merge_skips_failures_and_adds_notes(tmp_path):
    merger = make_merger(tmp_path)
    results = [
        (("a", 1), "正常内容"),
        (("a", 2), "识别失败（已重试5次）：超时"),
    ]
    out = merger.merge_contents_to_markdown(results)
    assert "正常内容" in out
    assert "识别说明" in out
    assert "识别失败（已重试5次）：超时" in out
    assert "第 2 页" in out


def test_merge_all_failures_keeps_notes(tmp_path):
    merger = make_merger(tmp_path)
    results = [(("a", 1), "识别失败：API返回空内容")]
    out = merger.merge_contents_to_markdown(results)
    assert "*未识别到有效内容*" in out
    assert "识别失败：API返回空内容" in out
    assert "第 1 页" in out


def test_merge_empty_returns_placeholder(tmp_path):
    merger = make_merger(tmp_path)
    assert merger.merge_contents_to_markdown([]) == "*未识别到有效内容*"


def test_save_to_file(tmp_path):
    merger = make_merger(tmp_path)
    path = merger.save_to_file("# 标题", "demo")
    assert str(tmp_path / "demo_ocr.md") == path
    assert (tmp_path / "demo_ocr.md").read_text(encoding="utf-8") == "# 标题"


def test_save_multiple_files(tmp_path):
    merger = make_merger(tmp_path)
    results = {
        "a": [(("a", 1), "A内容")],
        "b": [(("b", 1), "B内容")],
    }
    paths = merger.save_multiple_files(results, str(tmp_path))
    assert (tmp_path / "a_ocr.md").exists()
    assert (tmp_path / "b_ocr.md").exists()
    assert paths["a"] == str(tmp_path / "a_ocr.md")
