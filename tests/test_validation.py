# -- coding: utf-8 --
"""Preflight validation helpers unit tests."""

from ocrx.gui.validation import SUPPORTED_SUFFIXES, parse_page_range, validate_preflight


def test_validate_preflight_missing_fields():
    errors = validate_preflight({"API_KEY": "", "BASE_URL": "", "MODEL_NAME": ""}, [], "")
    assert any("API" in e or "Base" in e or "Model" in e for e in errors)
    assert any("文件" in e for e in errors)


def test_parse_page_range_ok():
    assert parse_page_range("1,3", 5) == [1, 3]
    assert parse_page_range("2-3", 5) == [2, 3]


def test_parse_page_range_invalid():
    assert parse_page_range("9", 3) is None
    assert parse_page_range("abc", 3) is None


def test_parse_page_range_empty_means_all_pages():
    assert parse_page_range("", 4) == [1, 2, 3, 4]
    assert parse_page_range("   ", 2) == [1, 2]


def test_parse_page_range_mixed_and_unordered():
    assert parse_page_range("3,1,2-2", 5) == [1, 2, 3]


def test_validate_preflight_ok():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.pdf", "b.PNG"],
        "1-2",
    )
    assert errors == []


def test_validate_preflight_unsupported_extension():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.txt"],
        "",
    )
    assert any("a.txt" in e for e in errors)
    assert ".txt" not in SUPPORTED_SUFFIXES


def test_validate_preflight_bad_page_range_token():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.pdf"],
        "abc",
    )
    assert errors
