"""Tác tử sinh kịch bản (T5.5): phân tích bài → LLM chia bước, viết lời → dựng kịch bản → tự kiểm 3 tầng →
còn lỗi thì gửi lỗi cho LLM sửa, tối đa `max_attempts` lần (kien-truc.md mục 5).

Kết quả không đạt sau số lần cho phép vẫn được trả về (lưu bản nháp kèm báo cáo) để giảng viên sửa tiếp:
NFR-13 chặn ở bước gửi duyệt/phát hành, không chặn ở bước sinh.
"""

import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from excel_core.checks import codes_for
from excel_core.script import self_check_files, validate_script
from tutor_backend.ai.exercise_analysis import ExerciseAnalysis
from tutor_backend.ai.llm_client import LLMClient, LLMError
from tutor_backend.ai.plan import Plan, PlanFormatError, parse_plan, plan_issues, plan_schema
from tutor_backend.ai.prompts import render
from tutor_backend.ai.rag import Passage
from tutor_backend.ai.ribbon_catalog import catalog_text
from tutor_backend.ai.script_builder import ExerciseInfo, build_script

logger = logging.getLogger(__name__)

MAX_PASSAGE_CHARS = 700
PLAN_SCHEMA_NAME = "tutor_script_plan"


@dataclass
class GenerationOutcome:
    script: dict[str, Any] | None
    report: dict[str, Any] | None  # SelfCheckReport (openapi.yaml) + phần "generation"
    attempts: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_ms: int = 0
    remaining_issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.script is not None and not self.remaining_issues


def _passage_ids(passages: Sequence[Passage]) -> dict[str, Passage]:
    return {f"ref_{i}": p for i, p in enumerate(passages, start=1)}


def _change_lines(analysis: ExerciseAnalysis) -> str:
    lines = []
    for change in analysis.changes:
        sources = "; ".join(label for _, label in change.sources) or "-"
        codes = sorted({code for check in change.checks for code in codes_for(check["type"])})
        where = change.label if change.sheet == analysis.sheet else f"{change.label} (sheet {change.sheet})"
        if change.context:
            where += f" ({change.context})"
        lines.append(f"{change.id} | {where} | {change.description} | {sources} | {', '.join(codes)}")
    return "\n".join(lines)


def build_request(analysis: ExerciseAnalysis, info: ExerciseInfo, passages: dict[str, Passage]) -> str:
    passage_text = "\n".join(
        f"[{ref}] {p.heading}: {' '.join(p.content.split())[:MAX_PASSAGE_CHARS]}"
        for ref, p in passages.items()
    )
    return render(
        "generate_script_user",
        title=info.title,
        sheet=info.sheet,
        prompt_text=info.prompt_text or "(không có, xem chữ trong file đề)",
        workbook_text="\n".join(analysis.workbook_text) or "(không có)",
        instructions=info.instructions or "(không có)",
        changes=_change_lines(analysis),
        preserved="\n".join(f"- {p}" for p in analysis.preserved) or "(không có)",
        passages=passage_text or "(không có đoạn giáo trình nào)",
        ribbon=catalog_text(),
    )


def _self_check_issues(
    script: dict[str, Any], starter: Path, solution: Path
) -> tuple[list[str], dict[str, Any]]:
    """Lỗi cần LLM sửa (chặn) và báo cáo tự kiểm để lưu."""
    validation = validate_script(script)
    report: dict[str, Any] = {
        "schema_ok": validation.schema_ok,
        "cross_reference_errors": [str(i) for i in validation.cross_reference_issues],
    }
    issues = [f"Lược đồ: {i}" for i in validation.schema_issues]
    issues += [f"Tham chiếu chéo: {i}" for i in validation.cross_reference_issues]
    if validation.schema_ok:
        self_check = self_check_files(script, starter, solution)
        report |= self_check.to_dict()
        issues += [f"Tự kiểm: {e}" for e in self_check.errors]
        issues += [
            f'Bước {i["step_id"]}: bỏ "{i["text"]}" khỏi câu chữ ({i["issue"]})'
            for i in self_check.hint_text_issues
        ]
    return issues, report


def generate_script(
    analysis: ExerciseAnalysis,
    info: ExerciseInfo,
    passages: Sequence[Passage],
    llm: LLMClient,
    files: tuple[Path, Path],
    max_attempts: int,
    on_stage: Callable[[str], None] | None = None,
) -> GenerationOutcome:
    """Sinh kịch bản cho một bài; `files` = (file đề, file đáp án) để tự kiểm tầng 3."""
    notify = on_stage or (lambda _: None)
    refs = _passage_ids(passages)
    schema = plan_schema(analysis, list(refs))
    system = render("generate_script_system")
    request = build_request(analysis, info, refs)
    user = request
    outcome = GenerationOutcome(script=None, report=None)
    for attempt in range(1, max_attempts + 1):
        outcome.attempts = attempt
        notify("llm")
        response = llm.complete_json(system, user, schema, PLAN_SCHEMA_NAME)
        outcome.prompt_tokens += response.prompt_tokens
        outcome.completion_tokens += response.completion_tokens
        outcome.llm_ms += response.duration_ms
        try:
            plan = parse_plan(response.data, schema)
        except PlanFormatError as exc:
            issues = [str(exc)]
            plan = None
        if plan is not None:
            notify("self_check")
            issues = plan_issues(plan, analysis)
            outcome.script = build_script(analysis, plan, info, refs, llm.model)
            check_issues, outcome.report = _self_check_issues(outcome.script, *files)
            issues += check_issues
        outcome.remaining_issues = issues
        logger.info("Sinh kịch bản %s lần %d: %d lỗi", info.code, attempt, len(issues))
        if not issues:
            break
        user = render(
            "repair_script_user",
            previous_plan=json.dumps(response.data, ensure_ascii=False)[:12000],
            issues="\n".join(f"- {i}" for i in issues),
            original_request=request,
        )
    if outcome.report is not None:
        outcome.report["generation"] = {
            "attempts": outcome.attempts,
            "remaining_issues": outcome.remaining_issues,
            "model": llm.model,
        }
    return outcome


__all__ = ["ExerciseInfo", "GenerationOutcome", "LLMError", "Plan", "build_request", "generate_script"]
