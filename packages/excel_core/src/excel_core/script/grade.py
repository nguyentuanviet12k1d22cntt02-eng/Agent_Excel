"""Chấm một file bài làm theo kịch bản, đúng như Desktop sẽ chấm (cùng `run_check`, cùng snapshot tham chiếu).

Giảng viên dùng để thử kịch bản trước khi có Desktop (GĐ7): mở file đề bằng Excel, làm vài bước như học
viên, lưu lại rồi chấm. Trên file không có sự kiện trực tiếp nên "in ra PDF" và "học viên tự xác nhận" không
chấm được.

Kịch bản theo quy trình (bước có `operation`): file chỉ cho thấy trạng thái lúc lưu, các bước trung gian (ẩn
cột H rồi lại hiện) không còn dấu vết. So bố cục, dòng/cột ẩn, kích thước của file với trạng thái mong đợi sau
từng bước (làm lần lượt các thao tác trên file đề) để biết học viên làm tới đâu: các bước trước đó tính là đã
qua, bước kế tiếp chấm như thường, các bước sau nữa là "chưa tới".
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from excel_core.checks import CheckContext, CheckResult, CheckStatus, read_requests, run_check
from excel_core.diff import LAYOUT_KINDS, ChangeKind, diff_workbooks
from excel_core.procedure import ProcedureError
from excel_core.readers import read_workbook
from excel_core.script.self_check import is_procedure, self_check_request, step_states
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
    if is_procedure(script):
        steps = _procedure_progress(script, steps, current, starter, solution)
    return GradeReport(_grade_checks(list(script.get("global_checks", [])), ctx), tuple(steps))


_STRUCTURE = LAYOUT_KINDS | {
    ChangeKind.COL_HIDDEN,
    ChangeKind.ROW_HIDDEN,
    ChangeKind.COL_WIDTH,
    ChangeKind.ROW_HEIGHT,
}


def _same_structure(expected: WorkbookSnapshot, current: WorkbookSnapshot, sheet: str) -> bool:
    """Bố cục (chèn/xóa), dòng/cột ẩn, kích thước của file bài làm giống trạng thái mong đợi."""
    return not any(
        c.sheet == sheet and c.kind in _STRUCTURE for c in diff_workbooks(expected, current).changes
    )


def _procedure_progress(
    script: Script,
    steps: list[StepGrade],
    current: WorkbookSnapshot,
    starter: WorkbookSnapshot,
    solution: WorkbookSnapshot,
) -> list[StepGrade]:
    """Bước quy trình đã qua / đang làm / chưa tới, theo trạng thái mong đợi khớp với file bài làm."""
    sheet = script["exercise"]["sheet"]
    try:
        states = step_states(script, starter, solution)
    except ProcedureError:
        return steps
    procedural = [i for i, step in enumerate(script["steps"]) if "operation" in step]
    candidates = [(0, starter)] + [
        (n, states[script["steps"][i]["id"]][1]) for n, i in enumerate(procedural, start=1)
    ]
    done = max((n for n, state in candidates if _same_structure(state, current, sheet)), default=None)
    if done is None:  # làm khác mọi trạng thái mong đợi: chấm từng bước như thường
        return steps
    passed = CheckResult(CheckStatus.PASSED, detail="đã làm tới bước quy trình sau")
    ahead = CheckResult(CheckStatus.NOT_EVALUABLE, detail="chưa tới bước này (quy trình làm theo thứ tự)")
    graded = list(steps)
    for n, i in enumerate(procedural, start=1):
        if n == done + 1:
            continue
        result = passed if n <= done else ahead
        g = steps[i]
        graded[i] = StepGrade(
            g.step_id, g.title, tuple(CheckGrade(c.index, c.type, result) for c in g.checks), ()
        )
    return graded


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
