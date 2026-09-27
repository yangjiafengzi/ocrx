# -- coding: utf-8 --
"""AppContext unit tests."""

from pathlib import Path

import pytest

from ocrx.gui.app_context import AppContext
from ocrx.gui.session_state import SessionState


@pytest.fixture(autouse=True)
def _fake_home(monkeypatch, tmp_path):
    """Redirect Path.home() so no default path can reach the real home."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    return fake_home


def make_context(tmp_path: Path) -> AppContext:
    return AppContext(
        config_path=str(tmp_path / "cfg.json"),
        example_path=str(tmp_path / "examples"),
        log_path=str(tmp_path / "app.log"),
    )


def test_app_context_uses_injected_paths(tmp_path):
    ctx = make_context(tmp_path)

    owned = (
        Path(ctx.config.config_file_path),
        Path(ctx.examples.library_path),
        Path(ctx.logger.log_file_path),
    )
    assert owned == (
        tmp_path / "cfg.json",
        tmp_path / "examples",
        tmp_path / "app.log",
    )
    for path in owned:
        assert path.is_relative_to(tmp_path)


def test_app_context_config_and_state_defaults(tmp_path):
    ctx = make_context(tmp_path)

    assert ctx.config.config["MAX_WORKERS"] == "10"
    assert ctx.config.config["PDF_SCALE_FACTOR"] == "3.0"
    assert isinstance(ctx.session_state, SessionState)
    assert ctx.session_state.file_paths == []
    assert ctx.session_state.page_range == ""
    assert ctx.session_state.selected_example_ids == []
    assert ctx.session_state.prompt_text == ""
    assert ctx.session_state.last_result == ""


def test_app_context_rebuild_service_uses_config(tmp_path):
    ctx = make_context(tmp_path)
    ctx.config.set("API_KEY", "k")
    ctx.config.set("BASE_URL", "http://127.0.0.1")
    ctx.config.set("MODEL_NAME", "m")
    ctx.config.set("OUTPUT_DIR", str(tmp_path / "out"))
    ctx.rebuild_service()

    assert ctx.service is not None
    assert ctx.service.api_key == "k"
    assert ctx.service.base_url == "http://127.0.0.1"
    assert ctx.service.model_name == "m"
    assert Path(ctx.service.output_dir) == tmp_path / "out"


def test_rebuild_service_replaces_previous_instance(tmp_path):
    ctx = make_context(tmp_path)
    first = ctx.service
    ctx.rebuild_service()
    assert ctx.service is not first


def test_load_example_images(tmp_path, sample_png):
    ctx = make_context(tmp_path)
    example = ctx.examples.add_example(str(sample_png), "参考文本", "描述")
    assert example is not None

    loaded = ctx.load_example_images([example.id])
    assert len(loaded) == 1
    text, data = loaded[0]
    assert text == "参考文本"
    assert data == Path(example.image_path).read_bytes()


def test_load_example_images_skips_unknown_and_missing(tmp_path, sample_png):
    ctx = make_context(tmp_path)
    example = ctx.examples.add_example(str(sample_png), "文本")
    assert example is not None
    Path(example.image_path).unlink()

    assert ctx.load_example_images(["nope", example.id]) == []


def test_clipboard_reuses_injected_root(tmp_path, monkeypatch):
    import ocrx.clipboard as cb

    def boom():
        raise AssertionError("must not create a new tk.Tk() when root is given")

    monkeypatch.setattr(cb.tk, "Tk", boom)
    copied = []

    class FakeRoot:
        def clipboard_clear(self):
            pass

        def clipboard_append(self, content):
            copied.append(content)

        def update(self):
            pass

    ctx = AppContext(
        config_path=str(tmp_path / "cfg.json"),
        example_path=str(tmp_path / "examples"),
        log_path=str(tmp_path / "app.log"),
        root=FakeRoot(),
    )
    assert ctx.clipboard.copy_to_clipboard("abc") is True
    assert copied == ["abc"]
