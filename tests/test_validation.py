# -- coding: utf-8 --
"""Preflight validation helpers unit tests."""

from ocrx.gui.validation import (
    SUPPORTED_SUFFIXES,
    parse_page_range,
    parse_page_range_tokens,
    validate_preflight,
)


def test_validate_preflight_missing_fields():
    errors = validate_preflight({"API_KEY": "", "BASE_URL": "", "MODEL_NAME": ""}, [], "")
    assert any("API Key" in e for e in errors)
    assert any("Base URL" in e for e in errors)
    assert any("Model Name" in e for e in errors)
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


def test_validate_preflight_rejects_invalid_page_range_structure():
    for bad in ("5-2", "0", "-1", "1--3"):
        errors = validate_preflight(
            {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
            ["a.pdf"],
            bad,
        )
        assert any("页码范围" in e for e in errors), bad


def test_validate_preflight_accepts_valid_page_range():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.pdf"],
        "1,3,5-10",
    )
    assert errors == []


def test_validate_preflight_blank_page_range_is_ok():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.pdf"],
        "   ",
    )
    assert errors == []


def test_parse_page_range_tokens_structure_only():
    assert parse_page_range_tokens("1,3,5-10") == [1, 3, 5, 6, 7, 8, 9, 10]
    assert parse_page_range_tokens("") == []
    assert parse_page_range_tokens("   ") == []


def test_parse_page_range_tokens_rejects_invalid_structure():
    assert parse_page_range_tokens("5-2") is None
    assert parse_page_range_tokens("0") is None
    assert parse_page_range_tokens("-1") is None
    assert parse_page_range_tokens("1--3") is None
    assert parse_page_range_tokens("0-3") is None
    assert parse_page_range_tokens("abc") is None
