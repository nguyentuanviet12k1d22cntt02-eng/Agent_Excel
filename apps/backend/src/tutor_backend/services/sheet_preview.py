"""Xem trước trang tính cho lưới mô phỏng trên Web (T6.4): giáo viên thấy vùng mục tiêu, vùng nguồn,
vùng của từng điều kiện nằm ở đâu trong bài.

Chỉ để xem: chữ hiển thị là gần đúng (định dạng số kiểu Việt Nam: phân cách nghìn ".", thập phân ","),
không thay cho cách Excel hiển thị.
"""

import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from excel_core.address import CellRange, column_letter, parse_range
from excel_core.readers import read_workbook
from excel_core.snapshot import CELL_GROUPS, RangeRequest, ReadRequest
from excel_core.snapshot.model import CellSnapshot, ErrorValue, NumberFormatInfo, SheetSnapshot
from tutor_backend.core.errors import InvalidError
from tutor_backend.schemas.preview import PreviewCell, SheetPreview

MAX_ROWS = 200
MAX_COLS = 30
GENERAL_DIGITS = 10  # ô General: Excel hiện tối đa khoảng 10 chữ số có nghĩa
_CACHE_SIZE = 32


def _group_thousands(digits: str) -> str:
    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    return ".".join([digits, *groups]) if digits else ".".join(groups)


def format_number(value: float, decimals: int | None, thousands: bool) -> str:
    """Số theo kiểu Việt Nam. `decimals` None (General): bỏ số 0 thừa sau dấu phẩy."""
    if math.isnan(value) or math.isinf(value):
        return str(value)
    if decimals is None:
        text = f"{value:.{GENERAL_DIGITS}g}"  # "g" đã bỏ số 0 thừa
        if "e" in text:
            return text.replace(".", ",")
    else:
        text = f"{value:.{decimals}f}"
    sign = "-" if text.startswith("-") else ""
    whole, _, fraction = text.lstrip("-").partition(".")
    if thousands:
        whole = _group_thousands(whole)
    return sign + whole + ("," + fraction if fraction else "")


def _format_date(value: datetime, fmt: NumberFormatInfo | None) -> str:
    if fmt is not None and fmt.category == "time":
        return value.strftime("%H:%M:%S" if value.second else "%H:%M")
    if value.hour or value.minute or value.second:
        return value.strftime("%d/%m/%Y %H:%M")
    return value.strftime("%d/%m/%Y")


def display_text(cell: CellSnapshot) -> str:
    value = cell.value
    fmt = cell.number_format
    if value is None:
        return ""
    if isinstance(value, ErrorValue):
        return value.code
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return _format_date(value, fmt)
    if isinstance(value, float):
        if fmt is None or fmt.category in ("general", "text", "scientific", "fraction"):
            return format_number(value, None, thousands=False)
        if fmt.category == "percent":
            return format_number(value * 100, fmt.decimals or 0, thousands=False) + "%"
        return format_number(value, fmt.decimals or 0, fmt.thousands_separator)
    return value


def _preview_cell(address: str, cell: CellSnapshot) -> PreviewCell | None:
    text = display_text(cell)
    font, fill, alignment = cell.font, cell.fill, cell.alignment
    styled = (
        (font and (font.bold or font.italic)) or (fill and fill.color) or (alignment and alignment.wrap_text)
    )
    if not text and not cell.formula and not styled:
        return None
    return PreviewCell(
        address=address,
        text=text,
        formula=cell.formula,
        bold=bool(font and font.bold),
        italic=bool(font and font.italic),
        color=font.color if font and font.color not in ("#000000", None) else None,
        fill=fill.color if fill else None,
        align=alignment.horizontal if alignment and alignment.horizontal != "general" else None,
        number=cell.value_kind in ("number", "date"),
        wrap=bool(alignment and alignment.wrap_text),
    )


def _shown_range(ws: Worksheet) -> tuple[CellRange, bool]:
    """Vùng hiện: luôn từ A1 (giáo viên quen nhìn theo vị trí trên trang), tối đa MAX_ROWS x MAX_COLS."""
    used = parse_range(ws.calculate_dimension())
    shown = CellRange(1, 1, min(used.max_col, MAX_COLS), min(used.max_row, MAX_ROWS))
    return shown, used.max_row > MAX_ROWS or used.max_col > MAX_COLS


@lru_cache(maxsize=_CACHE_SIZE)
def _build(path: str, mtime_ns: int, sheet: str) -> SheetPreview:
    del mtime_ns  # chỉ để khóa cache: file đổi thì đọc lại
    workbook = openpyxl.load_workbook(path, read_only=False)
    try:
        if sheet not in workbook.sheetnames or not isinstance(workbook[sheet], Worksheet):
            raise InvalidError(
                f"File không có trang tính {sheet!r}",
                code="sheet_not_found",
                errors=[{"path": "/sheet", "message": f"có: {', '.join(workbook.sheetnames)}"}],
            )
        names = list(workbook.sheetnames)
        shown, truncated = _shown_range(workbook[sheet])
    finally:
        workbook.close()
    snapshot = read_workbook(path, ReadRequest((RangeRequest(sheet, str(shown), CELL_GROUPS),)))
    data: SheetSnapshot = snapshot.sheets[sheet]
    cells = [
        preview
        for address, cell in data.cells.items()
        if (preview := _preview_cell(address, cell)) is not None
    ]
    return SheetPreview(
        sheet=sheet,
        sheet_names=names,
        range=str(shown),
        rows=shown.max_row,
        cols=shown.max_col,
        truncated=truncated,
        cells=cells,
        merged=[m for m in data.merged if parse_range(m).intersects(shown)],
        col_widths={
            column_letter(c): data.col_widths[column_letter(c)]
            for c in shown.cols()
            if column_letter(c) in data.col_widths
        },
        row_heights={r: data.row_heights[r] for r in shown.rows() if r in data.row_heights},
        hidden_rows=sorted(r for r in data.hidden_rows if r <= shown.max_row),
        hidden_cols=sorted(c for c in data.hidden_cols if c in {column_letter(i) for i in shown.cols()}),
    )


def sheet_preview(path: Path, sheet: str) -> SheetPreview:
    return _build(str(path), path.stat().st_mtime_ns, sheet)
