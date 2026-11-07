"""is_formula — mọi ô trong vùng là công thức, không phải số gõ tay."""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.snapshot import PropertyGroup

TYPE = "is_formula"
CODES = ("hardcoded_value", "empty")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.VALUES, PropertyGroup.FORMULAS)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.FORMULAS)
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        if cell.is_formula:
            continue
        failures.add("empty" if cell.value_kind == "empty" else "hardcoded_value", address)
    return failures.result()
