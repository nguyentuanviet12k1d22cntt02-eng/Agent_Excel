"""printed_to_pdf — học viên đã in ra PDF.

Không thấy trong workbook: Desktop bắt sự kiện WorkbookBeforePrint (T2.4).

Khi chấm trên file (Backend tự kiểm), điều kiện này không chấm được.
"""

from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read

TYPE = "printed_to_pdf"
CODES = ("not_printed",)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return []


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    if ctx.printed_to_pdf is None:
        return CheckResult.not_evaluable("chỉ Desktop chấm được (sự kiện in)")
    return CheckResult.ok() if ctx.printed_to_pdf else CheckResult.fail("not_printed")
