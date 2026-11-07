"""header_footer — đầu/cuối trang có nội dung yêu cầu (ví dụ số trang "&P") ở đúng vị trí."""

from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read, sheet_read
from excel_core.snapshot import PropertyGroup

TYPE = "header_footer"
CODES = ("wrong_position", "missing_page_number", "missing_header_footer")
PAGE_NUMBER_CODE = "&p"


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [sheet_read("current", sheet, PropertyGroup.PAGE_SETUP)]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    sheet = ctx.sheet(check)
    sheet.require_sheet_group(PropertyGroup.PAGE_SETUP)
    parts = sheet.page_setup.header_footer if sheet.page_setup else {}
    wanted = check["contains"].casefold()
    position = check["position"]
    if wanted in parts.get(position, "").casefold():
        return CheckResult.ok()
    elsewhere = [p for p, text in parts.items() if wanted in text.casefold()]
    if elsewhere:
        return CheckResult.fail("wrong_position", detail=f"đang ở {', '.join(elsewhere)}")
    code = "missing_page_number" if PAGE_NUMBER_CODE in wanted else "missing_header_footer"
    return CheckResult.fail(code)
