"""fill — màu nền: một màu cụ thể (có ngưỡng) hoặc "any" (có tô màu bất kỳ)."""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.checks.colors import colors_close
from excel_core.snapshot import PropertyGroup

TYPE = "fill"
CODES = ("no_fill", "wrong_fill")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.STYLE)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.STYLE)
    wanted = check["color"]
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        color = cell.fill.color if cell.fill else None
        if color is None:
            failures.add("no_fill", address)
        elif wanted != "any" and not colors_close(color, wanted):
            failures.add("wrong_fill", address)
    return failures.result()
