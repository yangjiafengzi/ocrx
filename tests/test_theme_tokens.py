# -- coding: utf-8 --
from ocrx.gui import theme_tokens as tt


def test_color_tokens_are_hex():
    for value in tt.COLORS.values():
        assert value.startswith("#") and len(value) == 7


def test_apply_appearance_is_idempotent():
    tt.apply_appearance()
    tt.apply_appearance()
    assert tt.FONT[0]
