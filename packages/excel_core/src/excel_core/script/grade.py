"""Chấm một file bài làm theo kịch bản, đúng như Desktop sẽ chấm (cùng `run_check`, cùng snapshot tham chiếu).

Giảng viên dùng để thử kịch bản trước khi có Desktop (GĐ7): mở file đề bằng Excel, làm vài bước như học
viên, lưu lại rồi chấm. Trên file không có sự kiện trực tiếp nên "in ra PDF" và "học viên tự xác nhận" không
chấm được.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from excel_core.checks import CheckContext, CheckResult, CheckStatus, read_requests, run_check
from excel_core.readers import read_workbook
from excel_core.script.self_check import self_check_request
from excel_core.snapshot import WorkbookSnapshot, merge_requests

type Script = Mapping[str, Any]


@dataclass(frozen=True)
class CheckGrade:
    index: int
    type: str
    result: CheckResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "type": self.type,
            "status": self.result.status.value,
            "code": self.result.code,
            "cells": list(self.result.cells),
            "detail": self.result.detail,
        }


def _status(checks: tuple[CheckGrade, ...]) -> CheckStatus:
    if any(c.result.status == CheckStatus.FAILED for c in checks):
        return CheckStatus.FAILED
    if any(c.result.status == CheckStatus.NOT_EVALUABLE for c in checks):
        return CheckStatus.NOT_EVALUABLE
    return CheckStatus.PASSED


@dataclass(frozen=True)
class StepGrade:
    step_id: str
    title: str
    checks: tuple[CheckGrade, ...]
    feedback: tuple[Mapping[str, Any], ...]  # phản hồi gia sư sẽ hiện, theo mã lỗi của điều kiện chưa đạt

    @property
    def status(self) -> CheckStatus:
        return _status(self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "status": self.status.value,
            "checks": [c.to_dict() for c in self.checks],
            "feedback": [dict(f) for f in self.feedback],
        }


@dataclass(frozen=True)
class GradeReport:
    global_checks: tuple[CheckGrade, ...]
    steps: tuple[StepGrade, ...]

    @property
    def current_step_id(self) -> str | None:
        """Bước học viên đang làm: bước đầu tiên chưa đạt (Desktop đi theo thứ tự bước)."""
        return next((s.step_id for s in self.steps if s.status != CheckStatus.PASSED), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_step_id": self.current_step_id,
            "global_checks": [c.to_dict() for c in self.global_checks],
            "steps": [s.to_dict() for s in self.steps],
        }


def _grade_checks(checks: list[Mapping[str, Any]], ctx: CheckContext) -> tuple[CheckGrade, ...]:
    return tuple(CheckGrade(i, check["type"], run_check(check, ctx)) for i, check in enumerate(checks))


def _feedback(step: Mapping[str, Any], checks: tuple[CheckGrade, ...]) -> tuple[Mapping[str, Any], ...]:
    codes = [c.result.code for c in checks if c.result.status == CheckStatus.FAILED and c.result.code]
    by_code = {f["code"]: f for f in step.get("feedback", [])}
    return tuple(by_code[code] for code in dict.fromkeys(codes) if code in by_code)


def grade(
    script: Script, current: WorkbookSnapshot, starter: WorkbookSnapshot, solution: WorkbookSnapshot
) -> GradeReport:
    ctx = CheckContext(
        current=current, default_sheet=script["exercise"]["sheet"], starter=starter, solution=solution
    )
    steps = []
    for step in script["steps"]:
        checks = _grade_checks(step["checks"], ctx)
        steps.append(StepGrade(step["id"], step["title"], checks, _feedback(step, checks)))
    return GradeReport(_grade_checks(list(script.get("global_checks", [])), ctx), tuple(steps))


def grade_files(
    script: Script, current_path: Path | str, starter_path: Path | str, solution_path: Path | str
) -> GradeReport:
    """Chấm file bài làm (.xlsx đã lưu bằng Excel, để có giá trị công thức) theo kịch bản."""
    sheet = script["exercise"]["sheet"]
    checks = [*script.get("global_checks", []), *(c for s in script["steps"] for c in s["checks"])]
    current_needs = read_requests(checks, sheet).get("current")
    request = self_check_request(script, starter_path, solution_path)
    if current_needs is not None:
        request = merge_requests([request, current_needs])
    return grade(
        script,
        read_workbook(current_path, request),
        read_workbook(starter_path, request),
        read_workbook(solution_path, request),
    )
