"""So sánh file đề với file kết quả mẫu (T4.3).

Kết quả là danh sách thay đổi có cấu trúc, các ô cùng loại thay đổi được gom thành vùng chữ nhật. Dùng cho:
tác tử sinh kịch bản (T5.5, "xương sống" của kịch bản, kiến trúc A2) và độ phủ diff khi tự kiểm (T4.5).
"""

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import openpyxl

from excel_core.address import (
    AddressError,
    CellRange,
    cell_address,
    column_index,
    column_letter,
    group_into_ranges,
    parse_range,
    split_sheet_reference,
)
from excel_core.diff.alignment import IDENTITY, AxisMap, align_sheets
from excel_core.diff.describe import (
    describe_alignment,
    describe_border,
    describe_font,
    describe_number_format,
    describe_value,
    object_changes,
)
from excel_core.formula import FormulaError, parse_formula
from excel_core.readers import read_workbook, used_range
from excel_core.snapshot import (
    CELL_GROUPS,
    EMPTY_CELL,
    SHEET_GROUPS,
    CellSnapshot,
    PropertyGroup,
    RangeRequest,
    ReadRequest,
    SheetRequest,
    SheetSnapshot,
    WorkbookSnapshot,
)

SIZE_TOLERANCE = 0.5  # pt / ký tự: dưới ngưỡng này coi như không đổi kích thước


class ChangeKind(StrEnum):
    VALUE = "value"
    FORMULA = "formula"
    NUMBER_FORMAT = "number_format"
    FONT = "font"
    FILL = "fill"
    BORDER = "border"
    ALIGNMENT = "alignment"
    MERGED = "merged"
    ROW_HIDDEN = "row_hidden"
    COL_HIDDEN = "col_hidden"
    ROW_HEIGHT = "row_height"
    COL_WIDTH = "col_width"
    AUTOFILTER = "autofilter"
    PAGE_SETUP = "page_setup"
    CHART = "chart"
    SHEET_ADDED = "sheet_added"
    SHEET_REMOVED = "sheet_removed"
    # Chèn/xóa cột, dòng: vùng là dải cột "D:E" / dòng "5:7"; xóa tính theo file đề, chèn theo file đáp án.
    # Các thay đổi khác của trang tính đó tính theo vị trí trong file đáp án.
    COL_INSERTED = "col_inserted"
    COL_DELETED = "col_deleted"
    ROW_INSERTED = "row_inserted"
    ROW_DELETED = "row_deleted"


@dataclass(frozen=True)
class Change:
    """Một thay đổi từ file đề sang file đáp án."""

    sheet: str
    kind: ChangeKind
    range: str | None  # vùng ô, dải dòng "5:7", dải cột "C:D"; None nếu thay đổi theo sheet
    before: str
    after: str

    def __str__(self) -> str:
        where = f" {self.range}" if self.range else ""
        return f"[{self.sheet}]{where} {self.kind.value}: {self.before} → {self.after}"


@dataclass(frozen=True)
class WorkbookDiff:
    changes: tuple[Change, ...]

    def __iter__(self) -> Iterator[Change]:
        return iter(self.changes)

    def __len__(self) -> int:
        return len(self.changes)

    def of_kind(self, *kinds: ChangeKind) -> tuple[Change, ...]:
        return tuple(c for c in self.changes if c.kind in kinds)

    def cell_changes(self) -> tuple[Change, ...]:
        """Thay đổi trên vùng ô (có địa chỉ A1), dùng để tính độ phủ của kịch bản."""
        return tuple(c for c in self.changes if c.kind in CELL_KINDS and c.range)

    def to_text(self) -> str:
        """Dạng chữ gọn, mỗi thay đổi một dòng (đưa vào prompt cho LLM)."""
        return "\n".join(str(c) for c in self.changes)


LAYOUT_KINDS = frozenset(
    {ChangeKind.COL_INSERTED, ChangeKind.COL_DELETED, ChangeKind.ROW_INSERTED, ChangeKind.ROW_DELETED}
)

CELL_KINDS = frozenset(
    {
        ChangeKind.VALUE,
        ChangeKind.FORMULA,
        ChangeKind.NUMBER_FORMAT,
        ChangeKind.FONT,
        ChangeKind.FILL,
        ChangeKind.BORDER,
        ChangeKind.ALIGNMENT,
        ChangeKind.MERGED,
    }
)


def _value_change(before: CellSnapshot, after: CellSnapshot) -> tuple[str, str, str] | None:
    """(chữ trước, chữ sau, khóa gom nhóm) cho thay đổi giá trị/công thức; None nếu không đổi."""
    if before.formula or after.formula:
        same_r1c1 = before.formula_r1c1 is not None and before.formula_r1c1 == after.formula_r1c1
        if before.formula == after.formula or same_r1c1:
            # Cùng công thức (cùng R1C1: công thức chỉ dời theo cột/dòng bị chèn, xóa): giá trị khác là hệ quả
            return None
        old = before.formula or describe_value(before)
        new = f"{after.formula} (R1C1 {after.formula_r1c1})" if after.formula else describe_value(after)
        key = f"formula|{after.formula_r1c1 or after.formula}|{before.formula is None}"
        return old, new, key
    if before.value == after.value and before.value_kind == after.value_kind:
        return None
    return describe_value(before), describe_value(after), f"value|{before.value_kind}|{after.value_kind}"


def _cell_field_changes(
    before: CellSnapshot, after: CellSnapshot
) -> Iterator[tuple[ChangeKind, str, str, str]]:
    """Mọi thay đổi của một ô: (loại, chữ trước, chữ sau, khóa gom nhóm). Trường chưa đọc thì bỏ qua."""
    value = _value_change(before, after)
    if value:
        kind = ChangeKind.FORMULA if value[2].startswith("formula") else ChangeKind.VALUE
        yield kind, value[0], value[1], value[2]
    pairs: list[tuple[ChangeKind, Any, Any, Callable[[Any], str]]] = [
        (ChangeKind.NUMBER_FORMAT, before.number_format, after.number_format, describe_number_format),
        (ChangeKind.FONT, before.font, after.font, describe_font),
        (ChangeKind.FILL, before.fill, after.fill, lambda f: f.color or "không tô"),
        (ChangeKind.BORDER, before.border, after.border, describe_border),
        (ChangeKind.ALIGNMENT, before.alignment, after.alignment, describe_alignment),
    ]
    for kind, old, new, describe in pairs:
        if old is None or new is None or old == new:
            continue
        yield kind, describe(old), describe(new), f"{kind}|{old!r}|{new!r}"


def _is_auto_format(before: CellSnapshot, after: SheetSnapshot, address: str) -> bool:
    """Định dạng số Excel tự áp khi gõ công thức vào ô General: lấy theo ô được tham chiếu đầu tiên.

    Không phải thao tác của người làm đáp án nên không tính là thay đổi (T2.6: b22 thừa bước "định dạng").
    """
    cell = after.cell(address)
    if cell.formula is None or before.formula is not None or cell.number_format is None:
        return False
    if before.number_format is not None and before.number_format.category != "general":
        return False
    try:
        references = parse_formula(cell.formula).references
    except FormulaError:
        return False
    if not references:
        return False
    sheet, first = split_sheet_reference(references[0])
    if sheet not in (None, after.name):
        return False
    try:
        source = after.cell(parse_range(first).top_left)
    except AddressError:
        return False
    return source.number_format is not None and source.number_format.code == cell.number_format.code


def _compared_addresses(before: SheetSnapshot, after: SheetSnapshot) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for read in (*before.read_ranges, *after.read_ranges):
        rng = parse_range(read.range)
        cells.update((col, row) for row in rng.rows() for col in rng.cols())
    return cells


@dataclass(frozen=True)
class SheetLayout:
    """Khớp cột, dòng của một trang tính (IDENTITY: bố cục không đổi, so theo địa chỉ)."""

    cols: AxisMap = IDENTITY
    rows: AxisMap = IDENTITY

    def starter_cell(self, before: SheetSnapshot, col: int, row: int) -> CellSnapshot:
        """Ô của file đề ứng với ô (col, row) của đáp án; cột/dòng chèn mới thì là ô trống."""
        source_col, source_row = self.cols.starter(col), self.rows.starter(row)
        if source_col is None or source_row is None:
            return EMPTY_CELL
        return before.cell(cell_address(source_col, source_row))


def sheet_layout(before: SheetSnapshot, after: SheetSnapshot) -> SheetLayout:
    """Khớp cột, dòng của file đề với file đáp án trên vùng đã đọc ở cả hai bên (xem alignment.py)."""
    cells = _compared_addresses(before, after)
    if not cells:
        return SheetLayout()
    cols = range(min(c for c, _ in cells), max(c for c, _ in cells) + 1)
    rows = range(min(r for _, r in cells), max(r for _, r in cells) + 1)
    col_map, row_map = align_sheets(before, after, cols, rows)
    return SheetLayout(col_map, row_map)


def _cell_diff(
    name: str, before: SheetSnapshot, after: SheetSnapshot, layout: SheetLayout
) -> list[tuple[CellRange, Change]]:
    # Khóa gom nhóm → mô tả của từng ô; vùng gom được thì lấy mô tả của ô góc trên trái
    buckets: dict[tuple[ChangeKind, str], dict[tuple[int, int], tuple[str, str]]] = {}
    for col, row in _compared_addresses(before, after):
        address = cell_address(col, row)
        source = layout.starter_cell(before, col, row)
        for kind, old, new, key in _cell_field_changes(source, after.cell(address)):
            if kind == ChangeKind.NUMBER_FORMAT and _is_auto_format(source, after, address):
                continue
            buckets.setdefault((kind, key), {})[(col, row)] = (old, new)
    found = []
    for (kind, _), described in buckets.items():
        for rng in group_into_ranges(described):
            old, new = described[(rng.min_col, rng.min_row)]
            found.append((rng, Change(name, kind, str(rng), old, new)))
    order = list(ChangeKind)
    return sorted(found, key=lambda item: (item[0].min_row, item[0].min_col, order.index(item[1].kind)))


def _line_ranges(items: set[int]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for item in sorted(items):
        if spans and spans[-1][1] == item - 1:
            spans[-1] = (spans[-1][0], item)
        else:
            spans.append((item, item))
    return spans


def _col_span(first: int, last: int) -> str:
    return f"{column_letter(first)}:{column_letter(last)}"


def _moved_merges(before: SheetSnapshot, layout: SheetLayout) -> set[str]:
    """Ô gộp của file đề, đổi sang vị trí trong đáp án; ô gộp nằm trên cột/dòng bị xóa thì bỏ."""
    moved = set()
    for merged in before.merged:
        rng = parse_range(merged)
        c1, c2 = layout.cols.solution(rng.min_col), layout.cols.solution(rng.max_col)
        r1, r2 = layout.rows.solution(rng.min_row), layout.rows.solution(rng.max_row)
        if None not in (c1, c2, r1, r2):
            moved.add(str(CellRange(c1, r1, c2, r2)))  # type: ignore[arg-type]
    return moved


def _moved_lines[K](items: Mapping[K, float] | frozenset[K], axis: AxisMap, is_col: bool) -> dict[K, float]:
    """Thuộc tính theo cột/dòng của file đề (độ rộng, ẩn), đổi sang vị trí trong đáp án."""
    moved: dict[K, float] = {}
    values = items if isinstance(items, Mapping) else dict.fromkeys(items, 1.0)
    for key, value in values.items():
        index = column_index(str(key)) if is_col else int(key)  # type: ignore[call-overload]
        target = axis.solution(index)
        if target is not None:
            moved[column_letter(target) if is_col else target] = value  # type: ignore[index]
    return moved


def _layout_changes(name: str, layout: SheetLayout) -> list[Change]:
    changes = []
    for kind, indices, label, is_col in (
        (ChangeKind.COL_DELETED, layout.cols.deleted, "xóa cột", True),
        (ChangeKind.COL_INSERTED, layout.cols.inserted, "chèn cột", True),
        (ChangeKind.ROW_DELETED, layout.rows.deleted, "xóa dòng", False),
        (ChangeKind.ROW_INSERTED, layout.rows.inserted, "chèn dòng", False),
    ):
        for first, last in _line_ranges(set(indices)):
            span = _col_span(first, last) if is_col else f"{first}:{last}"
            changes.append(Change(name, kind, span, "", label))
    return changes


def _structure_diff(
    name: str, before: SheetSnapshot, after: SheetSnapshot, layout: SheetLayout
) -> list[Change]:
    changes = _layout_changes(name, layout)
    before_merged = _moved_merges(before, layout)
    for merged in sorted(set(after.merged) - before_merged):
        changes.append(Change(name, ChangeKind.MERGED, merged, "không gộp", "gộp ô"))
    for merged in sorted(before_merged - set(after.merged)):
        changes.append(Change(name, ChangeKind.MERGED, merged, "gộp ô", "bỏ gộp"))
    hidden_rows = set(_moved_lines(before.hidden_rows, layout.rows, is_col=False))
    for shown, label in ((after.hidden_rows - hidden_rows, "ẩn"), (hidden_rows - after.hidden_rows, "hiện")):
        for first, last in _line_ranges(set(shown)):
            changes.append(Change(name, ChangeKind.ROW_HIDDEN, f"{first}:{last}", "", label))
    hidden_cols = set(_moved_lines(before.hidden_cols, layout.cols, is_col=True))
    cols_hidden = {column_index(c) for c in after.hidden_cols - hidden_cols}
    cols_shown = {column_index(c) for c in hidden_cols - after.hidden_cols}
    for cols, label in ((cols_hidden, "ẩn"), (cols_shown, "hiện")):
        for first, last in _line_ranges(cols):
            changes.append(Change(name, ChangeKind.COL_HIDDEN, _col_span(first, last), "", label))
    row_heights = _moved_lines(before.row_heights, layout.rows, is_col=False)
    col_widths = _moved_lines(before.col_widths, layout.cols, is_col=True)
    changes += _size_diff(name, ChangeKind.ROW_HEIGHT, row_heights, after.row_heights, after.hidden_rows)
    changes += _size_diff(name, ChangeKind.COL_WIDTH, col_widths, after.col_widths, after.hidden_cols)
    return changes


def _size_diff(
    name: str,
    kind: ChangeKind,
    before: Mapping[Any, float],
    after: Mapping[Any, float],
    hidden: frozenset[Any],
) -> list[Change]:
    changes = []
    for key in sorted(set(before) & set(after), key=lambda k: (len(str(k)), str(k))):
        if key in hidden or abs(before[key] - after[key]) < SIZE_TOLERANCE:
            continue
        span = f"{key}:{key}"
        changes.append(Change(name, kind, span, f"{before[key]:g}", f"{after[key]:g}"))
    return changes


def _sheet_object_diff(name: str, before: SheetSnapshot, after: SheetSnapshot) -> list[Change]:
    changes = []
    compared = (
        (ChangeKind.AUTOFILTER, PropertyGroup.FILTER, before.autofilter, after.autofilter),
        (ChangeKind.PAGE_SETUP, PropertyGroup.PAGE_SETUP, before.page_setup, after.page_setup),
        (ChangeKind.CHART, PropertyGroup.CHARTS, before.charts, after.charts),
    )
    for kind, group, old_object, new_object in compared:
        if group not in before.sheet_groups or group not in after.sheet_groups:
            continue
        for old, new in object_changes(old_object, new_object):
            changes.append(Change(name, kind, None, old, new))
    return changes


def diff_workbooks(starter: WorkbookSnapshot, solution: WorkbookSnapshot) -> WorkbookDiff:
    """So sánh hai snapshot. Chỉ so những gì đã đọc ở cả hai bên."""
    changes: list[Change] = []
    for name in solution.sheet_names:
        if name not in starter.sheet_names:
            changes.append(Change(name, ChangeKind.SHEET_ADDED, None, "", "thêm sheet"))
            continue
        if name not in starter.sheets or name not in solution.sheets:
            continue
        before, after = starter.sheets[name], solution.sheets[name]
        layout = sheet_layout(before, after)
        changes += [change for _, change in _cell_diff(name, before, after, layout)]
        changes += _structure_diff(name, before, after, layout)
        changes += _sheet_object_diff(name, before, after)
    for name in starter.sheet_names:
        if name not in solution.sheet_names:
            changes.append(Change(name, ChangeKind.SHEET_REMOVED, None, "có sheet", "xóa sheet"))
    return WorkbookDiff(tuple(changes))


def pair_request(starter_path: Path | str, solution_path: Path | str) -> ReadRequest:
    """Yêu cầu đọc chung cho hai file: vùng đang dùng gộp của từng sheet có ở cả hai."""
    starter = openpyxl.load_workbook(starter_path)
    solution = openpyxl.load_workbook(solution_path)
    ranges, sheets = [], []
    for ws in solution.worksheets:
        rng = parse_range(used_range(ws))
        if ws.title in starter.sheetnames:
            rng = rng.union(parse_range(used_range(starter[ws.title])))
        ranges.append(RangeRequest(ws.title, str(rng), CELL_GROUPS))
        sheets.append(SheetRequest(ws.title, SHEET_GROUPS))
    return ReadRequest(tuple(ranges), tuple(sheets))


def diff_files(starter_path: Path | str, solution_path: Path | str) -> WorkbookDiff:
    """Đọc file đề và file đáp án với cùng một yêu cầu đọc rồi so sánh."""
    request = pair_request(starter_path, solution_path)
    return diff_workbooks(read_workbook(starter_path, request), read_workbook(solution_path, request))
