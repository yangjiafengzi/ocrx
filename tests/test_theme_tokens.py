# -- coding: utf-8 --
import customtkinter

from ocrx.gui import theme_tokens as tt

EXPECTED_COLOR_KEYS = (
    "primary",
    "primary_hover",
    "bg",
    "surface",
    "text",
    "muted",
    "border",
    "success",
    "danger",
)


def test_color_tokens_are_hex():
    for value in tt.COLORS.values():
        assert value.startswith("#") and len(value) == 7


def test_expected_color_keys_present_and_non_empty():
    for key in EXPECTED_COLOR_KEYS:
        assert key in tt.COLORS
        assert tt.COLORS[key]


def test_apply_appearance_is_idempotent():
    tt.apply_appearance()
    tt.apply_appearance()
    assert customtkinter.get_appearance_mode().lower() == "light"
