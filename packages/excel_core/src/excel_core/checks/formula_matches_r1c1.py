"""formula_matches_r1c1 — công thức đúng mẫu R1C1 cho trước (khi chỉ có một cách đúng)."""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.formula import FormulaError, normalize_r1c1
from excel_core.snapshot import PropertyGroup

TYPE = "formula_matches_r1c1"
CODES = ("hardcoded_value", "wrong_formula", "empty")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.VALUES, PropertyGroup.FORMULAS)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.FORMULAS)
    try:
        wanted = normalize_r1c1(check["r1c1"])
    except FormulaError as exc:
        return CheckResult.not_evaluable(f"Mẫu R1C1 trong kịch bản không hợp lệ: {exc}")
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        if cell.formula is None:
            failures.add("empty" if cell.value_kind == "empty" else "hardcoded_value", address)
        elif cell.formula_r1c1 != wanted:
            failures.add("wrong_formula", address)
    return failures.result()
