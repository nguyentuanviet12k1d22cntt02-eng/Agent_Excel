"""Dựng kịch bản v1 (schemas/tutor-script/v1) từ phân tích bài + kế hoạch của LLM (T5.5).

Phần tất định do code làm: vùng mục tiêu, điều kiện kiểm chứng, điều kiện toàn bài, vùng khoanh ở gợi ý cấp 3.
Phần chữ (thẻ yêu cầu, gợi ý, phản hồi) lấy từ kế hoạch của LLM.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from excel_core.address import group_into_ranges, parse_range
from excel_core.checks import codes_for
from tutor_backend.ai.exercise_analysis import ChangeItem, ExerciseAnalysis
from tutor_backend.ai.plan import MAX_ACTIONS, Plan, PlanStep
from tutor_backend.ai.rag import Passage
from tutor_backend.ai.ribbon_catalog import RIBBON
from tutor_backend.ai.vietnamese import strip_accents

MAX_MESSAGE = 600
MAX_TITLE = 120
MAX_QUOTE = 300
# Điều kiện chấm từng ô độc lập: gộp được các vùng kề nhau có cùng tham số thành một vùng
CELLWISE_TYPES = frozenset({"value_type", "is_formula", "number_format", "alignment", "font", "fill"})


@dataclass(frozen=True)
class ExerciseInfo:
    code: str
    title: str
    sheet: str
    prompt_text: str | None = None
    instructions: str | None = None  # lưu ý thêm của giảng viên cho AI


def _clip(text: str, limit: int = MAX_MESSAGE) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def step_id(number: int, title: str, used: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", strip_accents(title).lower()).strip("_")[:28].rstrip("_")
    base = f"s{number}_{slug}" if slug else f"s{number}"
    candidate, suffix = base, 2
    while candidate in used:
        candidate, suffix = f"{base}_{suffix}", suffix + 1
    used.add(candidate)
    return candidate


def _signature(check: dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in check.items() if k != "range"}, sort_keys=True, ensure_ascii=False)


def _mergeable(check: dict[str, Any]) -> bool:
    if check["type"] == "value_equals":
        return check.get("expected", {}).get("from") == "solution"
    return check["type"] in CELLWISE_TYPES and "range" in check


def merge_checks(checks: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gộp điều kiện chấm từng ô cùng tham số khi các vùng ghép thành hình chữ nhật (F10:F14 + G10:G14).

    Giữ thứ tự xuất hiện đầu tiên: thứ tự điều kiện quyết định mã lỗi báo trước (danh-muc-dieu-kien.md mục 6).
    """
    ordered: list[tuple[float, dict[str, Any]]] = []
    groups: dict[str, tuple[int, list[dict[str, Any]]]] = {}
    for index, check in enumerate(checks):
        if _mergeable(check):
            groups.setdefault(_signature(check), (index, []))[1].append(check)
        elif all(check != existing for _, existing in ordered):
            ordered.append((index, check))
    for index, same in groups.values():
        cells: set[tuple[int, int]] = set()
        for check in same:
            rng = parse_range(check["range"])
            cells.update((c, r) for r in rng.rows() for c in rng.cols())
        for offset, rng in enumerate(group_into_ranges(cells)):
            ordered.append((index + offset / 1000, {**same[0], "range": str(rng)}))
    return [check for _, check in sorted(ordered, key=lambda item: item[0])]


def _cell_target(sheet: str, default_sheet: str, rng: str, role: str, label: str) -> dict[str, Any]:
    target: dict[str, Any] = {"range": rng, "role": role, "label": _clip(label, 60)}
    if sheet != default_sheet:
        target["sheet"] = sheet
    return target


def _targets(
    changes: list[ChangeItem], default_sheet: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(vùng nguồn, vùng đích) của bước, bỏ trùng; vùng đích kề nhau cùng sheet được gộp."""
    sources, targets = [], []
    seen: set[tuple[str, str, str]] = set()
    for change in changes:
        for rng, label in change.sources:
            if (change.sheet, rng, "source") not in seen:
                seen.add((change.sheet, rng, "source"))
                sources.append(_cell_target(change.sheet, default_sheet, rng, "source", label))
    by_sheet: dict[str, list[ChangeItem]] = {}
    for change in changes:
        if change.range:
            by_sheet.setdefault(change.sheet, []).append(change)
    for sheet, items in by_sheet.items():
        cells: set[tuple[int, int]] = set()
        for item in items:
            for text in (item.range or "", *item.more_ranges):
                rng = parse_range(text)
                cells.update((c, r) for r in rng.rows() for c in rng.cols())
        for rng in group_into_ranges(cells):
            label = next((i.label for i in items if parse_range(i.range or "") == rng), None)
            label = label or " và ".join(
                dict.fromkeys(
                    i.label
                    for i in items
                    if any(rng.contains(parse_range(r)) for r in (i.range or "", *i.more_ranges))
                )
            )
            targets.append(_cell_target(sheet, default_sheet, str(rng), "target", label or "vùng cần làm"))
    return sources, targets


def _hints(
    step: PlanStep, sources: list[dict[str, Any]], targets: list[dict[str, Any]], ui: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    highlight = [{"cells": {k: v for k, v in t.items() if k != "label"}} for t in sources + targets]
    highlight += [{"ui": {"tab": u["tab"], "control": u["control"]}} for u in ui]
    actions = [_clip(a) for a in step.actions][:MAX_ACTIONS] or [_clip(step.hint_detailed)]
    detailed: dict[str, Any] = {
        "level": 4,
        "text": _clip(step.hint_detailed or "Làm theo các bước:"),
        "actions": actions,
    }
    if step.alternative:
        detailed["alternative"] = _clip(step.alternative)
    hints = [
        {"level": 1, "text": _clip(step.hint_orientation)},
        {"level": 2, "text": _clip(step.hint_tool)},
        {"level": 3, "text": _clip(step.hint_location), "highlight": highlight},
        detailed,
    ]
    if step.reference_ids:
        hints[1]["reference_ids"] = list(step.reference_ids)
    return hints


def _reference(ref_id: str, passage: Passage) -> dict[str, Any]:
    location = passage.heading + (f", trang {passage.page}" if passage.page else "")
    return {
        "id": ref_id,
        "kind": "textbook",
        "title": _clip(f"{passage.textbook_title}: {passage.heading}", 200),
        "location": _clip(location, 200),
        "quote": _clip(passage.content, MAX_QUOTE),
    }


def build_step(
    number: int, step: PlanStep, analysis: ExerciseAnalysis, global_codes: set[str], used_ids: set[str]
) -> dict[str, Any]:
    changes = [c for change_id in step.change_ids if (c := analysis.change(change_id)) is not None]
    sources, targets = _targets(changes, analysis.sheet)
    ui = [
        {"tab": RIBBON[c].tab, "control": c, "label": RIBBON[c].label[:60]}
        for c in step.ui_controls
        if c in RIBBON
    ]
    checks = merge_checks([dict(check) for change in changes for check in change.checks])
    returnable = global_codes | {code for change in changes for code in change.codes()}
    feedback, seen = [], set()
    for code, message in step.feedback:
        if code in returnable and code not in seen:  # mã không trả về được thì phản hồi vô dụng: bỏ
            seen.add(code)
            feedback.append({"code": code, "message": _clip(message)})
    built: dict[str, Any] = {
        "id": step_id(number, step.title, used_ids),
        "title": _clip(step.title or f"Bước {number}", MAX_TITLE),
        "task": _clip(step.task or step.title),
        "targets": {"cells": sources + targets or [{"range": "A1", "role": "target"}]},
        "checks": checks,
        "hints": _hints(step, sources, targets, ui),
    }
    if ui:
        built["targets"]["ui"] = ui
    operations = [change.operation for change in changes if change.operation is not None]
    if len(operations) == 1:
        built["operation"] = dict(operations[0])
    guides = [change.guide for change in changes if change.guide]
    if len(guides) == 1:
        built["guide"] = [dict(item) for item in guides[0]]
    if feedback:
        built["feedback"] = feedback
    if step.reference_ids:
        built["reference_ids"] = list(step.reference_ids)
    return built


def build_script(
    analysis: ExerciseAnalysis,
    plan: Plan,
    info: ExerciseInfo,
    passages: dict[str, Passage],
    model: str,
) -> dict[str, Any]:
    global_codes = {code for check in analysis.global_checks for code in codes_for(check["type"])}
    used_ids: set[str] = set()
    steps = [
        build_step(n, step, analysis, global_codes, used_ids)
        for n, step in enumerate(plan.steps, start=1)
        if any(analysis.change(c) for c in step.change_ids)
    ]
    cited = list(dict.fromkeys(ref for step in plan.steps for ref in step.reference_ids if ref in passages))
    exercise: dict[str, Any] = {"id": info.code, "title": _clip(info.title, 200), "sheet": info.sheet}
    if plan.summary:
        exercise["summary"] = _clip(plan.summary, 1000)
    if plan.skills:
        exercise["skills"] = list(plan.skills)
    script: dict[str, Any] = {
        "schema_version": "1",
        "exercise": exercise,
        "revision": 1,
        "meta": {
            "origin": "ai",
            "model": model[:80],
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "notes": f"Sinh tự động từ diff đề/đáp án ({len(analysis.changes)} thay đổi).",
        },
    }
    if cited:
        script["references"] = [_reference(ref, passages[ref]) for ref in cited]
    if analysis.global_checks:
        script["global_checks"] = [dict(c) for c in analysis.global_checks]
    script["steps"] = steps
    if plan.completion_message:
        script["completion"] = {"message": _clip(plan.completion_message)}
    return script
