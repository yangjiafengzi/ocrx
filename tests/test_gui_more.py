# -- coding: utf-8 --
"""更多 GUI 组件逻辑测试（全部使用假控件，无需真实窗口）。

覆盖 ExampleManagerUI（示例库次级视图的核心）与 theme 滚动条工具。
"""

from types import SimpleNamespace

from ocrx.example_library import ExampleLibrary
from ocrx.gui.example_manager_ui import ExampleManagerUI


class FakeLabel:
    def __init__(self):
        self.text = None

    def config(self, text=None):
        self.text = text


class FakeTree:
    def __init__(self):
        self.children = []
        self.rows = {}
        self.next_id = 0
        self.selected = []
        self.identify_region = "cell"
        self.identify_col = "#1"
        self.identify_row_id = "r0"

    def get_children(self):
        return list(self.children)

    def delete(self, item):
        if item in self.children:
            self.children.remove(item)
        self.rows.pop(item, None)

    def insert(self, parent, index, values=None, tags=()):
        item = f"r{self.next_id}"
        self.next_id += 1
        self.children.append(item)
        self.rows[item] = {"values": list(values or []), "tags": list(tags)}
        return item

    def item(self, item, option=None, **kwargs):
        if kwargs:
            self.rows[item].update(kwargs)
            return
        if option is None:
            return dict(self.rows[item])
        return self.rows[item][option]

    def selection(self):
        return list(self.selected)

    def index(self, item):
        return self.children.index(item)

    def identify(self, what, x, y):
        if what == "region":
            return self.identify_region
        if what == "column":
            return self.identify_col
        if what == "row":
            return self.identify_row_id
        return ""

    def identify_column(self, x):
        return self.identify_col

    def identify_row(self, y):
        return self.identify_row_id


# ---------- ExampleManagerUI 逻辑 ----------


def make_example_ui(tmp_path):
    library = ExampleLibrary(str(tmp_path / "library"))
    ui = ExampleManagerUI.__new__(ExampleManagerUI)
    ui.library = library
    ui.selected_examples = []
    ui.on_selection_change = None
    ui.on_data_change = None
    ui.tree = FakeTree()
    ui.stats_label = FakeLabel()
    return library, ui


def test_example_ui_refresh_list(tmp_path, sample_png):
    library, ui = make_example_ui(tmp_path)
    library.add_example(str(sample_png), "示例文本", "标签")
    ui.refresh_list()
    assert len(ui.tree.children) == 1
    assert ui.stats_label.text == "共 1 个示例"
    values = ui.tree.item(ui.tree.children[0], "values")
    assert values[2] == "标签"


def test_example_ui_selection_toggle(tmp_path, sample_png):
    library, ui = make_example_ui(tmp_path)
    example = library.add_example(str(sample_png), "文本")
    ui.refresh_list()
    changes = []
    ui.on_selection_change = lambda ids: changes.append(ids)
    ui.tree.identify_row_id = ui.tree.children[0]
    event = SimpleNamespace(x=0, y=0)
    ui._on_tree_click(event)
    assert ui.selected_examples == [example.id]
    assert changes == [[example.id]]
    ui._on_tree_click(event)
    assert ui.selected_examples == []


def test_example_ui_delete_selected(tmp_path, sample_png, monkeypatch):
    library, ui = make_example_ui(tmp_path)
    example = library.add_example(str(sample_png), "文本")
    ui.refresh_list()
    ui.selected_examples = [example.id]
    monkeypatch.setattr(
        "ocrx.gui.example_manager_ui.messagebox.askyesno", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "ocrx.gui.example_manager_ui.messagebox.showinfo", lambda *a, **k: None
    )
    ui._on_delete_selected()
    assert library.get_stats()["total_examples"] == 0
    assert ui.tree.children == []


def test_example_ui_select_all_and_by_description(tmp_path, sample_png):
    library, ui = make_example_ui(tmp_path)
    library.add_example(str(sample_png), "a", "手写")
    library.add_example(str(sample_png), "b", "印刷")
    ui.refresh_list()
    ui.select_all()
    assert len(ui.selected_examples) == 2
    ui.clear_selection()
    assert ui.selected_examples == []
    ui.select_by_description("手写")
    assert len(ui.selected_examples) == 1


def test_example_preview_truncation():
    long_text = "这是一个很长的示例识别文本内容" * 10
    preview = ExampleManagerUI._make_preview(long_text)
    assert preview.endswith("…")
    assert len(preview) < len(long_text)
    # 半角字符占位更少，允许显示更多
    ascii_preview = ExampleManagerUI._make_preview("a" * 100)
    assert ascii_preview.endswith("…")
    assert len(ascii_preview) > len(preview)
    # 短文本原样返回
    short = "短文本"
    assert ExampleManagerUI._make_preview(short) == short


# ---------- theme 滚动条工具 ----------


def test_attach_scrollbar_hides_and_min_thumb():
    """回归测试：滚动条按需显示 + 内容极少时滑块保持最小尺寸。"""
    from ocrx.gui.theme import attach_scrollbar

    class FakeScrollbar:
        def __init__(self):
            self.mapped = True
            self.value = (0.0, 1.0)
            self.grid_opts = {"row": 0, "column": 1, "sticky": "ns"}

        def winfo_manager(self):
            return "grid"

        def winfo_ismapped(self):
            return self.mapped

        def winfo_height(self):
            return 200

        def grid_info(self):
            return self.grid_opts

        def grid(self, **kwargs):
            self.mapped = True

        def grid_remove(self):
            self.mapped = False

        def set(self, first, last):
            self.value = (float(first), float(last))

        def get(self):
            return self.value

    class FakeTarget:
        def __init__(self):
            self.view = (0.0, 0.2)

        def configure(self, **kwargs):
            self.yscrollcommand = kwargs.get("yscrollcommand")

        def yview(self):
            return self.view

    sb = FakeScrollbar()
    target = FakeTarget()
    setter = attach_scrollbar(sb, target, orient="vertical", manager="grid")

    # 有溢出 → 显示
    assert sb.mapped is True
    # 内容放得下 → 隐藏，不显示满条假滑块
    target.view = (0.0, 1.0)
    setter(0.0, 1.0)
    assert sb.mapped is False
    # 内容极多 → 显示且滑块有最小尺寸
    target.view = (0.0, 0.005)
    setter(0.0, 0.005)
    assert sb.mapped is True
    first, last = sb.get()
    assert last - first >= 40 / 200 - 1e-9, "滑块不应小到消失"
