"""autofilter — bộ lọc đang bật trên bảng, đúng cột (theo tiêu đề), đúng tiêu chí."""

from excel_core.address import parse_range
from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read, check_range, sheet_read
from excel_core.checks.table import normalize_header
from excel_core.snapshot import PropertyGroup

TYPE = "autofilter"
CODES = ("no_filter", "wrong_column", "wrong_criteria")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [sheet_read("current", sheet, PropertyGroup.FILTER)]


def normalize_criterion(text: str) -> str:
    value = " ".join(str(text).split()).casefold()
    return value[1:] if value.startswith("=") and not value.startswith("==") else value


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    sheet = ctx.sheet(check)
    sheet.require_sheet_group(PropertyGroup.FILTER)
    info = sheet.autofilter
    if info is None or not parse_range(info.range).intersects(check_range(check)):
        return CheckResult.fail("no_filter", detail="chưa bật bộ lọc trên bảng")
    column = check.get("column")
    if column is None:
        return CheckResult.ok()
    criteria_by_header = {normalize_header(h): c for h, c in info.columns.items()}
    actual = criteria_by_header.get(normalize_header(column))
    if actual is None:
        active = ", ".join(info.columns) or "không cột nào"
        return CheckResult.fail("wrong_column", detail=f"đang lọc: {active}")
    wanted = check.get("criteria")
    if wanted is not None and {normalize_criterion(c) for c in actual} != {
        normalize_criterion(c) for c in wanted
    }:
        return CheckResult.fail("wrong_criteria", detail=f"tiêu chí đang đặt: {list(actual)}")
    return CheckResult.ok()
