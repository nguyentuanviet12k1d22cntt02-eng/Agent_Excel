"""visible_rows — đúng tập dòng đang hiện trong vùng (sau khi lọc), so với file đáp án."""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    CheckSpecError,
    Read,
    cell_read,
    check_range,
)
from excel_core.snapshot import PropertyGroup

TYPE = "visible_rows"
CODES = ("wrong_rows_visible",)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [
        cell_read("current", sheet, check["range"], PropertyGroup.STRUCTURE),
        cell_read("solution", sheet, check["range"], PropertyGroup.STRUCTURE),
    ]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    if check["expected"]["from"] != "solution":
        raise CheckSpecError("visible_rows chỉ nhận expected: {from: solution}")
    table = check_range(check)
    current, solution = ctx.sheet(check), ctx.sheet(check, "solution")
    current.require(table, PropertyGroup.STRUCTURE)
    solution.require(table, PropertyGroup.STRUCTURE)
    rows = set(table.rows())
    differing = sorted((current.hidden_rows ^ solution.hidden_rows) & rows)
    if not differing:
        return CheckResult.ok()
    return CheckResult.fail(
        "wrong_rows_visible", [str(r) for r in differing], f"{len(differing)} dòng khác đáp án"
    )
