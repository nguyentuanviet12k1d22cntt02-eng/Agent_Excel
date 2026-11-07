"""value_equals — giá trị vùng bằng giá trị kỳ vọng (mặc định lấy từ đáp án)."""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.checks.expected import expected_reads, expected_values
from excel_core.checks.values import is_number_stored_as_text, values_equal
from excel_core.snapshot import PropertyGroup

TYPE = "value_equals"
# Thứ tự ưu tiên khi nhiều ô sai khác kiểu: lỗi cụ thể trước, "chưa làm" sau cùng
CODES = ("stored_as_text", "wrong_value", "empty")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.VALUES), *expected_reads(check, sheet)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.VALUES)
    tolerance = float(check.get("tolerance", 0))
    failures = Failures(CODES)
    for address, expected in zip(target.cells(), expected_values(check, target, ctx), strict=True):
        cell = sheet.cell(address)
        if values_equal(cell.value, expected, tolerance):
            continue
        if cell.value is None:
            failures.add("empty", address)
        elif isinstance(expected, float | int) and is_number_stored_as_text(cell, expected):
            failures.add("stored_as_text", address)
        else:
            failures.add("wrong_value", address)
    return failures.result()
