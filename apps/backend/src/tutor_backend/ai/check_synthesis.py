"""Suy ra điều kiện kiểm chứng từ một thay đổi đề → đáp án (tất định, không qua AI; T5.5).

Tham số lấy từ chính file đáp án (định dạng số, căn lề, hàm dùng...), nên điều kiện luôn đạt trên đáp án.
AI chỉ chia thay đổi thành bước và viết lời hướng dẫn: T2.6 cho thấy AI viết tham số điều kiện hay sai.
"""

import re
from typing import Any

from excel_core.address import CellRange, cell_address, parse_range
from excel_core.checks.alignment import effective_horizontal
from excel_core.checks.border import STYLE_FAMILIES
from excel_core.diff import Change, ChangeKind
from excel_core.formula import FormulaError, parse_formula
from excel_core.snapshot import NumberFormatInfo, SheetSnapshot, WorkbookSnapshot

type Check = dict[str, Any]

# Loại định dạng số được chấp nhận theo loại của đáp án (danh-muc-dieu-kien.md: so theo ý nghĩa)
NUMBER_FAMILIES: dict[str, list[str]] = {
    "number": ["number", "accounting"],
    "accounting": ["number", "accounting"],
    "currency": ["currency", "accounting"],
    "percent": ["percent"],
    "date": ["date"],
    "time": ["time"],
    "text": ["text"],
    "scientific": ["scientific"],
    "fraction": ["fraction"],
}
_NO_DECIMALS = {"date", "time", "text", "general"}
_SIDES = ("top", "bottom", "left", "right")


def _top_left(rng: CellRange) -> str:
    return cell_address(rng.min_col, rng.min_row)


def value_checks(rng: CellRange, solution: SheetSnapshot, source: CellRange | None) -> list[Check]:
    expected = {"from": "range", "range": str(source)} if source else {"from": "solution"}
    checks: list[Check] = [{"type": "value_equals", "range": str(rng), "expected": expected}]
    kinds = {solution.cell(address).value_kind for address in rng.cells()}
    if kinds in ({"number"}, {"date"}):
        # Bắt lỗi hay gặp: số/ngày gõ dạng chữ (stored_as_text)
        checks.append({"type": "value_type", "range": str(rng), "kind": kinds.pop()})
    return checks


def formula_functions(formula: str) -> list[str]:
    try:
        return sorted(set(parse_formula(formula).functions))
    except FormulaError:
        return []


def formula_checks(rng: CellRange, solution: SheetSnapshot) -> list[Check]:
    top = solution.cell(_top_left(rng))
    checks: list[Check] = [{"type": "is_formula", "range": str(rng)}]
    functions = formula_functions(top.formula or "")
    if functions:
        checks.append({"type": "formula_uses_function", "range": str(rng), "functions": functions})
    patterns = {solution.cell(a).formula_r1c1 for a in rng.cells()}
    if rng.size > 1 and len(patterns) == 1:
        checks.append({"type": "formula_consistent", "range": str(rng)})
    checks.append({"type": "value_equals", "range": str(rng), "expected": {"from": "solution"}})
    return checks


def number_format_check(rng: CellRange, info: NumberFormatInfo) -> list[Check]:
    check: Check = {"type": "number_format", "range": str(rng)}
    if info.category in NUMBER_FAMILIES:
        check["categories"] = NUMBER_FAMILIES[info.category]
    if info.decimals is not None and info.category not in _NO_DECIMALS:
        check["decimals"] = info.decimals
    if info.thousands_separator:
        check["thousands_separator"] = True
    if info.category == "date" and info.date_pattern and info.date_pattern != "short_date":
        check["date_pattern"] = info.date_pattern
    return [check] if len(check) > 2 else []


def alignment_check(rng: CellRange, starter: SheetSnapshot, solution: SheetSnapshot) -> list[Check]:
    address = _top_left(rng)
    before, after = starter.cell(address).alignment, solution.cell(address).alignment
    if after is None:
        return []
    check: Check = {"type": "alignment", "range": str(rng)}
    if after.horizontal != "general":
        check["horizontal"] = [effective_horizontal(solution.cell(address))]
    if before is None or before.vertical != after.vertical:
        check["vertical"] = [after.vertical]
    if before is None or before.wrap_text != after.wrap_text:
        check["wrap_text"] = after.wrap_text
    return [check] if len(check) > 2 else []


def font_check(rng: CellRange, starter: SheetSnapshot, solution: SheetSnapshot) -> list[Check]:
    address = _top_left(rng)
    before, after = starter.cell(address).font, solution.cell(address).font
    if before is None or after is None:
        return []
    check: Check = {"type": "font", "range": str(rng)}
    for attr in ("bold", "italic", "underline", "size", "name", "color"):
        if getattr(before, attr) != getattr(after, attr):
            check[attr] = getattr(after, attr)
    return [check] if len(check) > 2 else []


def _edge(sheet: SheetSnapshot, col: int, row: int, side: str) -> str | None:
    border = sheet.cell(cell_address(col, row)).border
    return getattr(border, side) if border is not None else None


def border_check(rng: CellRange, solution: SheetSnapshot) -> list[Check]:
    every_side = all(
        _edge(solution, col, row, side) for row in rng.rows() for col in rng.cols() for side in _SIDES
    )
    sides = ["outline", "inside"] if every_side and rng.size > 1 else ["outline"]
    style = _edge(solution, rng.min_col, rng.min_row, "top") or "any"
    family = next((name for name, members in STYLE_FAMILIES.items() if style in members), "any")
    return [{"type": "border", "range": str(rng), "sides": sides, "style": family}]


def line_check(change: Change) -> list[Check]:
    """Dòng/cột ẩn hiện, kích thước. `change.range` dạng "5:7" hoặc "C:D"."""
    span = change.range or ""
    first = span.split(":")[0]
    axis = "rows" if first.isdigit() else "cols"
    value = span if span.split(":")[0] != span.split(":")[-1] else first
    if change.kind in (ChangeKind.ROW_HIDDEN, ChangeKind.COL_HIDDEN):
        return [{"type": "row_col_hidden", axis: value, "hidden": change.after == "ẩn"}]
    try:
        size = float(change.after)
    except ValueError:
        return []
    return [{"type": "row_col_size", axis: value, "equals": size}]


def sheet_object_checks(
    kind: ChangeKind, sheet: str, starter: WorkbookSnapshot, solution: WorkbookSnapshot
) -> list[Check]:
    """Bộ lọc, trang in, biểu đồ, thêm sheet: so đối tượng của sheet trên hai file."""
    if kind == ChangeKind.SHEET_ADDED:
        return [{"type": "sheet_exists", "name_pattern": re.escape(sheet)}]
    after = solution.sheets.get(sheet)
    before = starter.sheets.get(sheet)
    if after is None or before is None:
        return []
    if kind == ChangeKind.AUTOFILTER:
        return _autofilter_checks(after)
    if kind == ChangeKind.PAGE_SETUP:
        return _page_checks(before, after)
    if kind == ChangeKind.CHART:
        return _chart_checks(before, after)
    return []


def _autofilter_checks(after: SheetSnapshot) -> list[Check]:
    info = after.autofilter
    if info is None:
        return []
    check: Check = {"type": "autofilter", "range": info.range}
    if len(info.columns) == 1:
        (column, criteria), *_ = info.columns.items()
        check["column"] = column
        if criteria:
            check["criteria"] = list(criteria)
    checks = [check]
    table = parse_range(info.range)
    if any(table.min_row < row <= table.max_row for row in after.hidden_rows):
        checks.append({"type": "visible_rows", "range": info.range, "expected": {"from": "solution"}})
    return checks


def _page_checks(before: SheetSnapshot, after: SheetSnapshot) -> list[Check]:
    old, new = before.page_setup, after.page_setup
    if old is None or new is None:
        return []
    check: Check = {"type": "page_setup"}
    for field in ("orientation", "paper_size", "center_horizontally", "print_area"):
        if getattr(old, field) != getattr(new, field) and getattr(new, field) is not None:
            check[field] = getattr(new, field)
    if old.fit_to_pages != new.fit_to_pages:
        wide, tall = new.fit_to_pages
        if wide:
            check["fit_to_pages_wide"] = wide
        if tall:
            check["fit_to_pages_tall"] = tall
    if old.margins_cm != new.margins_cm:
        check["margins_cm"] = dict(zip(("top", "bottom", "left", "right"), new.margins_cm, strict=True))
    checks = [check] if len(check) > 1 else []
    for position, text in new.header_footer.items():
        if old.header_footer.get(position) != text:
            contains = "&P" if "&p" in text.lower() else text
            checks.append({"type": "header_footer", "position": position, "contains": contains})
    return checks


def _chart_checks(before: SheetSnapshot, after: SheetSnapshot) -> list[Check]:
    checks = []
    for chart in after.charts:
        if chart in before.charts:
            continue
        check: Check = {"type": "chart"}
        if chart.chart_type != "other":
            check["chart_types"] = [chart.chart_type]
        refs = [r for s in chart.series for r in (s.values_ref, s.categories_ref, s.name_ref) if r]
        boxes = [parse_range(r.split("!")[-1]) for r in refs if r.split("!")[0] in (after.name, r)]
        if boxes:
            box = boxes[0]
            for other in boxes[1:]:
                box = box.union(other)
            check["data_range"] = str(box)
        if chart.title is not None:
            check["has_title"] = True
        checks.append(check)
    return checks


def cell_change_checks(
    change: Change, rng: CellRange, starter: SheetSnapshot, solution: SheetSnapshot, source: CellRange | None
) -> list[Check]:
    """Điều kiện cho một thay đổi trên vùng ô."""
    match change.kind:
        case ChangeKind.VALUE:
            return value_checks(rng, solution, source)
        case ChangeKind.FORMULA:
            return formula_checks(rng, solution)
        case ChangeKind.NUMBER_FORMAT:
            info = solution.cell(_top_left(rng)).number_format
            return number_format_check(rng, info) if info else []
        case ChangeKind.ALIGNMENT:
            return alignment_check(rng, starter, solution)
        case ChangeKind.FONT:
            return font_check(rng, starter, solution)
        case ChangeKind.FILL:
            return [{"type": "fill", "range": str(rng), "color": "any"}]
        case ChangeKind.BORDER:
            return border_check(rng, solution)
        case ChangeKind.MERGED:
            return [{"type": "merged", "range": str(rng)}]
    return []
