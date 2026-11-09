"""Dẫn từng thao tác trên Excel (step.guide): chỗ đang dẫn theo vùng chọn và menu đang mở, tự quay lui khi
lệch; phiên chạy thử kịch bản theo quy trình báo bấm nhầm lệnh và lùi bước khi hoàn tác (không cần Excel).

Đã chạy thật trên Excel (bài 06): mở file → 1/4 khoanh tiêu đề cột D→F; chọn D→F → 2/4 nút Format; mở menu →
3/4 Hide & Unhide; mở menu con → 4/4 Unhide Columns; đóng menu → về 2/4; chỉ chọn cột D → về 1/4.
"""

import os
from pathlib import Path
from typing import Any

import openpyxl
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from excel_core.readers import read_workbook  # noqa: E402
from excel_core.snapshot import PropertyGroup, RangeRequest, ReadRequest  # noqa: E402
from tutor_desktop.agent.guide import Guide, GuideItem, parse_guide, position, selected_lines  # noqa: E402
from tutor_desktop.agent.preview_session import PreviewSession  # noqa: E402
from tutor_desktop.monitor.watcher import ExcelWatcher  # noqa: E402

SHEET = "S"
GUIDE = [
    {"action": "select", "axis": "cols", "lines": ["D", "E", "F"], "text": "Kéo chọn tiêu đề cột D → F"},
    {"action": "click", "control": "FormatCellsMenu", "tab": "TabHome", "text": "Bấm nút Format"},
    {"action": "click", "control": "HideUnhideMenu", "text": "Trỏ vào Hide & Unhide"},
    {"action": "click", "control": "ColumnsUnhide", "text": "Chọn Unhide Columns"},
]


def test_selected_lines_reads_whole_columns_cells_and_several_areas():
    assert selected_lines("$D:$F", "cols") == {"D", "E", "F"}
    assert selected_lines("$D$5:$F$9", "cols") == {"D", "E", "F"}
    assert selected_lines("$D:$E,$H:$H", "cols") == {"D", "E", "H"}
    assert selected_lines("$5:$7", "rows") == {"5", "6", "7"}
    assert selected_lines("$5:$7", "cols") == {"*"}  # chọn cả dòng: phủ mọi cột, không khớp bước chọn cột


def test_position_goes_forward_with_the_screen_and_back_when_it_changes():
    items = parse_guide({"guide": GUIDE})

    def at(selected: bool, shown: set[int]) -> int:
        return position(items, selected, lambda i: i in shown)

    assert at(False, {1, 2, 3}) == 0  # chưa chọn đúng vùng: dù menu đang mở vẫn dẫn chọn vùng trước
    assert at(True, {1}) == 1  # chọn xong: chỉ nút Format
    assert at(True, {1, 2}) == 2  # menu Format mở: chỉ Hide & Unhide
    assert at(True, {1, 2, 3}) == 3  # menu con mở: chỉ Unhide Columns
    assert at(True, set()) == 1  # nút chưa hiện (đang ở thẻ khác): vẫn ở bước bấm nút (khung chỉ vào thẻ)


class FakeLink:
    """Excel giả cho luồng giám sát: vùng chọn, tiêu đề cột, nút/mục menu đang hiện."""

    def __init__(self) -> None:
        self.address = "$A$1"
        self.open: set[str] = {"FormatCellsMenu"}

    def selection(self, _sheet: str) -> str:
        return self.address

    def header_rect(self, names: tuple[str, ...]) -> tuple[int, int, int, int]:
        assert names == ("D", "E", "F")
        return 100, 10, 300, 30

    def ui_target(self, control: str, _tab: str | None) -> tuple[tuple[int, int, int, int], str] | None:
        return ((400, 10, 480, 40), "control") if control in self.open else None


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def test_watcher_marks_only_the_current_place_and_reports_moves(app: QApplication):
    watcher = ExcelWatcher(Path("bai-06.xlsx"))
    moves: list[int] = []
    watcher.guide_moved.connect(moves.append)
    link, guide = FakeLink(), Guide(parse_guide({"guide": GUIDE}), SHEET)

    (mark,) = watcher._guide_marks(link, guide, busy=False)  # type: ignore[arg-type]
    assert (mark.rect, mark.label) == ((100, 10, 300, 30), "1/4. Kéo chọn tiêu đề cột D → F")
    link.address = "$D:$F"
    link.open |= {"HideUnhideMenu"}
    (mark,) = watcher._guide_marks(link, guide, busy=False)  # type: ignore[arg-type]
    assert mark.label == "3/4. Trỏ vào Hide & Unhide"
    link.address = "$A$1"  # Excel bận: dùng vùng chọn đọc lần trước ($D:$F)
    (mark,) = watcher._guide_marks(link, guide, busy=True)  # type: ignore[arg-type]
    assert mark.label.startswith("3/4")
    link.open = {"FormatCellsMenu"}
    watcher._guide_marks(link, guide, busy=False)  # type: ignore[arg-type]
    assert moves == [0, 2, 0]  # bỏ chọn vùng: quay về bước chọn


# ---------------------------------------------------------------- phiên chạy thử: bấm nhầm lệnh, hoàn tác
def build(path: Path, gap: int, hidden: tuple[str, ...] = ()) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = SHEET
    ws["B2"] = "DANH SÁCH HÀNG"
    rows = (("Mã hàng", "Tên hàng", "Số lượng", "Đơn giá"), ("A01", "Bút", 10, 5000))
    for row, values in enumerate(rows, start=4):
        for index, value in enumerate(values):
            ws.cell(row, 2 + index + (gap if index >= 2 else 0), value)
    for column in hidden:
        ws.column_dimensions[column].hidden = True
    wb.save(path)
    return path


def literal(address: str, value: str) -> dict[str, Any]:
    return {"type": "value_equals", "range": address, "expected": {"from": "literal", "value": value}}


def proc_step(step_id: str, operation: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    hints = [{"level": n, "text": "Gợi ý."} for n in range(1, 5)]
    return {
        "id": step_id,
        "title": step_id,
        "task": "Làm.",
        "targets": {"cells": [{"range": "D4", "role": "target"}]},
        "operation": operation,
        "checks": checks,
        "hints": hints,
        "guide": GUIDE,
    }


SCRIPT = {
    "schema_version": "1",
    "exercise": {"id": "quy-trinh", "title": "Cột", "sheet": SHEET},
    "steps": [
        proc_step(
            "hien_e",
            {"action": "unhide", "axis": "cols", "lines": ["E"]},
            [{"type": "row_col_hidden", "cols": "E", "hidden": False}],
        ),
        proc_step(
            "xoa_d_e",
            {"action": "delete", "axis": "cols", "lines": ["D", "E"]},
            [literal("C4", "Tên hàng"), literal("D4", "Số lượng")],
        ),
    ],
}
BOX = ReadRequest((RangeRequest(SHEET, "A1:H6", frozenset({PropertyGroup.VALUES, PropertyGroup.STRUCTURE})),))


def test_wrong_command_is_reported_and_undo_goes_back_a_step(tmp_path: Path):
    starter = build(tmp_path / "de.xlsx", gap=2, hidden=("E",))
    session = PreviewSession(SCRIPT, {}, read_workbook(starter, BOX))
    assert session.layout_box is not None and session.guide()[0] == GuideItem(
        "select", "Kéo chọn tiêu đề cột D → F", "cols", ("D", "E", "F")
    )
    assert session.guiding(show_targets=True) and not session.guiding()

    def evaluate(path: Path) -> Any:
        return session.evaluate(read_workbook(path, BOX))

    wrong = evaluate(
        build(tmp_path / "an-nham.xlsx", gap=2, hidden=("D", "E", "F"))
    )  # Hide Columns thay Unhide
    assert wrong.deviation == ("cột D đang bị ẩn", "cột F đang bị ẩn") and session.index == 0
    assert evaluate(build(tmp_path / "hien-e.xlsx", gap=2)).advanced  # làm lại đúng: qua bước 1
    undone = evaluate(starter)  # Ctrl+Z: cột E ẩn lại như lúc bắt đầu bước 1
    assert undone.rewound_to == 0 and session.index == 0 and "hien_e" not in session.done


def test_menu_items_used_by_generated_guides_are_in_the_catalog():
    from tutor_desktop.monitor.excel_link import MENU_ITEMS, menu_name  # noqa: PLC0415

    # Mã backend ghi vào step.guide (tutor_backend/ai/procedure.py, _CLICKS) cho mục trong menu thả xuống
    used = {"HideUnhideMenu", "ColumnsHide", "ColumnsUnhide", "RowsHide", "RowsUnhide", "ColumnWidth"}
    used |= {"RowHeight", "SheetColumnsInsert", "SheetRowsInsert", "SheetColumnsDelete", "SheetRowsDelete"}
    assert used <= MENU_ITEMS.keys()
    assert menu_name("Column Width...") == menu_name("column width") == "column width"
