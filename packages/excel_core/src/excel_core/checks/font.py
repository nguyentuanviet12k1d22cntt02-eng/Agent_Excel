"""font — phông chữ: chỉ kiểm thuộc tính được ghi trong kịch bản (đậm, nghiêng, gạch chân, cỡ, tên, màu)."""

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
from excel_core.snapshot import FontInfo, PropertyGroup

TYPE = "font"
CODES = ("wrong_font",)
SIZE_TOLERANCE = 0.01


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.STYLE)]


def _matches(font: FontInfo | None, check: CheckSpec) -> bool:
    if font is None:
        return False
    for attr in ("bold", "italic", "underline"):
        if attr in check and getattr(font, attr) != check[attr]:
            return False
    if "size" in check and abs(font.size - float(check["size"])) > SIZE_TOLERANCE:
        return False
    if "name" in check and font.name.casefold() != str(check["name"]).casefold():
        return False
    return not ("color" in check and not colors_close(font.color, check["color"]))


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.STYLE)
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        if not _matches(cell.font, check):
            failures.add("wrong_font", address)
    return failures.result()
