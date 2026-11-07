"""data_unchanged — vùng dữ liệu gốc giữ nguyên như file đề (điều kiện toàn bài).

Ô có công thức trong file đề thì so công thức (giá trị được phép đổi theo ô khác); ô hằng số thì so giá trị.
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
from excel_core.checks.values import values_equal
from excel_core.snapshot import PropertyGroup

TYPE = "data_unchanged"
CODES = ("formula_overwritten", "source_modified")
_GROUPS = (PropertyGroup.VALUES, PropertyGroup.FORMULAS)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    rng = check["range"]
    return [cell_read("current", sheet, rng, *_GROUPS), cell_read("starter", sheet, rng, *_GROUPS)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    current, starter = ctx.sheet(check), ctx.sheet(check, "starter")
    for group in _GROUPS:
        current.require(target, group)
        starter.require(target, group)
    failures = Failures(CODES)
    for address in target.cells():
        now, before = current.cell(address), starter.cell(address)
        if before.formula is not None:
            if now.formula != before.formula:
                failures.add("formula_overwritten", address)
        elif now.formula is not None or not values_equal(now.value, before.value):
            failures.add("source_modified", address)
    return failures.result()
