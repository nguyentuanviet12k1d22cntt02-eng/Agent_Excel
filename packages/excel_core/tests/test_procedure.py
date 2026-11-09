"""Làm lần lượt thao tác cấu trúc trên snapshot (excel_core.procedure). Đối chiếu Excel thật trên bài 06: giá
trị, ô gộp, cột ẩn, độ rộng sau từng bước khớp hết; ở đây kiểm các quy tắc trên trang tính nhỏ."""

from datetime import datetime

import pytest

from excel_core.procedure import Operation, ProcedureError, apply_operation, map_line, resolve_sizes, simulate
from excel_core.snapshot import (
    CELL_GROUPS,
    BorderInfo,
    CellSnapshot,
    FillInfo,
    RangeRead,
    SheetSnapshot,
    WorkbookSnapshot,
)

FILL = FillInfo("#FFFF00")


def text(value: str, fill: FillInfo | None = None) -> CellSnapshot:
    return CellSnapshot(value=value, value_kind="text", fill=fill)


def sheet() -> SheetSnapshot:
    """B: Mã, C: Tên (nền vàng), D trống, E trống đang ẩn, F: Số lượng; tiêu đề gộp B2:F2."""
    return SheetSnapshot(
        name="S",
        cells={
            "B2": text("DANH SÁCH"),
            "B4": text("Mã"),
            "C4": text("Tên", FILL),
            "F4": text("Số lượng"),
            "C5": CellSnapshot(border=BorderInfo(bottom="thin")),
        },
        read_ranges=(RangeRead("A1:F6", CELL_GROUPS),),
        merged=("B2:F2",),
        hidden_cols=frozenset({"E"}),
        col_widths={"B": 6.0, "C": 20.0, "D": 9.0, "E": 0.0, "F": 12.0},
    )


def op(data: dict) -> Operation:
    return Operation.from_json(data)


def test_operation_json_round_trip_and_line_mapping():
    delete = op({"action": "delete", "axis": "cols", "lines": ["H", "D", "E"]})
    assert delete.lines == (4, 5, 8) and delete.to_json()["lines"] == ["D", "E", "H"]
    assert [delete.map_line(n) for n in (3, 4, 6, 8, 9)] == [3, None, 4, None, 6]
    insert = op({"action": "insert", "axis": "rows", "lines": ["5"], "count": 2})
    assert insert.to_json() == {"action": "insert", "axis": "rows", "lines": ["5"], "count": 2}
    assert map_line([insert, op({"action": "delete", "axis": "rows", "lines": ["7"]})], 5) is None
    with pytest.raises(ProcedureError):
        op({"action": "insert", "axis": "cols", "lines": ["C", "D"]})
    with pytest.raises(ProcedureError):
        op({"action": "move", "axis": "cols", "lines": ["C"]})


def test_insert_shifts_cells_widens_merges_and_copies_left_format():
    after = apply_operation(sheet(), op({"action": "insert", "axis": "cols", "lines": ["D"]}))

    assert after.cell("G4").value == "Số lượng" and after.cell("C4").value == "Tên"
    assert after.merged == ("B2:G2",)  # ô gộp cắt qua chỗ chèn thì nới ra
    assert after.cell("D4") == CellSnapshot(fill=FILL)  # định dạng của cột bên trái, không có giá trị
    assert after.cell("D5").border == BorderInfo(bottom="thin")
    assert after.hidden_cols == {"F"} and after.col_widths["D"] == 20.0 and after.col_widths["G"] == 12.0
    assert after.read_ranges[0].range == "A1:G6"


def test_delete_non_adjacent_columns_shrinks_merges():
    after = apply_operation(sheet(), op({"action": "delete", "axis": "cols", "lines": ["C", "E"]}))

    assert after.cell("B4").value == "Mã" and after.cell("D4").value == "Số lượng"
    assert after.merged == ("B2:D2",) and after.hidden_cols == frozenset()
    assert after.col_widths == {"B": 6.0, "C": 9.0, "D": 12.0}
    one_cell = apply_operation(after, op({"action": "delete", "axis": "cols", "lines": ["C", "D"]}))
    assert one_cell.merged == ()  # co còn một ô thì không còn là ô gộp


def test_hide_unhide_and_resize():
    shown = apply_operation(sheet(), op({"action": "unhide", "axis": "cols", "lines": ["E"]}))
    # Cột ẩn đọc ra độ rộng 0: hiện lại thì chưa biết độ rộng thật, bỏ khỏi snapshot (diff không so)
    assert "E" not in shown.hidden_cols and "E" not in shown.col_widths
    hidden = apply_operation(shown, op({"action": "hide", "axis": "cols", "lines": ["C"]}))
    assert hidden.hidden_cols == {"C"} and hidden.col_widths["C"] == 0.0
    resized = apply_operation(
        sheet(), op({"action": "resize", "axis": "cols", "lines": ["F"], "sizes": {"F": 15}})
    )
    assert resized.col_widths["F"] == 15.0
    with pytest.raises(ProcedureError, match="Thiếu kích thước"):
        apply_operation(sheet(), op({"action": "resize", "axis": "cols", "lines": ["F"]}))


def workbook(page: SheetSnapshot) -> WorkbookSnapshot:
    return WorkbookSnapshot("openpyxl", datetime(2026, 1, 1), None, ("S",), "S", {"S": page})


def test_simulate_reports_meaningless_steps():
    starter = workbook(sheet())
    states = simulate(
        starter,
        "S",
        [
            op({"action": "unhide", "axis": "cols", "lines": ["E"]}),
            op({"action": "delete", "axis": "cols", "lines": ["D", "E"]}),
        ],
    )
    assert states[-1].sheet("S").cell("D4").value == "Số lượng"
    with pytest.raises(ProcedureError, match="Thao tác 1: Cột D đang không ẩn"):
        simulate(starter, "S", [op({"action": "unhide", "axis": "cols", "lines": ["D"]})])
    with pytest.raises(ProcedureError, match="đã ẩn sẵn"):
        simulate(starter, "S", [op({"action": "hide", "axis": "cols", "lines": ["E"]})])


def test_resize_takes_the_size_the_column_ends_with_in_the_solution():
    operations = [
        op({"action": "insert", "axis": "cols", "lines": ["C"]}),
        op({"action": "resize", "axis": "cols", "lines": ["D"]}),  # cột Tên (đang ở D) theo mẫu
        op({"action": "delete", "axis": "cols", "lines": ["C"]}),
    ]
    solution = SheetSnapshot(name="S", col_widths={"C": 25.5})
    assert resolve_sizes(operations, solution)[1].sizes == {4: 25.5}
    gone = [op({"action": "resize", "axis": "cols", "lines": ["C"]}), operations[2]]
    with pytest.raises(ProcedureError, match="đề phải ghi rõ số đo"):
        resolve_sizes(gone, solution)
    given = [op({"action": "resize", "axis": "cols", "lines": ["C"], "sizes": {"C": 8}}), operations[2]]
    assert resolve_sizes(given, solution)[0].sizes == {3: 8.0}
