"""Đọc các đối tượng theo sheet bằng openpyxl: bộ lọc, thiết lập trang in, biểu đồ (T2.3 đã thử)."""

import logging

from openpyxl.worksheet.worksheet import Worksheet

from excel_core.address import cell_address, parse_range, split_sheet_reference
from excel_core.snapshot import AutoFilterInfo, ChartInfo, ChartSeriesInfo, PageSetupInfo

logger = logging.getLogger(__name__)

CM_PER_INCH = 2.54
PAPER_SIZES = {1: "letter", 5: "legal", 8: "A3", 9: "A4", 11: "A5"}
_OPERATORS = {
    None: "",
    "equal": "",
    "notEqual": "<>",
    "lessThan": "<",
    "lessThanOrEqual": "<=",
    "greaterThan": ">",
    "greaterThanOrEqual": ">=",
}
_CHART_TYPES = {
    "LineChart": "line",
    "LineChart3D": "line",
    "PieChart": "pie",
    "PieChart3D": "pie",
    "ProjectedPieChart": "pie",
    "DoughnutChart": "doughnut",
    "AreaChart": "area",
    "AreaChart3D": "area",
    "ScatterChart": "scatter",
}
_HEADER_FOOTER_PARTS = ("left", "center", "right")


def _criterion(text: object) -> str:
    """Tiêu chí lọc chuẩn hóa: bỏ dấu "=" đầu như COM trả (T2.3)."""
    value = str(text).strip()
    return value[1:] if value.startswith("=") and not value.startswith("==") else value


def _filter_criteria(column: object) -> tuple[str, ...]:
    criteria: list[str] = []
    filters = getattr(column, "filters", None)
    if filters is not None:
        criteria += [_criterion(v) for v in filters.filter]
        if filters.blank:
            criteria.append("(blank)")
    custom = getattr(column, "customFilters", None)
    if custom is not None:
        for item in custom.customFilter:
            criteria.append(_OPERATORS.get(item.operator, item.operator or "") + _criterion(item.val))
    top10 = getattr(column, "top10", None)
    if top10 is not None:
        criteria.append(
            f"{'bottom' if not top10.top else 'top'}{int(top10.val)}{'%' if top10.percent else ''}"
        )
    dynamic = getattr(column, "dynamicFilter", None)
    if dynamic is not None:
        criteria.append(f"dynamic:{dynamic.type}")
    return tuple(criteria)


def read_autofilter(ws_formulas: Worksheet, ws_values: Worksheet) -> AutoFilterInfo | None:
    """Bộ lọc của sheet (hoặc của bảng đầu tiên có lọc). Cột theo tiêu đề (quy tắc code 2.3 mục 9)."""
    auto_filter = ws_formulas.auto_filter
    if not auto_filter.ref:
        auto_filter = next(
            (t.autoFilter for t in ws_formulas.tables.values() if t.autoFilter is not None), None
        )
        if auto_filter is None or not auto_filter.ref:
            return None
    rng = parse_range(auto_filter.ref)
    columns = {}
    for column in auto_filter.filterColumn:
        col = rng.min_col + int(column.colId)
        header = ws_values.cell(rng.min_row, col).value
        title = str(header).strip() if header not in (None, "") else cell_address(col, rng.min_row)
        columns[title] = _filter_criteria(column)
    return AutoFilterInfo(str(rng), columns)


def _print_area(ws: Worksheet) -> str | None:
    area = ws.print_area
    if not area:
        return None
    first = area.split(",")[0] if isinstance(area, str) else area[0]
    return str(parse_range(split_sheet_reference(first)[1]))


def _fit_to_pages(ws: Worksheet) -> tuple[int | None, int | None]:
    properties = ws.sheet_properties.pageSetUpPr
    if properties is None or not properties.fitToPage:
        return None, None
    wide, tall = ws.page_setup.fitToWidth, ws.page_setup.fitToHeight
    # Trong file, 0 là "tự động" (không ép); bỏ trống là mặc định 1 trang
    return (1 if wide is None else (int(wide) or None)), (1 if tall is None else (int(tall) or None))


def _header_footer(ws: Worksheet) -> dict[str, str]:
    parts = {}
    for kind, item in (("header", ws.oddHeader), ("footer", ws.oddFooter)):
        for position in _HEADER_FOOTER_PARTS:
            text = getattr(item, position).text
            if text:
                parts[f"{kind}_{position}"] = text
    return parts


def read_page_setup(ws: Worksheet) -> PageSetupInfo:
    setup, margins = ws.page_setup, ws.page_margins
    paper = PAPER_SIZES.get(int(setup.paperSize)) if setup.paperSize else None
    return PageSetupInfo(
        orientation="landscape" if setup.orientation == "landscape" else "portrait",
        paper_size=paper,
        margins_cm=tuple(  # type: ignore[arg-type]
            round(float(m) * CM_PER_INCH, 2)
            for m in (margins.top, margins.bottom, margins.left, margins.right)
        ),
        fit_to_pages=_fit_to_pages(ws),
        center_horizontally=bool(ws.print_options.horizontalCentered),
        print_area=_print_area(ws),
        header_footer=_header_footer(ws),
    )


def _chart_type(chart: object) -> str:
    name = type(chart).__name__
    if name in ("BarChart", "BarChart3D"):
        return "bar" if getattr(chart, "barDir", "col") == "bar" else "column"
    return _CHART_TYPES.get(name, "other")


def _ref(reference: object) -> str | None:
    formula = getattr(reference, "f", None)
    if not formula:
        return None
    sheet, address = split_sheet_reference(formula)
    return f"{sheet}!{address}" if sheet else address


def _series_ref(source: object) -> str | None:
    """Tham chiếu của tx / cat / val (numRef, strRef hoặc multiLvlStrRef)."""
    if source is None:
        return None
    for attr in ("numRef", "strRef", "multiLvlStrRef"):
        ref = _ref(getattr(source, attr, None))
        if ref:
            return ref
    return None


def _cached_text(source: object) -> str | None:
    cache = getattr(getattr(source, "strRef", None), "strCache", None)
    points = getattr(cache, "pt", None)
    return str(points[0].v) if points else None


def _chart_title(chart: object) -> str | None:
    title = getattr(chart, "title", None)
    if title is None:
        return None
    rich = getattr(getattr(title, "tx", None), "rich", None)
    if rich is not None:
        return "".join(run.t for paragraph in rich.p for run in (paragraph.r or []))
    linked = _cached_text(getattr(title, "tx", None))
    if linked is not None:
        return linked
    # Có tiêu đề nhưng không ghi chữ: Excel tự lấy tên chuỗi dữ liệu duy nhất
    series = list(getattr(chart, "series", []))
    return (_cached_text(series[0].tx) or "") if len(series) == 1 else ""


def read_charts(ws: Worksheet) -> tuple[ChartInfo, ...]:
    charts = []
    for chart in ws._charts:  # openpyxl chỉ cho truy cập qua thuộc tính nội bộ này
        series = tuple(
            ChartSeriesInfo(
                name_ref=_series_ref(s.tx),
                categories_ref=_series_ref(s.cat) or _series_ref(getattr(s, "xVal", None)),
                values_ref=_series_ref(s.val) or _series_ref(getattr(s, "yVal", None)),
            )
            for s in chart.series
        )
        charts.append(ChartInfo(_chart_type(chart), _chart_title(chart), series))
    return tuple(charts)
