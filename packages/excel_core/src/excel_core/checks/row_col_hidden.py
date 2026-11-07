"""row_col_hidden — dòng/cột bị ẩn hoặc đang hiện."""

from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Failures, Read, cell_read
from excel_core.checks.lines import line_range, lines_of
from excel_core.snapshot import PropertyGroup

TYPE = "row_col_hidden"
CODES = ("wrong_visibility",)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    axis, lines = lines_of(check)
    return [cell_read("current", sheet, line_range(axis, lines), PropertyGroup.STRUCTURE)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    axis, lines = lines_of(check)
    sheet = ctx.sheet(check)
    sheet.require(line_range(axis, lines), PropertyGroup.STRUCTURE)
    hidden = sheet.hidden_rows if axis == "rows" else sheet.hidden_cols
    failures = Failures(CODES)
    for line in lines:
        if (line in hidden) != bool(check["hidden"]):
            failures.add("wrong_visibility", str(line))
    return failures.result()
