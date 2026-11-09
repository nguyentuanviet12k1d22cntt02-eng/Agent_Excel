"""Chèn/xóa cột, dòng: so theo cột/dòng tương ứng, không theo địa chỉ (bài 06 thao tác với cột)."""

from datetime import datetime

from excel_core.diff import ChangeKind, diff_workbooks
from excel_core.diff.alignment import IDENTITY, align_axis
from excel_core.snapshot import (
    CELL_GROUPS,
    SHEET_GROUPS,
    CellSnapshot,
    FontInfo,
    RangeRead,
    SheetSnapshot,
    WorkbookSnapshot,
)

S = "Bài tập"
BOLD = FontInfo(name="Calibri", size=11, bold=True, italic=False, underline=False, color="#000000")


def text(value: str, bold: bool = False) -> CellSnapshot:
    return CellSnapshot(value=value, value_kind="text", font=BOLD if bold else None)


def number(value: float) -> CellSnapshot:
    return CellSnapshot(value=value, value_kind="number")


def sheet(cells: dict[str, CellSnapshot], **extra) -> SheetSnapshot:
    return SheetSnapshot(
        name=S,
        cells=cells,
        read_ranges=(RangeRead("A1:J12", CELL_GROUPS),),
        sheet_groups=SHEET_GROUPS,
        **extra,
    )


def book(s: SheetSnapshot) -> WorkbookSnapshot:
    return WorkbookSnapshot("openpyxl", datetime(2026, 11, 9), None, (S,), None, {S: s})


def table(columns: dict[str, list[CellSnapshot]], first_row: int = 2) -> dict[str, CellSnapshot]:
    return {f"{col}{first_row + i}": cell for col, cells in columns.items() for i, cell in enumerate(cells)}


NAMES = [text("Họ tên", bold=True), text("An"), text("Bình"), text("Chi")]
SCORES = [text("Điểm", bold=True), number(7), number(8), number(9)]
RANKS = [text("Xếp loại", bold=True), text("Khá"), text("Giỏi"), text("Giỏi")]


def test_deleting_empty_columns_is_one_change_not_many_format_changes():
    # Đề: B=Họ tên, C, D trống (D đang ẩn), E=Điểm, F=Xếp loại; đáp án: xóa C:D, mọi thứ dời sang trái
    before = sheet(
        {**table({"B": NAMES, "E": SCORES, "F": RANKS}), "A1": text("BẢNG ĐIỂM", bold=True)},
        merged=("A1:F1",),
        hidden_cols=frozenset({"D"}),
        col_widths={"E": 12.0, "F": 15.0},
    )
    after = sheet(
        {**table({"B": NAMES, "C": SCORES, "D": RANKS}), "A1": text("BẢNG ĐIỂM", bold=True)},
        merged=("A1:D1",),
        col_widths={"C": 12.0, "D": 20.0},
    )

    changes = [(c.kind, c.range) for c in diff_workbooks(book(before), book(after))]

    # Ô gộp tiêu đề co theo, cột ẩn bị xóa, độ rộng dời theo cột: không phải thay đổi. Chỉ cột D đổi độ rộng.
    assert changes == [(ChangeKind.COL_DELETED, "C:D"), (ChangeKind.COL_WIDTH, "D:D")]


def test_inserted_row_in_table():
    before = sheet(table({"B": NAMES, "C": SCORES}))
    after = sheet(
        {
            **table({"B": NAMES[:2], "C": SCORES[:2]}),
            **table({"B": NAMES[2:], "C": SCORES[2:]}, first_row=5),
        }
    )

    changes = [(c.kind, c.range) for c in diff_workbooks(book(before), book(after))]

    assert changes == [(ChangeKind.ROW_INSERTED, "4:4")]


def test_reordered_rows_are_not_insert_delete():
    # Sắp xếp: cùng các dòng, khác thứ tự (b16) — phải để bước "sắp xếp" nhận ra, không coi là chèn/xóa dòng
    rows = [("H", 0), ("A", 9), ("B", 5), ("C", 1)]
    before = [(name,) for name, _ in rows]
    after = [before[0], before[3], before[2], before[1]]
    assert align_axis(before, after) is IDENTITY


def test_new_value_equal_to_existing_one_is_not_a_shift():
    # Ô mới =SUM(...) ra đúng bằng giá trị một ô khác: không phải dịch cột
    before = [(None,), (None,), (25000,), (None,), (None,), (None,)]
    after = [(None,), (None,), (25000,), (None,), (None,), (25000,)]
    assert align_axis(before, after) is IDENTITY
