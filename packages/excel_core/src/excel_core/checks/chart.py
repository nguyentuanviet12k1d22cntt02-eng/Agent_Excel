"""chart — có biểu đồ đúng loại, đúng vùng dữ liệu, có tiêu đề.

Vùng dữ liệu đạt khi `data_range` bằng vùng bao các tham chiếu của biểu đồ trên sheet đó, tính theo một
trong các cách: chỉ vùng giá trị; giá trị + tên chuỗi; giá trị + nhãn trục; tất cả. Người học chọn vùng có
hoặc không có dòng tiêu đề, cột nhãn đều tạo được cùng một biểu đồ.
"""

from collections.abc import Iterable

from excel_core.address import AddressError, CellRange, parse_range, split_sheet_reference
from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read, sheet_read
from excel_core.snapshot import ChartInfo, PropertyGroup

TYPE = "chart"
CODES = ("missing_chart", "wrong_chart_type", "wrong_data_range", "missing_title")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [sheet_read("current", sheet, PropertyGroup.CHARTS)]


def _bounding(refs: Iterable[str | None], sheet: str) -> CellRange | None:
    box: CellRange | None = None
    for ref in refs:
        if not ref:
            continue
        ref_sheet, address = split_sheet_reference(ref)
        if ref_sheet not in (None, sheet):
            return None
        try:
            rng = parse_range(address)
        except AddressError:
            return None
        box = rng if box is None else box.union(rng)
    return box


def _data_range_ok(chart: ChartInfo, wanted: CellRange, sheet: str) -> bool:
    values = [s.values_ref for s in chart.series]
    names = [s.name_ref for s in chart.series]
    categories = [s.categories_ref for s in chart.series]
    options = (values, values + names, values + categories, values + names + categories)
    return any(_bounding(option, sheet) == wanted for option in options)


def _problems(chart: ChartInfo, check: CheckSpec, sheet: str) -> list[str]:
    problems = []
    if "chart_types" in check and chart.chart_type not in check["chart_types"]:
        problems.append("wrong_chart_type")
    if "data_range" in check and not _data_range_ok(chart, parse_range(check["data_range"]), sheet):
        problems.append("wrong_data_range")
    wants_title = check.get("has_title") or "title_contains" in check
    title = chart.title
    if (wants_title and title is None) or (
        "title_contains" in check and check["title_contains"].casefold() not in (title or "").casefold()
    ):
        problems.append("missing_title")
    return problems


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    sheet = ctx.sheet(check)
    sheet.require_sheet_group(PropertyGroup.CHARTS)
    if not sheet.charts:
        return CheckResult.fail("missing_chart")
    # Nhiều biểu đồ: đạt nếu có một cái đạt; không thì báo theo cái gần đúng nhất
    best = min((_problems(chart, check, sheet.name) for chart in sheet.charts), key=len)
    return CheckResult.fail(best[0], detail=", ".join(best)) if best else CheckResult.ok()
