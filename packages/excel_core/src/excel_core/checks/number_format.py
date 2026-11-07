"""number_format — định dạng số so theo ý nghĩa (loại, số chữ số thập phân, dấu nghìn, mẫu ngày).

Không so chuỗi mã: Comma Style mỗi máy một mã, máy vi-VN và en-US khác nhau (T1.2).
"""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.snapshot import NumberFormatInfo, PropertyGroup, normalize_date_pattern, parse_number_format

TYPE = "number_format"
# Thứ tự kiểm cũng là thứ tự ưu tiên mã lỗi: sai loại (ví dụ còn General) báo trước
CODES = (
    "wrong_category",
    "missing_separator",
    "unexpected_separator",
    "wrong_decimals",
    "wrong_date_pattern",
)
GENERAL = parse_number_format(None)  # ô chưa từng định dạng


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.NUMBER_FORMAT)]


def _cell_code(info: NumberFormatInfo, check: CheckSpec) -> str | None:
    categories = check.get("categories")
    if categories and info.category not in categories:
        return "wrong_category"
    separator = check.get("thousands_separator")
    if separator is True and not info.thousands_separator:
        return "missing_separator"
    if separator is False and info.thousands_separator:
        return "unexpected_separator"
    if "decimals" in check and info.decimals != check["decimals"]:
        return "wrong_decimals"
    pattern = check.get("date_pattern")
    if pattern and info.date_pattern != normalize_date_pattern(pattern):
        return "wrong_date_pattern"
    return None


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.NUMBER_FORMAT)
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        code = _cell_code(cell.number_format or GENERAL, check)
        if code:
            failures.add(code, address)
    return failures.result()
