"""Quy trình thao tác cấu trúc theo đề: ẩn/hiện, chèn, xóa, đổi kích thước dòng/cột.

Đề bài kiểu "Hiển thị cột E → chèn cột sau G → ẩn H → … → xóa các cột trống" có nhiều thao tác triệt tiêu
nhau (hiện rồi xóa, ẩn rồi hiện), so file đề với file đáp án không thấy. Module này làm lần lượt các thao tác
trên snapshot file đề để có **trạng thái mong đợi sau từng bước**: tự kiểm, chấm thử kịch bản theo từng trạng
thái đó (trường `operation` của bước, lược đồ kịch bản v1).

Làm giống Excel ở những điểm điều kiện kiểm cần: cột/dòng chèn mới mang định dạng của cột bên trái (dòng bên
trên), ô gộp cắt qua chỗ chèn thì nới ra, cột/dòng xóa thì ô gộp co lại. Công thức không được viết lại tham
chiếu (giá trị giữ nguyên, chỉ dời chỗ).
"""

import dataclasses
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from excel_core.address import (
    MAX_COL,
    MAX_ROW,
    CellRange,
    cell_address,
    column_index,
    column_letter,
    parse_cell,
    parse_range,
)
from excel_core.snapshot import CellSnapshot, RangeRead, SheetSnapshot, WorkbookSnapshot

ACTIONS = ("hide", "unhide", "insert", "delete", "resize")
AXES = ("cols", "rows")


class ProcedureError(ValueError):
    """Thao tác không làm được (sai tên cột/dòng, thiếu kích thước…)."""


@dataclass(frozen=True)
class Operation:
    """Một thao tác cấu trúc. Dòng/cột ghi theo bố cục **lúc làm thao tác** (như đề bài ghi)."""

    action: str  # hide | unhide | insert | delete | resize
    axis: str  # cols | rows
    lines: tuple[int, ...]  # chỉ số từ 1; insert: chèn TRƯỚC lines[0]
    count: int = 1  # insert: số dòng/cột chèn
    sizes: Mapping[int, float] = field(default_factory=dict)  # resize: kích thước sau thao tác

    def __post_init__(self) -> None:
        if self.action not in ACTIONS or self.axis not in AXES:
            raise ProcedureError(f"Thao tác không hỗ trợ: {self.action} {self.axis}")
        if not self.lines or min(self.lines) < 1:
            raise ProcedureError("Thao tác thiếu dòng/cột")
        if self.action == "insert" and (self.count < 1 or len(self.lines) != 1):
            raise ProcedureError("Chèn: một vị trí, số dòng/cột chèn từ 1")

    @property
    def is_col(self) -> bool:
        return self.axis == "cols"

    def name(self, line: int) -> str:
        return column_letter(line) if self.is_col else str(line)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Operation:
        """Từ trường `operation` của bước: {"action": "delete", "axis": "cols", "lines": ["D", "E", "H"]}."""
        axis = data.get("axis", "")

        def index(name: str) -> int:
            try:
                return column_index(name) if axis == "cols" else int(name)
            except ValueError as exc:
                raise ProcedureError(f"Tên dòng/cột không hợp lệ: {name!r}") from exc

        lines = tuple(sorted({index(str(n)) for n in data.get("lines", [])}))
        sizes = {index(str(k)): float(v) for k, v in (data.get("sizes") or {}).items()}
        return cls(data.get("action", ""), axis, lines, int(data.get("count") or 1), sizes)

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "action": self.action,
            "axis": self.axis,
            "lines": [self.name(n) for n in self.lines],
        }
        if self.action == "insert" and self.count != 1:
            data["count"] = self.count
        if self.sizes:
            data["sizes"] = {self.name(n): round(v, 2) for n, v in sorted(self.sizes.items())}
        return data

    def map_line(self, line: int) -> int | None:
        """Vị trí sau thao tác của dòng/cột đang ở `line`; bị xóa thì None."""
        if self.action == "insert":
            return line + self.count if line >= self.lines[0] else line
        if self.action == "delete":
            if line in self.lines:
                return None
            return line - sum(1 for d in self.lines if d < line)
        return line


def map_line(operations: Iterable[Operation], line: int) -> int | None:
    """Vị trí của dòng/cột `line` sau khi làm lần lượt các thao tác; bị xóa giữa chừng thì None."""
    current: int | None = line
    for op in operations:
        if current is None:
            return None
        current = op.map_line(current)
    return current


# ---------------------------------------------------------------- dời chỗ trên một trục
def _move_cell(op: Operation, address: str) -> str | None:
    col, row = parse_cell(address)
    if op.is_col:
        new = op.map_line(col)
        return None if new is None else cell_address(new, row)
    new = op.map_line(row)
    return None if new is None else cell_address(col, new)


def _move_range(op: Operation, rng: CellRange) -> CellRange | None:
    """Vùng sau thao tác: cắt qua chỗ chèn thì nới ra (như ô gộp trong Excel), có dòng/cột bị xóa thì co."""
    first, last = (rng.min_col, rng.max_col) if op.is_col else (rng.min_row, rng.max_row)
    if op.action == "insert":
        at = op.lines[0]
        new_first = first + op.count if first >= at else first
        new_last = last + op.count if last >= at else last
    else:
        kept = [n for line in range(first, last + 1) if (n := op.map_line(line)) is not None]
        if not kept:
            return None
        new_first, new_last = kept[0], kept[-1]
    if op.is_col:
        return CellRange(new_first, rng.min_row, min(new_last, MAX_COL), rng.max_row)
    return CellRange(rng.min_col, new_first, rng.max_col, min(new_last, MAX_ROW))


def _move_keys[V](
    op: Operation, items: Mapping[Any, V], key: Callable[[int], Any], index: Callable[[Any], int]
) -> dict[Any, V]:
    moved = {}
    for name, value in items.items():
        new = op.map_line(index(name))
        if new is not None:
            moved[key(new)] = value
    return moved


def _inserted_cells(op: Operation, sheet: SheetSnapshot, cells: dict[str, CellSnapshot]) -> None:
    """Cột (dòng) chèn mới mang định dạng của cột bên trái (dòng bên trên), không có giá trị — như Excel."""
    at = op.lines[0]
    if at == 1:
        return
    for address, cell in sheet.cells.items():
        col, row = parse_cell(address)
        if (col if op.is_col else row) != at - 1:
            continue
        styled = dataclasses.replace(cell, value=None, value_kind="empty", formula=None, formula_r1c1=None)
        if styled == CellSnapshot():
            continue
        for offset in range(op.count):
            target = cell_address(at + offset, row) if op.is_col else cell_address(col, at + offset)
            cells[target] = styled


def apply_operation(sheet: SheetSnapshot, op: Operation) -> SheetSnapshot:
    """Trạng thái trang tính sau một thao tác."""
    letter = column_letter if op.is_col else int

    def index(name: Any) -> int:
        return column_index(name) if op.is_col else int(name)

    hidden = set(sheet.hidden_cols if op.is_col else sheet.hidden_rows)
    sizes = dict(sheet.col_widths if op.is_col else sheet.row_heights)
    if op.action in ("hide", "unhide"):
        names = {letter(n) for n in op.lines}
        if op.action == "hide":
            hidden |= names
            sizes.update(dict.fromkeys(names & sizes.keys(), 0.0))
        else:
            hidden -= names
            # Dòng/cột ẩn được đọc ra kích thước 0: hiện lại thì chưa biết kích thước thật, bỏ khỏi snapshot
            for name in names:
                if sizes.get(name) == 0.0:
                    del sizes[name]
        return _with_lines(sheet, op, hidden, sizes)
    if op.action == "resize":
        missing = [op.name(n) for n in op.lines if n not in op.sizes]
        if missing:
            raise ProcedureError(f"Thiếu kích thước mong đợi cho {', '.join(missing)}")
        sizes.update({letter(n): op.sizes[n] for n in op.lines if letter(n) not in hidden})
        return _with_lines(sheet, op, hidden, sizes)

    cells: dict[str, CellSnapshot] = {}
    for address, cell in sheet.cells.items():
        moved = _move_cell(op, address)
        if moved is not None:
            cells[moved] = cell
    if op.action == "insert":
        _inserted_cells(op, sheet, cells)
    merged = []
    for text in sheet.merged:
        rng = _move_range(op, parse_range(text))
        if rng is not None and rng.size > 1:
            merged.append(str(rng))
    reads = []
    for read in sheet.read_ranges:
        rng = _move_range(op, parse_range(read.range))
        if rng is not None:
            reads.append(RangeRead(str(rng), read.groups))
    moved_hidden = set(_move_keys(op, dict.fromkeys(hidden, True), letter, index))
    moved_sizes = _move_keys(op, sizes, letter, index)
    if op.action == "insert" and op.lines[0] > 1:
        left = letter(op.lines[0] - 1)
        for offset in range(op.count):
            if left in sizes and left not in hidden:
                moved_sizes[letter(op.lines[0] + offset)] = sizes[left]
    shifted = dataclasses.replace(sheet, cells=cells, merged=tuple(sorted(merged)), read_ranges=tuple(reads))
    return _with_lines(shifted, op, moved_hidden, moved_sizes)


def _with_lines(
    sheet: SheetSnapshot, op: Operation, hidden: set[Any], sizes: dict[Any, float]
) -> SheetSnapshot:
    if op.is_col:
        return dataclasses.replace(sheet, hidden_cols=frozenset(hidden), col_widths=sizes)
    return dataclasses.replace(sheet, hidden_rows=frozenset(hidden), row_heights=sizes)


def check_operation(sheet: SheetSnapshot, op: Operation) -> None:
    """Thao tác vô nghĩa trên trạng thái hiện tại thì báo (AI đọc sai đề hay sai thứ tự)."""
    hidden = sheet.hidden_cols if op.is_col else sheet.hidden_rows
    names = [op.name(n) for n in op.lines]
    key = (lambda n: n) if op.is_col else int
    if op.action == "unhide" and not any(key(n) in hidden for n in names):
        raise ProcedureError(
            f"{'Cột' if op.is_col else 'Dòng'} {', '.join(names)} đang không ẩn, không cần hiện"
        )
    if op.action == "hide" and all(key(n) in hidden for n in names):
        raise ProcedureError(f"{'Cột' if op.is_col else 'Dòng'} {', '.join(names)} đã ẩn sẵn")


def with_sheet(workbook: WorkbookSnapshot, sheet: SheetSnapshot) -> WorkbookSnapshot:
    return dataclasses.replace(workbook, sheets={**workbook.sheets, sheet.name: sheet})


def simulate(
    starter: WorkbookSnapshot, sheet: str, operations: Sequence[Operation], strict: bool = True
) -> list[WorkbookSnapshot]:
    """Trạng thái workbook sau từng thao tác (phần tử i: sau thao tác i). `strict`: báo thao tác vô nghĩa."""
    states, current = [], starter
    for number, op in enumerate(operations, start=1):
        page = current.sheet(sheet)
        try:
            if strict:
                check_operation(page, op)
            current = with_sheet(current, apply_operation(page, op))
        except ProcedureError as exc:
            raise ProcedureError(f"Thao tác {number}: {exc}") from exc
        states.append(current)
    return states


def resolve_sizes(operations: Sequence[Operation], solution: SheetSnapshot) -> list[Operation]:
    """Điền kích thước còn thiếu của thao tác đổi kích thước theo đáp án: dòng/cột đó (dời qua các thao tác
    sau) có kích thước bao nhiêu trong đáp án. Kích thước đề ghi rõ (đã có trong `sizes`) giữ nguyên."""
    resolved = []
    for number, op in enumerate(operations):
        if op.action != "resize":
            resolved.append(op)
            continue
        sizes = dict(op.sizes)
        source = solution.col_widths if op.is_col else solution.row_heights
        for line in op.lines:
            if line in sizes:
                continue
            final = map_line(operations[number + 1 :], line)
            key = None if final is None else (column_letter(final) if op.is_col else final)
            if key is None or key not in source:
                raise ProcedureError(
                    f"Thao tác {number + 1}: không biết kích thước mong đợi của {op.name(line)} "
                    "(dòng/cột này không còn trong đáp án): đề phải ghi rõ số đo"
                )
            sizes[line] = source[key]
        resolved.append(dataclasses.replace(op, sizes=sizes))
    return resolved
