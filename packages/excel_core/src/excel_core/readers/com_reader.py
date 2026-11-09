"""Đọc workbook đang mở trong Excel qua COM thành WorkbookSnapshot (Desktop, T7.2). Thiết kế: snapshot.md.

Cho ra cùng kết quả với bộ đọc openpyxl (test so khớp trên các bài mẫu), để điều kiện kiểm chấm giống nhau ở
Backend (tự kiểm trên file) và Desktop (bài học viên đang làm).

- Không import win32com ở mức module: Backend chạy trên Linux vẫn import được `excel_core`
  (cau-truc-thu-muc.md mục 4). Hàm nhận đối tượng Workbook COM do Desktop đưa vào.
- Chỉ đọc, không bao giờ ghi vào workbook của học viên (NFR-06).
- Mã định dạng số đọc bằng LCID 1033 (en-US): theo cài đặt vùng vi-VN, Excel dịch "#,##0" thành "#.##0"
  (quy tắc code 2.3 mục 6).
- Đọc theo vùng: giá trị, công thức cả vùng một lần; định dạng thử đọc cả vùng trước (Excel trả None khi các ô
  khác nhau) rồi mới đọc từng ô, vì đọc định dạng từng ô chậm (~2 ms/ô, T2.1).
- Excel đang bận (học viên đang sửa ô, mở hộp thoại) thì COM ném lỗi; nơi gọi tự thử lại (quy tắc code 2.3
  mục 2), bộ đọc không thử lại.
"""

import logging
from collections.abc import Callable, Iterator
from datetime import datetime
from decimal import Decimal
from typing import Any

from excel_core.address import CellRange, cell_address, column_letter, parse_range, split_sheet_reference
from excel_core.formula import FormulaError, normalize_formula, to_r1c1
from excel_core.readers.openpyxl_objects import CM_PER_INCH, PAPER_SIZES
from excel_core.readers.openpyxl_reader import DEFAULT_FONT_COLOR, EXERCISE_ID_PROPERTY
from excel_core.snapshot import (
    CELL_GROUPS,
    SHEET_GROUPS,
    AlignmentInfo,
    AutoFilterInfo,
    BorderInfo,
    CellSnapshot,
    CellValue,
    ChartInfo,
    ChartSeriesInfo,
    ErrorValue,
    FillInfo,
    FontInfo,
    PageSetupInfo,
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

type Com = Any  # đối tượng COM gọi trễ (late binding) của pywin32

LCID_EN_US = 1033
POINTS_PER_INCH = 72
XL_NONE = -4142
XL_EDGES = {"left": 7, "top": 8, "bottom": 9, "right": 10}
XL_CONTINUOUS, XL_DOUBLE, XL_DASH, XL_DOT, XL_DASH_DOT, XL_DASH_DOT_DOT, XL_SLANT_DASH_DOT = (
    1,
    -4119,
    -4115,
    -4118,
    4,
    5,
    13,
)
XL_HAIRLINE, XL_THIN, XL_MEDIUM, XL_THICK = 1, 2, -4138, 4
_HORIZONTAL = {
    1: "general",
    -4131: "left",
    -4108: "center",
    -4152: "right",
    5: "fill",
    -4130: "justify",
    7: "center_across",
    -4117: "distributed",
}
_VERTICAL = {-4160: "top", -4108: "center", -4107: "bottom", -4130: "justify", -4117: "distributed"}
# Mã lỗi COM (CVErr) → chữ lỗi như trong ô
_ERRORS = {
    -2146826281: "#DIV/0!",
    -2146826246: "#N/A",
    -2146826259: "#NAME?",
    -2146826288: "#NULL!",
    -2146826252: "#NUM!",
    -2146826265: "#REF!",
    -2146826273: "#VALUE!",
    -2146824224: "#GETTING_DATA",
    -2146826236: "#SPILL!",
    -2146826225: "#CALC!",
}
_CHART_KINDS = {
    "column": {51, 52, 53, 54, 55, 56, -4100},
    "bar": {57, 58, 59, 60, 61, 62},
    "line": {4, 63, 64, 65, 66, 67, -4101},
    "pie": {5, 68, 69, 70, 71, -4102},
    "doughnut": {-4120, 80},
    "area": {1, 76, 77, -4098, 78, 79},
    "scatter": {-4169, 72, 73, 74, 75},
}
_HEADER_FOOTER = {
    "header_left": "LeftHeader",
    "header_center": "CenterHeader",
    "header_right": "RightHeader",
    "footer_left": "LeftFooter",
    "footer_center": "CenterFooter",
    "footer_right": "RightFooter",
}


# ---------------------------------------------------------------- tiện ích COM
def get_en_us(obj: Com, name: str) -> Any:
    """Đọc thuộc tính theo LCID 1033 (pywin32 mặc định dùng cài đặt vùng của máy)."""
    import pythoncom  # noqa: PLC0415 — chỉ có trên Windows, không import ở mức module

    dispid = obj._oleobj_.GetIDsOfNames(name)
    return obj._oleobj_.Invoke(dispid, LCID_EN_US, pythoncom.DISPATCH_PROPERTYGET, True)


def _grid(raw: Any, rows: int, cols: int) -> list[list[Any]]:
    """Giá trị COM của một vùng → mảng 2 chiều (vùng 1 ô thì COM trả giá trị đơn)."""
    if rows == 1 and cols == 1 and not isinstance(raw, tuple):
        return [[raw]]
    return [list(row) for row in raw]


def _address(rng: Com) -> str:
    return str(rng.Address).replace("$", "")


def _hex_color(bgr: Any) -> str:
    value = int(bgr)
    return f"#{value & 0xFF:02X}{(value >> 8) & 0xFF:02X}{(value >> 16) & 0xFF:02X}"


def normalize_com_value(raw: Any) -> tuple[CellValue, ValueKind]:
    """Giá trị COM (Range.Value) → giá trị chuẩn hóa như bộ đọc openpyxl.

    Số luôn về float; lỗi công thức COM trả số nguyên (CVErr); ô định dạng tiền tệ trả Decimal; ngày trả
    pywintypes.datetime có múi giờ.
    """
    if raw is None or raw == "":
        return None, "empty"
    if isinstance(raw, bool):
        return raw, "logical"
    if isinstance(raw, int):
        return ErrorValue(_ERRORS.get(raw, f"#ERR{raw}")), "error"
    if isinstance(raw, float | Decimal):
        return float(raw), "number"
    if isinstance(raw, datetime):
        return datetime(raw.year, raw.month, raw.day, raw.hour, raw.minute, raw.second), "date"
    return str(raw), "text"


def _formula(text: Any, row: int, col: int) -> tuple[str | None, str | None]:
    if not isinstance(text, str) or not text.startswith("="):
        return None, None
    try:
        return normalize_formula(text), to_r1c1(text, row, col)
    except FormulaError:
        logger.warning("Không phân tích được công thức ở %s: %r", cell_address(col, row), text)
        return text, None


# ---------------------------------------------------------------- định dạng ô
def _uniform(
    rng: Com, cells: list[tuple[int, int]], read: Callable[[Com], Any]
) -> dict[tuple[int, int], Any]:
    """Một thuộc tính cho mọi ô của vùng: đọc cả vùng một lần, khác nhau (None) thì đọc từng ô."""
    whole = read(rng)
    if whole is not None:
        return dict.fromkeys(cells, whole)
    sheet = rng.Worksheet
    return {(row, col): read(sheet.Cells(row, col)) for row, col in cells}


def _border_style(border: Com) -> str | None:
    style, weight = border.LineStyle, border.Weight
    if style in (None, XL_NONE):
        return None
    if style == XL_CONTINUOUS:
        return {XL_HAIRLINE: "hair", XL_MEDIUM: "medium", XL_THICK: "thick"}.get(weight, "thin")
    medium = weight in (XL_MEDIUM, XL_THICK)
    names = {
        XL_DOUBLE: "double",
        XL_DOT: "dotted",
        XL_DASH: "mediumDashed" if medium else "dashed",
        XL_DASH_DOT: "mediumDashDot" if medium else "dashDot",
        XL_DASH_DOT_DOT: "mediumDashDotDot" if medium else "dashDotDot",
        XL_SLANT_DASH_DOT: "slantDashDot",
    }
    return names.get(style, "thin")


def _style_fields(rng: Com, cells: list[tuple[int, int]]) -> dict[tuple[int, int], dict[str, Any]]:
    names = _uniform(rng, cells, lambda r: r.Font.Name)
    sizes = _uniform(rng, cells, lambda r: r.Font.Size)
    bold = _uniform(rng, cells, lambda r: r.Font.Bold)
    italic = _uniform(rng, cells, lambda r: r.Font.Italic)
    underline = _uniform(rng, cells, lambda r: r.Font.Underline)
    colors = _uniform(rng, cells, lambda r: r.Font.Color)
    patterns = _uniform(rng, cells, lambda r: r.Interior.Pattern)
    horizontal = _uniform(rng, cells, lambda r: r.HorizontalAlignment)
    vertical = _uniform(rng, cells, lambda r: r.VerticalAlignment)
    wrap = _uniform(rng, cells, lambda r: r.WrapText)
    sheet = rng.Worksheet
    fields: dict[tuple[int, int], dict[str, Any]] = {}
    for row, col in cells:
        cell = sheet.Cells(row, col)
        fill = None if patterns[(row, col)] == XL_NONE else _hex_color(cell.Interior.Color)
        borders = {side: _border_style(cell.Borders(index)) for side, index in XL_EDGES.items()}
        fields[(row, col)] = {
            "font": FontInfo(
                name=str(names[(row, col)] or "Calibri"),
                size=float(sizes[(row, col)] or 11),
                bold=bool(bold[(row, col)]),
                italic=bool(italic[(row, col)]),
                underline=underline[(row, col)] not in (None, XL_NONE),
                color=_hex_color(colors[(row, col)])
                if colors[(row, col)] is not None
                else DEFAULT_FONT_COLOR,
            ),
            "fill": FillInfo(fill),
            "border": BorderInfo(**borders),
            "alignment": AlignmentInfo(
                horizontal=_HORIZONTAL.get(horizontal[(row, col)], "general"),
                vertical=_VERTICAL.get(vertical[(row, col)], "bottom"),
                wrap_text=bool(wrap[(row, col)]),
            ),
        }
    return fields


# ---------------------------------------------------------------- vùng ô
def _cells(rng: CellRange) -> list[tuple[int, int]]:
    return [(row, col) for row in rng.rows() for col in rng.cols()]


def _read_range(ws: Com, request: RangeRequest) -> dict[tuple[int, int], dict[str, Any]]:
    """Các trường của từng ô trong một vùng (theo nhóm thuộc tính được yêu cầu)."""
    box = parse_range(request.range)
    rng = ws.Range(str(box))
    cells = _cells(box)
    fields: dict[tuple[int, int], dict[str, Any]] = {cell: {} for cell in cells}
    groups = request.groups
    if PropertyGroup.VALUES in groups:
        values = _grid(rng.Value, box.height, box.width)
        for row, col in cells:
            value, kind = normalize_com_value(values[row - box.min_row][col - box.min_col])
            fields[(row, col)] |= {"value": value, "value_kind": kind}
    if PropertyGroup.FORMULAS in groups:
        formulas = _grid(rng.Formula, box.height, box.width)
        for row, col in cells:
            formula, r1c1 = _formula(formulas[row - box.min_row][col - box.min_col], row, col)
            fields[(row, col)] |= {"formula": formula, "formula_r1c1": r1c1}
    if PropertyGroup.NUMBER_FORMAT in groups:
        codes = _uniform(rng, cells, lambda r: get_en_us(r, "NumberFormat"))
        for cell in cells:
            fields[cell]["number_format"] = parse_number_format(str(codes[cell] or "General"))
    if PropertyGroup.STYLE in groups:
        for cell, style in _style_fields(rng, cells).items():
            fields[cell] |= style
    return fields


def _structure(ws: Com, ranges: list[CellRange]) -> dict[str, Any]:
    if not ranges:
        return {}
    rows = sorted({r for rng in ranges for r in rng.rows()})
    cols = sorted({c for rng in ranges for c in rng.cols()})
    merged: set[str] = set()
    for rng in ranges:
        if ws.Range(str(rng)).MergeCells is False:
            continue
        for row, col in _cells(rng):
            cell = ws.Cells(row, col)
            if cell.MergeCells:
                merged.add(_address(cell.MergeArea))
    hidden_rows = frozenset(r for r in rows if ws.Rows(r).Hidden)
    hidden_cols = frozenset(column_letter(c) for c in cols if ws.Columns(c).Hidden)
    # Dòng/cột ẩn: COM trả kích thước 0 (bộ đọc openpyxl làm giống)
    heights = {r: 0.0 if r in hidden_rows else float(ws.Rows(r).RowHeight) for r in rows}
    widths = {
        column_letter(c): 0.0
        if column_letter(c) in hidden_cols
        else round(float(ws.Columns(c).ColumnWidth), 2)
        for c in cols
    }
    return {
        "merged": tuple(sorted(merged)),
        "hidden_rows": hidden_rows,
        "hidden_cols": hidden_cols,
        "row_heights": heights,
        "col_widths": widths,
    }


# ---------------------------------------------------------------- đối tượng theo sheet
def _criterion(text: Any) -> str:
    value = str(text).strip()
    return value[1:] if value.startswith("=") and not value.startswith("==") else value


def _read_autofilter(ws: Com) -> AutoFilterInfo | None:
    if not ws.AutoFilterMode or ws.AutoFilter is None:
        return None
    auto = ws.AutoFilter
    box = parse_range(_address(auto.Range))
    columns: dict[str, tuple[str, ...]] = {}
    for index in range(1, auto.Filters.Count + 1):
        item = auto.Filters(index)
        if not item.On:
            continue
        col = box.min_col + index - 1
        header = ws.Cells(box.min_row, col).Value
        title = str(header).strip() if header not in (None, "") else cell_address(col, box.min_row)
        criteria: list[str] = []
        for raw in (item.Criteria1, _optional(lambda f=item: f.Criteria2)):
            if raw is None:
                continue
            criteria += [_criterion(v) for v in raw] if isinstance(raw, tuple) else [_criterion(raw)]
        columns[title] = tuple(criteria)
    return AutoFilterInfo(str(box), columns)


def _optional(read: Callable[[], Any]) -> Any:
    """Thuộc tính COM có thể không tồn tại ở trạng thái hiện tại (ví dụ Criteria2 khi chỉ có 1 tiêu chí)."""
    import pywintypes  # noqa: PLC0415

    try:
        return read()
    except pywintypes.com_error:
        return None


def _read_page_setup(ws: Com) -> PageSetupInfo:
    setup = ws.PageSetup

    def cm(points: Any) -> float:
        return round(float(points) / POINTS_PER_INCH * CM_PER_INCH, 2)

    fit: tuple[int | None, int | None] = (None, None)
    if setup.Zoom is False:
        fit = (int(setup.FitToPagesWide) or None, int(setup.FitToPagesTall) or None)
    area = str(setup.PrintArea or "")
    print_area = str(parse_range(split_sheet_reference(area.split(",")[0])[1])) if area else None
    return PageSetupInfo(
        orientation="landscape" if setup.Orientation == 2 else "portrait",  # noqa: PLR2004 — xlLandscape
        paper_size=PAPER_SIZES.get(int(setup.PaperSize)),
        margins_cm=(cm(setup.TopMargin), cm(setup.BottomMargin), cm(setup.LeftMargin), cm(setup.RightMargin)),
        fit_to_pages=fit,
        center_horizontally=bool(setup.CenterHorizontally),
        print_area=print_area,
        header_footer={
            key: text for key, prop in _HEADER_FOOTER.items() if (text := str(getattr(setup, prop) or ""))
        },
    )


def _series_args(formula: str) -> list[str]:
    """Đối số của =SERIES(tên, danh mục, giá trị, thứ tự), tách theo dấu phẩy ngoài nháy và ngoặc."""
    body = formula.strip()
    body = body[body.find("(") + 1 : body.rfind(")")]
    args, depth, quoted, current = [], 0, False, ""
    for ch in body:
        if ch == "'":
            quoted = not quoted
        elif ch == "(" and not quoted:
            depth += 1
        elif ch == ")" and not quoted:
            depth -= 1
        if ch == "," and depth == 0 and not quoted:
            args.append(current)
            current = ""
        else:
            current += ch
    args.append(current)
    return args


def _ref(text: str) -> str | None:
    text = text.strip()
    if not text or text.startswith('"') or "!" not in text:
        return None
    sheet, address = split_sheet_reference(text)
    return f"{sheet}!{address.replace('$', '')}" if sheet else address.replace("$", "")


def _chart_kind(code: int) -> str:
    return next((kind for kind, codes in _CHART_KINDS.items() if code in codes), "other")


def _read_charts(ws: Com) -> tuple[ChartInfo, ...]:
    charts = []
    for index in range(1, ws.ChartObjects().Count + 1):
        chart = ws.ChartObjects(index).Chart
        title = str(chart.ChartTitle.Text) if chart.HasTitle else None
        series = []
        for s in range(1, chart.SeriesCollection().Count + 1):
            args = _series_args(str(chart.SeriesCollection(s).Formula)) + ["", "", ""]
            series.append(ChartSeriesInfo(_ref(args[0]), _ref(args[1]), _ref(args[2])))
        charts.append(ChartInfo(_chart_kind(int(chart.ChartType)), title, tuple(series)))
    return tuple(charts)


# ---------------------------------------------------------------- trang tính, workbook
def _read_sheet(ws: Com, ranges: list[RangeRequest], sheet_groups: frozenset[PropertyGroup]) -> SheetSnapshot:
    fields: dict[tuple[int, int], dict[str, Any]] = {}
    for request in ranges:
        for cell, values in _read_range(ws, request).items():
            fields.setdefault(cell, {}).update(values)
    cells = {}
    for (row, col), values in fields.items():
        snapshot = CellSnapshot(**values)
        if snapshot != CellSnapshot():
            cells[cell_address(col, row)] = snapshot
    structure = _structure(ws, [parse_range(r.range) for r in ranges if PropertyGroup.STRUCTURE in r.groups])
    return SheetSnapshot(
        name=str(ws.Name),
        cells=cells,
        read_ranges=tuple(RangeRead(str(parse_range(r.range)), r.groups) for r in ranges),
        sheet_groups=sheet_groups,
        autofilter=_read_autofilter(ws) if PropertyGroup.FILTER in sheet_groups else None,
        page_setup=_read_page_setup(ws) if PropertyGroup.PAGE_SETUP in sheet_groups else None,
        charts=_read_charts(ws) if PropertyGroup.CHARTS in sheet_groups else (),
        **structure,
    )


def _worksheets(workbook: Com) -> Iterator[Com]:
    for index in range(1, workbook.Worksheets.Count + 1):
        yield workbook.Worksheets(index)


def full_request_com(workbook: Com) -> ReadRequest:
    """Như `full_request` của bộ đọc openpyxl: vùng đang dùng của mọi trang tính, mọi nhóm thuộc tính."""
    ranges, sheets = [], []
    for ws in _worksheets(workbook):
        ranges.append(RangeRequest(str(ws.Name), _address(ws.UsedRange), CELL_GROUPS))
        sheets.append(SheetRequest(str(ws.Name), SHEET_GROUPS))
    return ReadRequest(tuple(ranges), tuple(sheets))


def _exercise_id(workbook: Com) -> str | None:
    properties = workbook.CustomDocumentProperties
    for index in range(1, properties.Count + 1):
        prop = properties(index)
        if prop.Name == EXERCISE_ID_PROPERTY:
            return str(prop.Value)
    return None


def read_workbook_com(workbook: Com, request: ReadRequest | None = None) -> WorkbookSnapshot:
    """Đọc workbook COM theo yêu cầu đọc; không có yêu cầu thì đọc mọi thứ (`full_request_com`)."""
    request = request or full_request_com(workbook)
    names = [str(workbook.Sheets(i).Name) for i in range(1, workbook.Sheets.Count + 1)]
    worksheet_names = {str(ws.Name) for ws in _worksheets(workbook)}
    sheets = {}
    for name in request.sheet_names:
        if name not in worksheet_names:
            logger.debug("Bỏ qua sheet %r: không có hoặc không phải trang tính", name)
            continue
        ranges = [r for r in request.ranges if r.sheet == name]
        sheets[name] = _read_sheet(workbook.Worksheets(name), ranges, request.sheet_groups(name))
    active = workbook.ActiveSheet
    return WorkbookSnapshot(
        source="com",
        taken_at=datetime.now(),
        exercise_id=_exercise_id(workbook),
        sheet_names=tuple(names),
        active_sheet=str(active.Name) if active is not None else None,
        sheets=sheets,
    )
