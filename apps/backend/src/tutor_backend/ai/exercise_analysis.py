"""Phân tích bài tập trước khi gọi AI (T5.5): diff đề → đáp án, nhãn cột, vùng nguồn, vùng giữ nguyên.

Kết luận T2.6 áp dụng ở đây:
- Diff là "xương sống" của kịch bản (kiến trúc A2); mỗi thay đổi có mã c1, c2… để AI xếp vào bước.
- Đưa **tiêu đề cột thật** cho từng vùng; không đưa địa chỉ ô và số liệu (AI hay chép sai, bịa số).
- Vùng "giữ nguyên" (dữ liệu nguồn, công thức có sẵn) sinh điều kiện toàn bài theo luật, không trông vào AI.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from excel_core.address import (
    CellRange,
    cell_address,
    column_index,
    column_letter,
    group_into_ranges,
    parse_cell,
    parse_range,
)
from excel_core.checks import codes_for
from excel_core.checks.sorted_by import sort_key
from excel_core.diff import (
    LAYOUT_KINDS,
    Change,
    ChangeKind,
    SheetLayout,
    diff_workbooks,
    pair_request,
    sheet_layout,
)
from excel_core.formula import FormulaError, parse_formula
from excel_core.readers import read_workbook
from excel_core.readers.shapes import ShapeText, shape_texts
from excel_core.snapshot import CellValue, SheetSnapshot, WorkbookSnapshot
from tutor_backend.ai.check_synthesis import (
    cell_change_checks,
    formula_functions,
    line_check,
    sheet_object_checks,
)

type Check = dict[str, Any]

HEADER_SEARCH_ROWS = 8  # tìm tiêu đề cột trong ngần này dòng phía trên vùng
MAX_LABEL_LENGTH = 40
MAX_LABEL_NAMES = 4  # số tiêu đề cột nêu trong nhãn của một bảng
MAX_REGION_CELLS = 2000  # vùng dữ liệu liền khối lớn hơn thì không mở rộng
MIN_INSTRUCTION_LENGTH = 15
MAX_INSTRUCTIONS = 30
# Loại thay đổi tách theo từng cột: nhập liệu, định dạng số, căn lề thường làm theo cột (b09)
SPLIT_BY_COLUMN = frozenset({ChangeKind.VALUE, ChangeKind.NUMBER_FORMAT, ChangeKind.ALIGNMENT})
KIND_NAMES = {
    "value": "nhập dữ liệu",
    "formula": "nhập công thức",
    "number_format": "định dạng số",
    "alignment": "căn lề",
    "font": "phông chữ",
    "fill": "tô màu nền",
    "border": "kẻ viền",
    "merged": "gộp ô",
    "row_hidden": "ẩn/hiện dòng",
    "col_hidden": "ẩn/hiện cột",
    "row_height": "chiều cao dòng",
    "col_width": "độ rộng cột",
    "autofilter": "lọc dữ liệu",
    "page_setup": "thiết lập trang in",
    "chart": "biểu đồ",
    "sheet_added": "thêm trang tính",
    "col_inserted": "chèn cột",
    "col_deleted": "xóa cột",
    "row_inserted": "chèn dòng",
    "row_deleted": "xóa dòng",
    "sort": "sắp xếp bảng",
}


@dataclass(frozen=True)
class ChangeItem:
    id: str  # "c1", "c2"… để AI xếp vào bước
    sheet: str
    kind: str
    range: str | None  # vùng ô; None nếu thay đổi theo sheet
    description: str  # đã thay đổi gì (không có địa chỉ ô, không có số liệu)
    label: str  # "cột Số lượng", "dòng TỔNG CỘNG"…
    checks: tuple[Check, ...]
    sources: tuple[tuple[str, str], ...] = ()  # (vùng, nhãn) dữ liệu nguồn để chỉ cho học viên
    context: str = ""  # chỉ cho AI: mỗi dòng của vùng ứng với gì ("Ngày", "Mã hàng"…)
    operation: Mapping[str, Any] | None = None  # thao tác cấu trúc theo quy trình trong đề (mã p1, p2…)
    more_ranges: tuple[str, ...] = ()  # vùng khoanh thêm (xóa các cột không liền nhau D, E, H)
    feedback_codes: tuple[str, ...] = ()  # mã lỗi đáng viết phản hồi; rỗng: mọi mã của các điều kiện

    def codes(self) -> list[str]:
        """Mã lỗi AI được viết phản hồi cho mục này."""
        if self.feedback_codes:
            return list(self.feedback_codes)
        return sorted({code for check in self.checks for code in codes_for(check["type"])})


@dataclass(frozen=True)
class ExerciseAnalysis:
    sheet: str
    changes: tuple[ChangeItem, ...]
    global_checks: tuple[Check, ...]
    preserved: tuple[str, ...]  # mô tả vùng giữ nguyên, cho prompt
    workbook_text: tuple[str, ...]  # câu chữ dài trong file đề (yêu cầu, hướng dẫn)
    starter: WorkbookSnapshot = field(repr=False)
    solution: WorkbookSnapshot = field(repr=False)

    def change(self, change_id: str) -> ChangeItem | None:
        return next((c for c in self.changes if c.id == change_id), None)


# ---------------------------------------------------------------- nhãn
def _text(sheet: SheetSnapshot, col: int, row: int) -> str | None:
    cell = sheet.cell(cell_address(col, row))
    if cell.value_kind == "text" and not cell.is_formula:
        text = str(cell.value).strip()
        if 0 < len(text) <= MAX_LABEL_LENGTH:
            return text
    return None


def column_header(sheet: SheetSnapshot, col: int, top_row: int) -> str | None:
    for row in range(top_row - 1, max(0, top_row - 1 - HEADER_SEARCH_ROWS), -1):
        if text := _text(sheet, col, row):
            return text
    return None


def row_header(sheet: SheetSnapshot, row: int, left_col: int) -> str | None:
    for col in range(left_col - 1, 0, -1):
        if text := _text(sheet, col, row):
            return text
    return None


def range_label(sheet: SheetSnapshot, rng: CellRange) -> str:
    """Nhãn để AI gọi tên vùng: "cột Số lượng", "dòng TỔNG CỘNG", "dòng tiêu đề STT, Họ tên"…"""
    first_row = [t for c in rng.cols() if (t := _text(sheet, c, rng.min_row))]
    mostly_text = len(first_row) * 2 >= rng.width
    if rng.width > 1 and mostly_text:
        names = ", ".join(first_row[:MAX_LABEL_NAMES])
        return f"dòng tiêu đề {names}" if rng.height == 1 else f"bảng gồm các cột {names}"
    top_left = _text(sheet, rng.min_col, rng.min_row)
    if top_left:
        return f'ô "{top_left}"' if rng.size == 1 else f'vùng "{top_left}"'
    columns = list(dict.fromkeys(h for c in rng.cols() if (h := column_header(sheet, c, rng.min_row))))
    row = row_header(sheet, rng.min_row, rng.min_col) if rng.height == 1 else None
    if rng.height == 1 and rng.width > 1 and row:
        return f"dòng {row}"
    if rng.size == 1 and columns and row:
        return f"ô {columns[0]} của dòng {row}"
    if columns:
        label = ", ".join(f"cột {h}" for h in columns)
        return label
    return f"dòng {row}" if row else "vùng ô"


def _row_context(sheet: SheetSnapshot, rng: CellRange) -> str:
    key = row_key(sheet, rng) if rng.height > 1 else None
    return f"mỗi dòng ứng với một {key}" if key else ""


def row_key(sheet: SheetSnapshot, rng: CellRange) -> str | None:
    """Tiêu đề của cột nhận dạng dòng (cột có dữ liệu đầu tiên bên trái vùng), để AI biết mỗi dòng là gì.

    b22: cột Tổng tiền, mỗi dòng ứng với một "Ngày" (T5.5: AI tưởng mỗi dòng là một món hàng).
    """
    for col in range(1, rng.min_col):
        kinds = [sheet.cell(cell_address(col, row)).value_kind for row in rng.rows()]
        filled = [k for k in kinds if k != "empty"]
        # Bỏ cột số (STT, số liệu): cột nhận dạng là chữ (mã, tên) hoặc ngày
        if filled and sum(k in ("text", "date") for k in filled) * 2 > len(filled):
            return column_header(sheet, col, rng.min_row)
    return None


# ---------------------------------------------------------------- vùng nguồn, vùng liền khối
def _values(sheet: SheetSnapshot, rng: CellRange) -> list[CellValue]:
    return [sheet.cell(a).value for a in rng.cells()]


def value_source(
    starter: SheetSnapshot, solution: SheetSnapshot, rng: CellRange, used: CellRange
) -> CellRange | None:
    """Vùng cùng kích thước trong file đề có đúng các giá trị học viên phải chép (b09: bảng số liệu thô)."""
    target = _values(solution, rng)
    if all(v is None for v in target):
        return None
    for row in range(used.min_row, used.max_row - rng.height + 2):  # cùng cột, dòng khác
        if row != rng.min_row:
            candidate = CellRange(rng.min_col, row, rng.max_col, row + rng.height - 1)
            if _values(starter, candidate) == target:
                return candidate
    for col in range(used.min_col, used.max_col - rng.width + 2):  # cùng dòng, cột khác
        if col != rng.min_col:
            candidate = CellRange(col, rng.min_row, col + rng.width - 1, rng.max_row)
            if _values(starter, candidate) == target:
                return candidate
    return None


def _has_content(sheet: SheetSnapshot, rng: CellRange) -> bool:
    return any(not sheet.cell(a).is_empty for a in rng.cells())


def current_region(sheet: SheetSnapshot, rng: CellRange, bounds: CellRange) -> CellRange:
    """Như CurrentRegion của Excel: nới từng cạnh khi hàng/cột ngay bên ngoài còn ô có dữ liệu."""
    top, left, bottom, right = rng.min_row, rng.min_col, rng.max_row, rng.max_col
    grew = True
    while grew and (bottom - top + 1) * (right - left + 1) <= MAX_REGION_CELLS:
        grew = False
        if top > bounds.min_row and _has_content(sheet, CellRange(left, top - 1, right, top - 1)):
            top, grew = top - 1, True
        if bottom < bounds.max_row and _has_content(sheet, CellRange(left, bottom + 1, right, bottom + 1)):
            bottom, grew = bottom + 1, True
        if left > bounds.min_col and _has_content(sheet, CellRange(left - 1, top, left - 1, bottom)):
            left, grew = left - 1, True
        if right < bounds.max_col and _has_content(sheet, CellRange(right + 1, top, right + 1, bottom)):
            right, grew = right + 1, True
    return CellRange(left, top, right, bottom)


def _used(sheet: SheetSnapshot) -> CellRange:
    box = parse_range(sheet.read_ranges[0].range)
    for read in sheet.read_ranges[1:]:
        box = box.union(parse_range(read.range))
    return box


# ---------------------------------------------------------------- sắp xếp
def _rows(sheet: SheetSnapshot, table: CellRange) -> list[tuple[CellValue, ...]]:
    return [
        tuple(sheet.cell(cell_address(c, r)).value for c in table.cols())
        for r in range(table.min_row + 1, table.max_row + 1)
    ]


def _monotonic(values: list[CellValue]) -> str | None:
    keys = [sort_key(v) for v in values if v is not None]
    if len(keys) < 2 or len(set(keys)) < 2:
        return None
    if all(a <= b for a, b in zip(keys, keys[1:], strict=False)):
        return "asc"
    if all(a >= b for a, b in zip(keys, keys[1:], strict=False)):
        return "desc"
    return None


def detect_sort(starter: SheetSnapshot, solution: SheetSnapshot, table: CellRange) -> Check | None:
    """Bảng có cùng tập dòng nhưng đổi thứ tự, và một cột trong đáp án có thứ tự tăng/giảm → sắp xếp."""
    if table.height < 3:
        return None
    before, after = _rows(starter, table), _rows(solution, table)
    if before == after or Counter(before) != Counter(after):
        return None
    for index, col in enumerate(table.cols()):
        order = _monotonic([row[index] for row in after])
        header = _text(solution, col, table.min_row)
        if order and header and _monotonic([row[index] for row in before]) != order:
            return {"type": "sorted_by", "range": str(table), "key_column": header, "order": order}
    return None


# ---------------------------------------------------------------- mô tả thay đổi
def describe_change(change: Change, solution: SheetSnapshot | None, rng: CellRange | None) -> str:
    """Mô tả không có địa chỉ ô, không có số liệu: công thức chỉ nói dùng hàm gì, có sao chép không."""
    name = KIND_NAMES.get(change.kind.value, change.kind.value)
    if change.kind == ChangeKind.FORMULA and solution is not None and rng is not None:
        top = solution.cell(cell_address(rng.min_col, rng.min_row))
        functions = formula_functions(top.formula or "")
        how = f"dùng hàm {', '.join(functions)}" if functions else "tính bằng phép toán từ các ô khác"
        try:
            operators = set(parse_formula(top.formula or "=0").infix_operators)
        except FormulaError:
            operators = set()
        if not functions and operators:
            how += f" ({' '.join(sorted(operators))})"
        copied = "; một công thức sao chép cho cả vùng" if rng.size > 1 else ""
        return f"{name}: {how}{copied}"
    if change.kind == ChangeKind.VALUE:
        return f"{name}: {change.before} → {change.after}"
    return f"{name}: {change.before} → {change.after}" if change.before else f"{name}: {change.after}"


# ---------------------------------------------------------------- tách thay đổi thành mục cho AI
CELL_LEVEL = frozenset(
    {
        ChangeKind.VALUE,
        ChangeKind.FORMULA,
        ChangeKind.NUMBER_FORMAT,
        ChangeKind.ALIGNMENT,
        ChangeKind.FONT,
        ChangeKind.FILL,
        ChangeKind.BORDER,
        ChangeKind.MERGED,
    }
)
LINE_LEVEL = frozenset(
    {ChangeKind.ROW_HIDDEN, ChangeKind.COL_HIDDEN, ChangeKind.ROW_HEIGHT, ChangeKind.COL_WIDTH}
)
SHEET_LEVEL = frozenset(
    {ChangeKind.AUTOFILTER, ChangeKind.PAGE_SETUP, ChangeKind.CHART, ChangeKind.SHEET_ADDED}
)
MAX_GLOBAL_RANGES = 6
LAYOUT_KIND_NAMES = frozenset(kind.value for kind in LAYOUT_KINDS)


def _filled(sheet: SheetSnapshot, rng: CellRange) -> CellRange | None:
    """Khung nhỏ nhất bao các ô có nội dung trong vùng; vùng trống thì None."""
    cells = [(c, r) for r in rng.rows() for c in rng.cols() if not sheet.cell(cell_address(c, r)).is_empty]
    if not cells:
        return None
    cols, rows = [c for c, _ in cells], [r for _, r in cells]
    return CellRange(min(cols), min(rows), max(cols), max(rows))


def _moved_span(layout: SheetLayout, starter: SheetSnapshot, solution: SheetSnapshot, is_col: bool) -> range:
    """Dải cột (dòng) của đáp án bị dời chỗ mà nội dung giữ nguyên: chỉ cần chèn/xóa đúng là khớp."""
    axis = layout.cols if is_col else layout.rows
    used = _used(solution)

    def line(index: int) -> CellRange:
        if is_col:
            return CellRange(index, used.min_row, index, used.max_row)
        return CellRange(used.min_col, index, used.max_col, index)

    moved = []
    for index, source in sorted(axis.to_starter.items()):
        after, before = line(index), line(source)
        if (
            index != source
            and _has_content(solution, after)
            and _values(solution, after) == _values(starter, before)
        ):
            moved.append(index)
    if not moved:
        return range(0)
    end = moved[0]
    while end + 1 in moved:
        end += 1
    return range(moved[0], end + 1)


def layout_check(starter: SheetSnapshot, solution: SheetSnapshot, is_col: bool) -> Check | None:
    """layout_matches trên phần bị dời chỗ: đạt khi chèn/xóa đúng, không chờ học viên làm xong bước khác."""
    layout = sheet_layout(starter, solution)
    span = _moved_span(layout, starter, solution, is_col)
    if not span:
        return None
    used = _used(solution)
    region = (
        CellRange(span.start, used.min_row, span.stop - 1, used.max_row)
        if is_col
        else CellRange(used.min_col, span.start, used.max_col, span.stop - 1)
    )
    table = _filled(solution, region)
    if table is None:
        return None
    key = next(
        (
            str(cell.value)
            for col in table.cols()
            if not (cell := solution.cell(cell_address(col, table.min_row))).is_empty
        ),
        "",
    )
    return {
        "type": "layout_matches",
        "range": str(table),
        "key_column": key[:100],
        "description": "Dữ liệu dời đúng chỗ sau khi chèn/xóa.",
    }


def _split(change: Change) -> list[CellRange]:
    rng = parse_range(change.range or "")
    if change.kind in SPLIT_BY_COLUMN and rng.width > 1 and rng.height > 1:
        return [CellRange(c, rng.min_row, c, rng.max_row) for c in rng.cols()]
    return [rng]


def _auto_row_height(change: Change, changes: tuple[Change, ...]) -> bool:
    """Dòng cao lên vì cỡ chữ lớn hơn (Excel tự giãn), không phải người làm đáp án chỉnh (b14)."""
    if change.kind != ChangeKind.ROW_HEIGHT or not change.range:
        return False
    row = int(change.range.split(":")[0])
    for other in changes:
        if other.kind == ChangeKind.FONT and other.sheet == change.sheet and other.range:
            rng = parse_range(other.range)
            if rng.min_row <= row <= rng.max_row:
                return True
    return False


def _line_range(change: Change, used: CellRange) -> tuple[CellRange, str]:
    first, _, last = (change.range or "").partition(":")
    last = last or first
    suffix = f"–{last}" if last != first else ""
    if first.isdigit():
        return CellRange(used.min_col, int(first), used.max_col, int(last)), f"dòng {first}{suffix}"
    start, end = parse_range(f"{first}1").min_col, parse_range(f"{last}1").min_col
    return CellRange(start, used.min_row, end, used.max_row), f"cột {first}{suffix}"


def _sheet_target(checks: list[Check], sheet: SheetSnapshot) -> CellRange:
    for check in checks:
        for key in ("range", "data_range", "print_area"):
            if key in check:
                return parse_range(check[key])
    return _used(sheet)


# Lệnh Ribbon dùng khi đã chọn các ô (không chọn cả cột/dòng) để chỉ tác động đúng cột/dòng cần
_COMMANDS = {
    ChangeKind.COL_WIDTH: "Format > Column Width (áp cho cột của các ô đang chọn)",
    ChangeKind.ROW_HEIGHT: "Format > Row Height (áp cho dòng của các ô đang chọn)",
    ChangeKind.COL_HIDDEN: "Format > Hide & Unhide > Hide Columns hoặc Unhide Columns",
    ChangeKind.ROW_HIDDEN: "Format > Hide & Unhide > Hide Rows hoặc Unhide Rows",
    ChangeKind.COL_DELETED: "mũi tên của nút Delete > Delete Sheet Columns (bấm thẳng nút Delete chỉ xóa ô)",
    ChangeKind.ROW_DELETED: "mũi tên của nút Delete > Delete Sheet Rows (bấm thẳng nút Delete chỉ xóa ô)",
    ChangeKind.COL_INSERTED: "mũi tên của nút Insert > Insert Sheet Columns",
    ChangeKind.ROW_INSERTED: "mũi tên của nút Insert > Insert Sheet Rows",
}
_COL_KINDS = frozenset(
    {ChangeKind.COL_WIDTH, ChangeKind.COL_HIDDEN, ChangeKind.COL_DELETED, ChangeKind.COL_INSERTED}
)


def wide_merges(sheet: SheetSnapshot, span: CellRange, is_col: bool) -> list[CellRange]:
    """Ô gộp đi qua các cột (dòng) này mà tràn sang cột (dòng) khác.

    Bấm chuột vào tiêu đề cột thì Excel chỉ chọn đúng cột đó. Nhưng bấm vào ô gộp, hay chọn bằng lệnh (gõ địa
    chỉ vào Name Box, Go To) thì Excel nới vùng chọn cho trọn ô gộp (bài 06: gõ F:G thành B:H vì tiêu đề gộp
    B9:H9); đổi độ rộng hay xóa cột theo vùng chọn đó là sai cả loạt cột.
    """
    found = []
    for text in sheet.merged:
        m = parse_range(text)
        if is_col:
            crosses = m.min_col <= span.max_col and m.max_col >= span.min_col
            spills = m.min_col < span.min_col or m.max_col > span.max_col
        else:
            crosses = m.min_row <= span.max_row and m.max_row >= span.min_row
            spills = m.min_row < span.min_row or m.max_row > span.max_row
        if crosses and spills:
            found.append(m)
    return found


def merge_safe_cells(sheet: SheetSnapshot, span: CellRange, is_col: bool) -> CellRange | None:
    """Dãy ô trên một dòng (cột) không dính ô gộp: chọn các ô này rồi dùng lệnh Ribbon thì chỉ tác động đúng
    các cột (dòng) cần. Ưu tiên dòng có nội dung, không ẩn."""
    merges = [parse_range(m) for m in sheet.merged]
    lines = span.rows() if is_col else span.cols()
    candidates = []
    for line in lines:
        box = (
            CellRange(span.min_col, line, span.max_col, line)
            if is_col
            else CellRange(line, span.min_row, line, span.max_row)
        )
        hidden = line in sheet.hidden_rows if is_col else column_letter(line) in sheet.hidden_cols
        if hidden or any(m.intersects(box) for m in merges):
            continue
        candidates.append(box)
    used = _used(sheet)

    def in_table(box: CellRange) -> bool:
        line = box.min_row if is_col else box.min_col
        whole = (
            CellRange(used.min_col, line, used.max_col, line)
            if is_col
            else CellRange(line, used.min_row, line, used.max_row)
        )
        return _has_content(sheet, whole)

    # Ưu tiên ô có nội dung, rồi dòng (cột) nằm trong bảng, cuối cùng mới là dòng trống
    ranked = [box for box in candidates if _has_content(sheet, box)] + [b for b in candidates if in_table(b)]
    return (ranked or candidates or [None])[0]


def hidden_lines(sheet: SheetSnapshot, rng: CellRange, is_col: bool) -> list[str]:
    """Cột (chữ) / dòng (số) đang ẩn trong vùng: học viên không bấm hay kéo chuột tới được."""
    if is_col:
        return [column_letter(c) for c in rng.cols() if column_letter(c) in sheet.hidden_cols]
    return [str(r) for r in rng.rows() if r in sheet.hidden_rows]


def _hidden_note(kind: ChangeKind, target: CellRange, merged: bool, hidden: list[str]) -> str:
    """Dặn AI cách chọn khi trong vùng có cột (dòng) đang ẩn: không bấm hay kéo chuột tới được.

    Bài 06: cột E của file đề đang ẩn, kéo từ tiêu đề D thì chỉ được D hoặc lố sang F. Gõ địa chỉ vào Name Box
    thì chọn được cả cột ẩn; nhưng chọn kiểu này Excel nới theo ô gộp, nên khi có ô gộp tràn ra ngoài thì gõ
    các ô ở một dòng không có ô gộp (`target`) chứ không gõ cả cột.
    """
    if not hidden:
        return ""
    unit, other = ("cột", "dòng") if kind in _COL_KINDS else ("dòng", "cột")
    merge_part = (
        f" (các ô ở {other} không có ô gộp: gõ cả {unit} hay ô thuộc ô gộp thì Excel chọn lan theo ô gộp)"
        if merged
        else ""
    )
    return (
        f"{unit} {', '.join(hidden)} đang ẩn nên học viên không bấm hay kéo chuột tới được. Hướng dẫn chọn "
        f"bằng cách gõ {target} vào ô Name Box (bên trái thanh công thức) rồi nhấn Enter{merge_part}, rồi "
        f"dùng {_COMMANDS[kind]}"
    )


def _changed_lines(changes: Iterable[Change]) -> dict[tuple[str, ChangeKind], set[str]]:
    """Cột (chữ) / dòng (số dạng chữ) có thay đổi kích thước, theo sheet và loại."""
    found: dict[tuple[str, ChangeKind], set[str]] = {}
    for change in changes:
        if change.kind in (ChangeKind.COL_WIDTH, ChangeKind.ROW_HEIGHT) and change.range:
            first, _, last = change.range.partition(":")
            lines = (
                {column_letter(c) for c in range(column_index(first), column_index(last or first) + 1)}
                if change.kind == ChangeKind.COL_WIDTH
                else {str(r) for r in range(int(first), int(last or first) + 1)}
            )
            found.setdefault((change.sheet, change.kind), set()).update(lines)
    return found


class _Builder:
    def __init__(
        self, starter: WorkbookSnapshot, solution: WorkbookSnapshot, changes: Iterable[Change] = ()
    ) -> None:
        self.starter, self.solution = starter, solution
        self.resized = _changed_lines(changes)
        self.items: list[ChangeItem] = []
        self.emitted_sheet_kinds: set[tuple[str, ChangeKind]] = set()

    def next_id(self) -> str:
        return f"c{len(self.items) + 1}"

    def add_sort(self, sheet: str, check: Check) -> None:
        order = "tăng dần" if check["order"] == "asc" else "giảm dần"
        description = f"sắp xếp bảng theo cột {check['key_column']} {order}, giữ nguyên từng dòng"
        label = f"bảng có cột {check['key_column']}"
        self.items.append(
            ChangeItem(self.next_id(), sheet, "sort", check["range"], description, label, (check,))
        )

    def add(self, change: Change) -> None:
        if change.kind in LAYOUT_KINDS and change.range:
            self._add_layout(change)
        elif change.kind in CELL_LEVEL and change.range:
            self._add_cells(change)
        elif change.kind in LINE_LEVEL and change.range:
            self._add_line(change)
        elif change.kind in SHEET_LEVEL and (change.sheet, change.kind) not in self.emitted_sheet_kinds:
            self.emitted_sheet_kinds.add((change.sheet, change.kind))
            self._add_sheet_object(change)

    def _add_line(self, change: Change) -> None:
        sheet = self.solution.sheet(change.sheet)
        rng, label = _line_range(change, _used(sheet))
        checks = line_check(change)
        if not checks:
            return
        is_col = change.kind in _COL_KINDS
        merges = wide_merges(sheet, rng, is_col)
        if merges:
            checks += self._keep_sizes(change, sheet, rng, merges, is_col)
        description = f"{KIND_NAMES[change.kind.value]}: {change.before or '…'} → {change.after}"
        item = ChangeItem(
            self.next_id(),
            change.sheet,
            change.kind.value,
            str(rng),
            description,
            label,
            tuple(checks),
        )
        self.items.append(item)

    def _keep_sizes(
        self, change: Change, sheet: SheetSnapshot, rng: CellRange, merges: list[CellRange], is_col: bool
    ) -> list[Check]:
        """Các cột (dòng) khác của ô gộp giữ nguyên kích thước: bắt lỗi bấm vào ô gộp (chọn cả B–H) rồi đổi
        độ rộng."""
        if change.kind not in (ChangeKind.COL_WIDTH, ChangeKind.ROW_HEIGHT):
            return []
        own = (
            {column_letter(c) for c in rng.cols()} if is_col else {str(r) for r in rng.rows()}
        ) | self.resized.get((change.sheet, change.kind), set())
        span = sorted(
            {c for m in merges for c in m.cols()} if is_col else {r for m in merges for r in m.rows()}
        )
        checks: list[Check] = []
        for line in span:
            key = column_letter(line) if is_col else str(line)
            size = sheet.col_widths.get(key) if is_col else sheet.row_heights.get(line)
            if key in own or size is None or (is_col and key in sheet.hidden_cols):
                continue
            unit = "Cột" if is_col else "Dòng"
            checks.append(
                {
                    "type": "row_col_size",
                    "cols" if is_col else "rows": key,
                    "equals": size,
                    "description": f"{unit} {key} giữ nguyên kích thước (không chọn lan theo ô gộp).",
                }
            )
        return checks

    def _add_layout(self, change: Change) -> None:
        """Chèn/xóa cột, dòng: vùng mục tiêu theo bố cục học viên đang thấy, điều kiện kiểm phần bị dịch."""
        starter, solution = self.starter.sheet(change.sheet), self.solution.sheet(change.sheet)
        deleted = change.kind in (ChangeKind.COL_DELETED, ChangeKind.ROW_DELETED)
        is_col = change.kind in (ChangeKind.COL_DELETED, ChangeKind.COL_INSERTED)
        # Xóa: học viên làm trên bố cục của đề; chèn: chỗ chèn tính theo đáp án
        base = starter if deleted else solution
        lines = _line_range(change, _used(base))[0]
        # Cột (dòng) ẩn: chọn qua Name Box; có thêm ô gộp tràn ra ngoài thì gõ các ô ở dòng không có ô gộp
        hidden = hidden_lines(base, lines, is_col)
        merged = bool(hidden and wide_merges(base, lines, is_col))
        target = (merge_safe_cells(base, lines, is_col) or lines) if merged else lines
        context = _hidden_note(change.kind, target, merged, hidden)
        check = layout_check(starter, solution, is_col)
        if check is None:
            return
        first, _, last = (change.range or "").partition(":")
        count = (column_index(last) - column_index(first) if is_col else int(last) - int(first)) + 1
        unit = "cột" if is_col else "dòng"
        empty = deleted and not _has_content(starter, lines)
        description = f"{'xóa' if deleted else 'chèn'} {count} {unit}{' trống' if empty else ''}"
        label = (
            f"{unit} {first}" + (f"–{last}" if last != first else "") + (" của file đề" if deleted else "")
        )
        self.items.append(
            ChangeItem(
                self.next_id(),
                change.sheet,
                change.kind.value,
                str(target),
                description,
                label,
                (check,),
                context=context,
            )
        )

    def _add_sheet_object(self, change: Change) -> None:
        checks = sheet_object_checks(change.kind, change.sheet, self.starter, self.solution)
        if not checks or change.sheet not in self.solution.sheets:
            return
        target = _sheet_target(checks, self.solution.sheet(change.sheet))
        name = KIND_NAMES[change.kind.value]
        label = f"trang tính {change.sheet}"
        item = ChangeItem(
            self.next_id(), change.sheet, change.kind.value, str(target), name, label, tuple(checks)
        )
        self.items.append(item)

    def _add_cells(self, change: Change) -> None:
        starter, solution = self.starter.sheet(change.sheet), self.solution.sheet(change.sheet)
        for rng in _split(change):
            source = None
            if change.kind == ChangeKind.VALUE:
                source = value_source(starter, solution, rng, _used(starter))
            checks = cell_change_checks(change, rng, starter, solution, source)
            if not checks:
                continue
            sources = ((str(source), f"{range_label(starter, source)} (dữ liệu có sẵn)"),) if source else ()
            self.items.append(
                ChangeItem(
                    self.next_id(),
                    change.sheet,
                    change.kind.value,
                    str(rng),
                    describe_change(change, solution, rng),
                    range_label(solution, rng),
                    tuple(checks),
                    sources,
                    _row_context(solution, rng),
                )
            )


# ---------------------------------------------------------------- vùng giữ nguyên → điều kiện toàn bài
def _cells_of(ranges: list[str]) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for text in ranges:
        rng = parse_range(text)
        cells.update((c, r) for r in rng.rows() for c in rng.cols())
    return cells


def _formula_precedents(
    item: ChangeItem, starter: SheetSnapshot, solution: SheetSnapshot
) -> set[tuple[int, int]]:
    """Ô hằng số mà công thức mới tham chiếu tới, không đổi từ đề sang đáp án (b22: số liệu tiền chợ)."""
    found: set[tuple[int, int]] = set()
    for address in parse_range(item.range or "").cells():
        try:
            references = parse_formula(solution.cell(address).formula or "=0").references
        except FormulaError:
            continue
        for reference in references:
            if "!" in reference:
                continue
            try:
                rng = parse_range(reference)
            except ValueError:
                continue
            for cell in rng.cells():
                before, after = starter.cell(cell), solution.cell(cell)
                if not before.is_empty and not before.is_formula and before.value == after.value:
                    found.add(parse_cell(cell))
    return found


def protection(
    items: list[ChangeItem], starter: WorkbookSnapshot, solution: WorkbookSnapshot, sheet: str
) -> tuple[list[Check], list[str]]:
    """Điều kiện toàn bài: công thức có sẵn không bị gõ đè, dữ liệu gốc không bị sửa."""
    if sheet not in starter.sheets or sheet not in solution.sheets:
        return [], []
    if any(i.sheet == sheet and i.kind in LAYOUT_KIND_NAMES for i in items):
        # Bài chèn/xóa cột, dòng: dữ liệu dời chỗ hợp lệ, so theo địa chỉ sẽ báo nhầm "sửa dữ liệu gốc"
        return [], []
    before, after = starter.sheet(sheet), solution.sheet(sheet)
    mine = [i for i in items if i.sheet == sheet and i.range]
    changed = _cells_of([i.range for i in mine if i.range])
    checks: list[Check] = []
    preserved: list[str] = []
    kept = [
        parse_cell(a)
        for a, cell in before.cells.items()
        if cell.is_formula and after.cell(a).formula == cell.formula
    ]
    for rng in group_into_ranges(kept)[:MAX_GLOBAL_RANGES]:
        checks.append(
            {"type": "is_formula", "range": str(rng), "description": "Không gõ đè lên công thức có sẵn."}
        )
        preserved.append(f"{range_label(after, rng)}: công thức có sẵn, học viên KHÔNG được gõ đè")
    sources: set[tuple[int, int]] = set()
    for item in mine:
        for source, _ in item.sources:
            region = _cells_of([str(current_region(before, parse_range(source), _used(before)))])
            sources |= region if not region & changed else _cells_of([source])
        if item.kind == ChangeKind.FORMULA.value:
            sources |= _formula_precedents(item, before, after)
    for rng in group_into_ranges(sources - changed)[:MAX_GLOBAL_RANGES]:
        if rng.size < 2:
            continue
        checks.append({"type": "data_unchanged", "range": str(rng), "description": "Không sửa dữ liệu gốc."})
        preserved.append(f"{range_label(before, rng)}: dữ liệu gốc, học viên KHÔNG được sửa")
    return checks, preserved


def workbook_text(starter: WorkbookSnapshot, shapes: Sequence[ShapeText] = ()) -> list[str]:
    """Câu chữ trong file đề (yêu cầu, hướng dẫn) để AI hiểu đề bài: khối chữ trong hình vẽ (đề hay ghi các
    bước thực hành ở đây, bài 06) rồi câu dài trong ô."""
    texts = [
        f"[{shape.sheet}, khối chữ “{shape.name}”]\n" + "\n".join(f"  - {line}" for line in shape.lines)
        for shape in shapes
    ]
    for sheet in starter.sheets.values():
        for cell in sheet.cells.values():
            if cell.value_kind == "text" and len(str(cell.value)) >= MIN_INSTRUCTION_LENGTH:
                texts.append(f"[{sheet.name}] {str(cell.value).strip()}")
    return texts[:MAX_INSTRUCTIONS]


def _detect_sorts(
    starter: WorkbookSnapshot, solution: WorkbookSnapshot, diff_changes: tuple[Change, ...], builder: _Builder
) -> set[int]:
    """Thêm mục "sắp xếp" và trả về vị trí các thay đổi giá trị mà thao tác sắp xếp đã giải thích."""
    covered: set[int] = set()
    for name in solution.sheets:
        if name not in starter.sheets:
            continue
        after = solution.sheet(name)
        tables: dict[CellRange, list[int]] = {}
        for index, change in enumerate(diff_changes):
            if change.sheet == name and change.kind == ChangeKind.VALUE and change.range:
                table = current_region(after, parse_range(change.range), _used(after))
                tables.setdefault(table, []).append(index)
        for table, indices in tables.items():
            check = detect_sort(starter.sheet(name), after, table)
            if check is not None:
                builder.add_sort(name, check)
                covered.update(indices)
    return covered


def analyze_exercise(starter_path: Path | str, solution_path: Path | str, sheet: str) -> ExerciseAnalysis:
    request = pair_request(starter_path, solution_path)
    starter, solution = read_workbook(starter_path, request), read_workbook(solution_path, request)
    return analyze_snapshots(starter, solution, sheet, shape_texts(starter_path))


def analyze_snapshots(
    starter: WorkbookSnapshot, solution: WorkbookSnapshot, sheet: str, shapes: Sequence[ShapeText] = ()
) -> ExerciseAnalysis:
    """Như analyze_exercise trên hai snapshot (file đề có thể là trạng thái sau quy trình, procedure.py)."""
    diff = diff_workbooks(starter, solution)
    builder = _Builder(starter, solution, diff.changes)
    covered = _detect_sorts(starter, solution, diff.changes, builder)
    for index, change in enumerate(diff.changes):
        if index not in covered and not _auto_row_height(change, diff.changes):
            builder.add(change)
    global_checks, preserved = protection(builder.items, starter, solution, sheet)
    return ExerciseAnalysis(
        sheet=sheet,
        changes=tuple(builder.items),
        global_checks=tuple(global_checks),
        preserved=tuple(preserved),
        workbook_text=tuple(workbook_text(starter, shapes)),
        starter=starter,
        solution=solution,
    )
