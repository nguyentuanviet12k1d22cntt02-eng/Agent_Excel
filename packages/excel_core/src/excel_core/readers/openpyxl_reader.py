"""Đọc file .xlsx thành WorkbookSnapshot bằng openpyxl (Backend, T4.2). Thiết kế: snapshot.md mục 5.

File được mở 2 lần: `data_only=True` lấy giá trị đã tính (giá trị cache do Excel lưu), lần thường lấy công
thức và định dạng. File tạo bằng code mà chưa qua Excel thì ô công thức không có giá trị (None).
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import openpyxl
from openpyxl.cell.cell import Cell, MergedCell
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.worksheet.worksheet import Worksheet

from excel_core.address import CellRange, cell_address, column_letter, parse_range
from excel_core.formula import FormulaError, normalize_formula, to_r1c1
from excel_core.readers.colors import resolve_color, theme_palette
from excel_core.readers.openpyxl_objects import read_autofilter, read_charts, read_page_setup
from excel_core.snapshot import (
    CELL_GROUPS,
    SHEET_GROUPS,
    AlignmentInfo,
    BorderInfo,
    CellSnapshot,
    CellValue,
    ErrorValue,
    FillInfo,
    FontInfo,
    PropertyGroup,
    RangeRead,
    RangeRequest,
    ReadRequest,
    SheetRequest,
    SheetSnapshot,
    ValueKind,
    WorkbookSnapshot,
    parse_number_format,
)

logger = logging.getLogger(__name__)

EXERCISE_ID_PROPERTY = "tutor_exercise_id"
EXCEL_EPOCH = datetime(1899, 12, 30)  # ngày gốc của số seri ngày trong Excel
DEFAULT_FONT_COLOR = "#000000"
MAX_DIGIT_WIDTH_PX = 7  # Calibri 11, phông mặc định: dùng để đổi độ rộng cột trong file → số ký tự
COLUMN_PADDING_PX = 5
_HORIZONTAL = {None: "general", "centerContinuous": "center_across"}
_VERTICAL = {None: "bottom"}


@dataclass(frozen=True)
class _Book:
    formulas: Workbook
    values: Workbook
    palette: tuple[str, ...]


def used_range(ws: Worksheet) -> str:
    """Vùng đang dùng của sheet (gồm cả ô chỉ có định dạng)."""
    return str(parse_range(ws.calculate_dimension()))


def full_request(workbook: Workbook | Path | str) -> ReadRequest:
    """Yêu cầu đọc mọi thứ: vùng đang dùng của mọi trang tính, mọi nhóm thuộc tính."""
    wb = workbook if isinstance(workbook, Workbook) else openpyxl.load_workbook(workbook)
    ranges, sheets = [], []
    for ws in wb.worksheets:
        ranges.append(RangeRequest(ws.title, used_range(ws), CELL_GROUPS))
        sheets.append(SheetRequest(ws.title, SHEET_GROUPS))
    return ReadRequest(tuple(ranges), tuple(sheets))


def read_workbook(path: Path | str, request: ReadRequest | None = None) -> WorkbookSnapshot:
    """Đọc file theo yêu cầu đọc; không có yêu cầu thì đọc mọi thứ (`full_request`)."""
    path = Path(path)
    formulas = openpyxl.load_workbook(path)
    book = _Book(formulas, openpyxl.load_workbook(path, data_only=True), theme_palette(formulas.loaded_theme))
    request = request or full_request(formulas)
    sheets = {}
    for name in request.sheet_names:
        if name not in formulas.sheetnames or not isinstance(formulas[name], Worksheet):
            logger.debug("Bỏ qua sheet %r: không có hoặc không phải trang tính", name)
            continue
        ranges = [r for r in request.ranges if r.sheet == name]
        sheets[name] = _read_sheet(book, name, ranges, request.sheet_groups(name))
    return WorkbookSnapshot(
        source="openpyxl",
        taken_at=datetime.now(),
        exercise_id=_exercise_id(formulas),
        sheet_names=tuple(formulas.sheetnames),
        active_sheet=formulas.active.title if formulas.active is not None else None,
        sheets=sheets,
    )


def find_uncalculated_formulas(path: Path | str, sheet_names: list[str] | None = None) -> list[str]:
    """Ô công thức chưa có giá trị đã tính, dạng "Sheet!A1" (file tạo bằng code, chưa được Excel mở và lưu).

    Phân biệt với công thức trả về chuỗi rỗng: Excel lưu kết quả đó kèm kiểu chuỗi (`t="str"`), còn ô chưa
    tính không có kiểu, openpyxl đọc ra `None` với kiểu số `n`.
    """
    formulas = openpyxl.load_workbook(path)
    values = openpyxl.load_workbook(path, data_only=True)
    found = []
    for ws in formulas.worksheets:
        if sheet_names is not None and ws.title not in sheet_names:
            continue
        cached_sheet = values[ws.title]
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type != "f" and not isinstance(cell.value, ArrayFormula):
                    continue
                cached = cached_sheet[cell.coordinate]
                if cached.value is None and cached.data_type == "n":
                    found.append(f"{ws.title}!{cell.coordinate}")
    return found


def _exercise_id(wb: Workbook) -> str | None:
    for prop in wb.custom_doc_props.props:
        if prop.name == EXERCISE_ID_PROPERTY:
            return str(prop.value)
    return None


def _read_sheet(
    book: _Book, name: str, ranges: list[RangeRequest], sheet_groups: frozenset[PropertyGroup]
) -> SheetSnapshot:
    ws_f, ws_v = book.formulas[name], book.values[name]
    structure_ranges = [parse_range(r.range) for r in ranges if PropertyGroup.STRUCTURE in r.groups]
    merged, hidden_rows, hidden_cols, heights, widths = _read_structure(ws_f, structure_ranges)
    return SheetSnapshot(
        name=name,
        cells=_read_cells(ws_f, ws_v, ranges, book.palette),
        read_ranges=tuple(RangeRead(str(parse_range(r.range)), r.groups) for r in ranges),
        sheet_groups=sheet_groups,
        merged=merged,
        hidden_rows=hidden_rows,
        hidden_cols=hidden_cols,
        row_heights=heights,
        col_widths=widths,
        autofilter=read_autofilter(ws_f, ws_v) if PropertyGroup.FILTER in sheet_groups else None,
        page_setup=read_page_setup(ws_f) if PropertyGroup.PAGE_SETUP in sheet_groups else None,
        charts=read_charts(ws_f) if PropertyGroup.CHARTS in sheet_groups else (),
    )


def _read_cells(
    ws_f: Worksheet, ws_v: Worksheet, ranges: list[RangeRequest], palette: tuple[str, ...]
) -> dict[str, CellSnapshot]:
    groups_by_cell: dict[tuple[int, int], frozenset[PropertyGroup]] = {}
    for request in ranges:
        rng = parse_range(request.range)
        for row in rng.rows():
            for col in rng.cols():
                groups_by_cell[(row, col)] = groups_by_cell.get((row, col), frozenset()) | request.groups
    cells = {}
    for (row, col), groups in groups_by_cell.items():
        snapshot = _cell_snapshot(ws_f.cell(row, col), ws_v.cell(row, col), groups, palette)
        if snapshot != CellSnapshot():
            cells[cell_address(col, row)] = snapshot
    return cells


def _cell_snapshot(
    cell_f: Cell | MergedCell,
    cell_v: Cell | MergedCell,
    groups: frozenset[PropertyGroup],
    palette: tuple[str, ...],
) -> CellSnapshot:
    value: CellValue = None
    kind: ValueKind = "empty"
    formula = formula_r1c1 = None
    if PropertyGroup.VALUES in groups:
        value, kind = normalize_value(cell_v.value, cell_v.data_type)
    if PropertyGroup.FORMULAS in groups:
        formula, formula_r1c1 = _formula(cell_f)
    style = PropertyGroup.STYLE in groups
    return CellSnapshot(
        value=value,
        value_kind=kind,
        formula=formula,
        formula_r1c1=formula_r1c1,
        number_format=parse_number_format(cell_f.number_format)
        if PropertyGroup.NUMBER_FORMAT in groups
        else None,
        font=_font(cell_f, palette) if style else None,
        fill=FillInfo(_fill_color(cell_f, palette)) if style else None,
        border=_border(cell_f) if style else None,
        alignment=_alignment(cell_f) if style else None,
    )


def normalize_value(raw: object, data_type: str | None = None) -> tuple[CellValue, ValueKind]:
    """Giá trị Python của openpyxl → giá trị chuẩn hóa và loại (snapshot.md mục 5)."""
    if raw is None or raw == "":
        return None, "empty"
    if data_type == "e":
        return ErrorValue(str(raw)), "error"
    if isinstance(raw, bool):
        return raw, "logical"
    if isinstance(raw, int | float):
        return float(raw), "number"
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None), "date"
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day), "date"
    if isinstance(raw, time):
        return datetime.combine(EXCEL_EPOCH.date(), raw), "date"
    if isinstance(raw, timedelta):
        return EXCEL_EPOCH + raw, "date"
    return str(raw), "text"


def _formula(cell: Cell | MergedCell) -> tuple[str | None, str | None]:
    raw = cell.value
    if isinstance(raw, ArrayFormula):
        text = raw.text
    elif isinstance(raw, str) and cell.data_type == "f":
        text = raw
    else:
        return None, None
    if not text:
        return None, None
    try:
        return normalize_formula(text), to_r1c1(text, cell.row, cell.column)
    except FormulaError:
        logger.warning("Không phân tích được công thức ở %s: %r", cell.coordinate, text)
        return text, None


def _font(cell: Cell | MergedCell, palette: tuple[str, ...]) -> FontInfo:
    font = cell.font
    underline = font.u not in (None, "none")
    return FontInfo(
        name=font.name or "Calibri",
        size=float(font.sz or 11),
        bold=bool(font.b),
        italic=bool(font.i),
        underline=underline,
        color=resolve_color(font.color, palette, DEFAULT_FONT_COLOR) or DEFAULT_FONT_COLOR,
    )


def _fill_color(cell: Cell | MergedCell, palette: tuple[str, ...]) -> str | None:
    fill = cell.fill
    if getattr(fill, "patternType", None) in (None, "none"):
        stops = getattr(fill, "stop", None)
        return resolve_color(stops[0].color, palette, None) if stops else None
    return resolve_color(fill.fgColor, palette, None)


def _border(cell: Cell | MergedCell) -> BorderInfo:
    border = cell.border
    return BorderInfo(
        top=border.top.style if border.top else None,
        bottom=border.bottom.style if border.bottom else None,
        left=border.left.style if border.left else None,
        right=border.right.style if border.right else None,
    )


def _alignment(cell: Cell | MergedCell) -> AlignmentInfo:
    align = cell.alignment
    return AlignmentInfo(
        horizontal=_HORIZONTAL.get(align.horizontal, align.horizontal),
        vertical=_VERTICAL.get(align.vertical, align.vertical),
        wrap_text=bool(align.wrap_text),
    )


def display_column_width(file_width: float) -> float:
    """Độ rộng cột lưu trong file → số ký tự Excel hiển thị (9.140625 → 8.43)."""
    pixels = file_width * MAX_DIGIT_WIDTH_PX - COLUMN_PADDING_PX
    return max(0.0, int(pixels / MAX_DIGIT_WIDTH_PX * 100 + 0.5) / 100)


def _read_structure(
    ws: Worksheet, ranges: Iterable[CellRange]
) -> tuple[tuple[str, ...], frozenset[int], frozenset[str], dict[int, float], dict[str, float]]:
    ranges = list(ranges)
    if not ranges:
        return (), frozenset(), frozenset(), {}, {}
    rows = {r for rng in ranges for r in rng.rows()}
    cols = {c for rng in ranges for c in rng.cols()}
    merged = tuple(
        str(m.coord)
        for m in ws.merged_cells.ranges
        if any(parse_range(m.coord).intersects(r) for r in ranges)
    )
    hidden_rows = frozenset(r for r, dim in ws.row_dimensions.items() if dim.hidden and r in rows)
    default_height = float(ws.sheet_format.defaultRowHeight or 15)
    heights = {r: default_height for r in rows}
    for r, dim in ws.row_dimensions.items():
        if r in rows and dim.ht:
            heights[r] = float(dim.ht)
    default_width = (
        display_column_width(ws.sheet_format.defaultColWidth)
        if ws.sheet_format.defaultColWidth
        else float(ws.sheet_format.baseColWidth or 8) + 0.43
    )
    widths = {column_letter(c): default_width for c in cols}
    hidden_cols = set()
    for dim in ws.column_dimensions.values():
        for c in range(dim.min or 0, (dim.max or 0) + 1):
            if c not in cols:
                continue
            if dim.width:
                widths[column_letter(c)] = display_column_width(dim.width)
            if dim.hidden:
                hidden_cols.add(column_letter(c))
    # COM trả RowHeight/ColumnWidth = 0 cho dòng/cột ẩn: làm giống để hai bộ đọc cho cùng kết quả
    for r in hidden_rows:
        heights[r] = 0.0
    for c in hidden_cols:
        widths[c] = 0.0
    return merged, hidden_rows, frozenset(hidden_cols), heights, widths
