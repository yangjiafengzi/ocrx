# -- coding: utf-8 --
"""Preflight validation helpers unit tests."""

from ocrx.gui.validation import (
    COPY_MAX_PAGES,
    ERR_EMPTY_PROMPT,
    SUPPORTED_SUFFIXES,
    copy_page_limit_error,
    count_run_pages,
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


# -- copy page cap (COPY_MAX_PAGES product guard) --


def test_copy_max_pages_is_ten():
    assert COPY_MAX_PAGES == 10


def test_count_run_pages_images_count_one_each():
    pages = count_run_pages(["a.png", "b.jpg", "c.gif"], "", lambda p: 99)
    assert pages == 3


def test_count_run_pages_pdf_uses_page_count():
    counts = {"doc.pdf": 7}
    pages = count_run_pages(["doc.pdf"], "", counts.__getitem__)
    assert pages == 7


def test_count_run_pages_unreadable_pdf_counts_one():
    def boom(path):
        raise RuntimeError("cannot open")

    assert count_run_pages(["doc.pdf"], "", boom) == 1


def test_count_run_pages_range_caps_pdf_pages():
    counts = {"doc.pdf": 20}
    assert count_run_pages(["doc.pdf"], "1-5", counts.__getitem__) == 5
    assert count_run_pages(["doc.pdf"], "1,3,5", counts.__getitem__) == 3


def test_count_run_pages_range_applies_per_pdf():
    # The service feeds the same range to every PDF, so the cap estimate does too.
    counts = {"a.pdf": 20, "b.pdf": 20}
    assert count_run_pages(["a.pdf", "b.pdf"], "1-3", counts.__getitem__) == 6


def test_count_run_pages_images_ignore_range():
    # ProcessingService ignores page ranges for plain images (always 1 page).
    assert count_run_pages(["a.png", "b.png"], "1-1", lambda p: 1) == 2


def test_count_run_pages_range_beyond_pdf_end_selects_nothing():
    counts = {"doc.pdf": 2}
    assert count_run_pages(["doc.pdf"], "5-8", counts.__getitem__) == 0


def test_count_run_pages_mixed_files():
    counts = {"doc.pdf": 20}
    pages = count_run_pages(["doc.pdf", "a.png"], "1-4", counts.__getitem__)
    assert pages == 5


def test_copy_page_limit_error_mentions_save_mode_and_page_range():
    msg = copy_page_limit_error(12)
    assert "识别并保存" in msg
    assert "页面范围" in msg
    assert str(COPY_MAX_PAGES) in msg
    assert "12" in msg


# -- empty prompt product guard --


def test_validate_preflight_rejects_empty_prompt():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.png"],
        "",
        "",
    )
    assert errors == [ERR_EMPTY_PROMPT]


def test_validate_preflight_rejects_whitespace_prompt():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.png"],
        "",
        "   ",
    )
    assert ERR_EMPTY_PROMPT in errors
    assert ERR_EMPTY_PROMPT == "请填写提示词"


def test_validate_preflight_accepts_nonempty_prompt():
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.png"],
        "",
        "识别文字",
    )
    assert errors == []


def test_validate_preflight_prompt_none_skips_check():
    # Back-compat: callers that do not pass a prompt keep the old contract.
    errors = validate_preflight(
        {"API_KEY": "k", "BASE_URL": "https://x", "MODEL_NAME": "m"},
        ["a.png"],
        "",
    )
    assert errors == []
