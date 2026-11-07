"""merged — vùng được gộp thành đúng một ô."""

from excel_core.address import parse_range
from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read, cell_read, check_range
from excel_core.snapshot import PropertyGroup

TYPE = "merged"
CODES = ("not_merged",)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.STRUCTURE)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.STRUCTURE)
    if any(parse_range(m) == target for m in sheet.merged):
        return CheckResult.ok()
    overlapping = [m for m in sheet.merged if parse_range(m).intersects(target)]
    detail = f"đang gộp: {', '.join(overlapping)}" if overlapping else "chưa gộp"
    return CheckResult.fail("not_merged", [str(target)], detail)
