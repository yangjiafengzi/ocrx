# -- coding: utf-8 --
"""ExampleLibrary 单元测试。"""

from pathlib import Path

from ocrx.example_library import ExampleLibrary


def make_library(tmp_path):
    return ExampleLibrary(str(tmp_path / "library"))


def test_add_and_get(tmp_path, sample_png):
    lib = make_library(tmp_path)
    example = lib.add_example(str(sample_png), "正确文本", "手写")
    assert example is not None
    assert lib.get_example(example.id) is example
    assert lib.get_example("nope") is None


def test_add_copies_image_as_png(tmp_path, sample_png):
    lib = make_library(tmp_path)
    example = lib.add_example(str(sample_png), "文本")
    stored = Path(example.image_path)
    assert stored.exists()
    assert stored.suffix == ".png"
    assert stored.read_bytes().startswith(b"\x89PNG")


def test_add_missing_image_returns_none(tmp_path):
    lib = make_library(tmp_path)
    assert lib.add_example(str(tmp_path / "missing.png"), "文本") is None
    assert lib.get_stats()["total_examples"] == 0


def test_add_duplicate_image_gets_unique_ids(tmp_path, sample_png):
    """回归测试：同一图片添加两次不应产生重复 ID。"""
    lib = make_library(tmp_path)
    first = lib.add_example(str(sample_png), "第一份")
    second = lib.add_example(str(sample_png), "第二份")
    assert first is not None and second is not None
    ids = [ex.id for ex in lib.get_all_examples()]
    assert len(ids) == len(set(ids)) == 2
    paths = {Path(ex.image_path) for ex in lib.get_all_examples()}
    assert len(paths) == 2
    assert lib.get_example(first.id).text == "第一份"
    assert lib.get_example(second.id).text == "第二份"


def test_remove_example_deletes_file(tmp_path, sample_png):
    lib = make_library(tmp_path)
    example = lib.add_example(str(sample_png), "文本")
    img_path = Path(example.image_path)
    assert lib.remove_example(example.id) is True
    assert not img_path.exists()
    assert lib.get_stats()["total_examples"] == 0


def test_remove_missing_returns_false(tmp_path):
    lib = make_library(tmp_path)
    assert lib.remove_example("missing") is False


def test_clear_all(tmp_path, sample_png):
    lib = make_library(tmp_path)
    lib.add_example(str(sample_png), "a")
    lib.add_example(str(sample_png), "b")
    assert lib.clear_all() is True
    assert lib.get_stats()["total_examples"] == 0
    assert list((tmp_path / "library" / "images").iterdir()) == []


def test_search_by_description(tmp_path, sample_png):
    lib = make_library(tmp_path)
    lib.add_example(str(sample_png), "a", "手写笔记")
    lib.add_example(str(sample_png), "b", "印刷材料")
    found = lib.get_examples_by_description("手写")
    assert len(found) == 1
    assert found[0].description == "手写笔记"


def test_persist_and_reload(tmp_path, sample_png):
    lib = make_library(tmp_path)
    lib.add_example(str(sample_png), "持久化内容", "标签")
    lib2 = make_library(tmp_path)
    assert len(lib2.get_all_examples()) == 1
    assert lib2.get_all_examples()[0].text == "持久化内容"


def test_get_stats(tmp_path):
    lib = make_library(tmp_path)
    stats = lib.get_stats()
    assert stats["total_examples"] == 0
    assert stats["data_file"].endswith("examples.json")
