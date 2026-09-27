# -- coding: utf-8 --
"""SessionState unit tests."""

from ocrx.gui.session_state import SessionState


def test_session_state_defaults():
    state = SessionState()
    assert state.file_paths == []
    assert state.page_range == ""
    assert state.selected_example_ids == []
    assert state.prompt_text == ""
    assert state.output_dir == ""
    assert state.last_result == ""


def test_session_state_independent_defaults():
    a = SessionState()
    b = SessionState()
    a.file_paths.append("x.pdf")
    a.selected_example_ids.append("ex1")
    assert b.file_paths == []
    assert b.selected_example_ids == []
