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


def test_parse_page_range_tokens_rejects_unicode_digit_tokens():
    # Regression: str.isdigit() accepts e.g. "²" but int("²") raises ValueError.
    assert parse_page_range_tokens("1-²") is None
    assert parse_page_range_tokens("²-3") is None
    assert parse_page_range_tokens("²") is None
    assert parse_page_range_tokens("1²") is None


def test_validate_preflight_unicode_page_range_errors_without_raising():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.pdf"],
        "1-²",
    )
    assert any("页码范围" in e for e in errors)


def test_parse_page_range_tokens_rejects_huge_ranges():
    # Regression: expanding 1-99999999 must not materialize ~1e8 pages.
    assert parse_page_range_tokens("1-99999999") is None
    assert parse_page_range_tokens("1-10001") is None
    assert parse_page_range_tokens("1-10000") == list(range(1, 10001))


def test_parse_page_range_huge_range_returns_none():
    assert parse_page_range("1-99999999", 50) is None


def test_validate_preflight_rejects_huge_page_range():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.pdf"],
        "1-99999999",
    )
    assert any("页码范围" in e for e in errors)


def test_parse_page_range_tokens_empty_contract():
    # Empty, whitespace-only, and separator-only input all mean "no explicit
    # pages" (i.e. all pages); empty segments between tokens are ignored.
    assert parse_page_range_tokens("") == []
    assert parse_page_range_tokens("   ") == []
    assert parse_page_range_tokens(",") == []
    assert parse_page_range_tokens(" , , ") == []
    assert parse_page_range_tokens("1,,2,") == [1, 2]


def test_parse_page_range_empty_segments_mean_all_pages():
    assert parse_page_range(",", 3) == [1, 2, 3]
    assert parse_page_range("1,,2,", 5) == [1, 2]
