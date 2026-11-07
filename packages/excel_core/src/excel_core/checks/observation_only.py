"""observation_only — bước quan sát/nhận xét, không chấm tự động: học viên tự bấm "Đã xong"."""

from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read

TYPE = "observation_only"
CODES = ("not_confirmed",)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return []


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    if ctx.learner_confirmed is None:
        return CheckResult.not_evaluable("học viên tự xác nhận trên Desktop")
    return CheckResult.ok() if ctx.learner_confirmed else CheckResult.fail("not_confirmed")
