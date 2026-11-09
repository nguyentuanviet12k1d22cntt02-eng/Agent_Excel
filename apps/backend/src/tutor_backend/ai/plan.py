"""Kế hoạch kịch bản do LLM trả về (T5.5): chia thay đổi thành bước và viết lời hướng dẫn.

Lược đồ dựng theo từng bài, với danh sách đóng (enum) cho mã thay đổi, nút Ribbon, mã lỗi, đoạn giáo trình:
AI chỉ chọn được thứ có thật. Lược đồ dùng được với structured output chế độ strict (mọi trường bắt buộc,
trường tùy chọn cho phép null), như đã chạy ở T2.6.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from excel_core.checks import codes_for
from tutor_backend.ai.exercise_analysis import ExerciseAnalysis
from tutor_backend.ai.ribbon_catalog import RIBBON

SKILLS = [
    "data_entry",
    "cell_formatting",
    "number_formatting",
    "sheet_structure",
    "page_setup",
    "formula_basics",
    "function_math_stat",
    "function_logical",
    "function_text",
    "function_datetime",
    "function_lookup",
    "sort",
    "filter",
    "chart",
]
MAX_STEPS = 30
MAX_ACTIONS = 10
MAX_ERROR_MESSAGE = 200  # ký tự: lỗi lược đồ gửi lại cho AI và hiện trên Web


@dataclass(frozen=True)
class PlanStep:
    title: str
    task: str
    change_ids: tuple[str, ...]
    ui_controls: tuple[str, ...]
    hint_orientation: str
    hint_tool: str
    hint_location: str
    hint_detailed: str
    actions: tuple[str, ...]
    alternative: str | None
    feedback: tuple[tuple[str, str], ...]  # (mã lỗi, lời phản hồi)
    reference_ids: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    summary: str
    skills: tuple[str, ...]
    completion_message: str
    steps: tuple[PlanStep, ...]


def _string(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def _enum_array(values: Sequence[str], description: str) -> dict[str, Any]:
    if not values:
        return {"type": "array", "items": {"type": "string"}, "maxItems": 0, "description": description}
    return {"type": "array", "items": {"type": "string", "enum": list(values)}, "description": description}


def plan_schema(analysis: ExerciseAnalysis, reference_ids: Sequence[str]) -> dict[str, Any]:
    codes = sorted(
        {code for change in analysis.changes for code in change.codes()}
        | {code for check in analysis.global_checks for code in codes_for(check["type"])}
    )
    feedback_item = {
        "type": "object",
        "additionalProperties": False,
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "string", "enum": codes} if codes else {"type": "string"},
            "message": _string("Phản hồi ngắn cho lỗi này, tiếng Việt"),
        },
    }
    step = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "title",
            "task",
            "change_ids",
            "ui_controls",
            "hint_orientation",
            "hint_tool",
            "hint_location",
            "hint_detailed",
            "actions",
            "alternative",
            "feedback",
            "reference_ids",
        ],
        "properties": {
            "title": _string("Tên bước ngắn"),
            "task": _string("Thẻ yêu cầu: phải đạt gì, KHÔNG nói cách làm"),
            "change_ids": _enum_array([c.id for c in analysis.changes], "Các thay đổi thuộc bước này"),
            "ui_controls": _enum_array(list(RIBBON), "Nút Ribbon dùng ở bước này, theo thứ tự bấm"),
            "hint_orientation": _string("Cấp 1 định hướng: mục tiêu, kiến thức; không nêu tên công cụ"),
            "hint_tool": _string("Cấp 2 gợi ý công cụ: tên lệnh, hàm, nút"),
            "hint_location": _string("Cấp 3 chỉ vị trí: nói 'vùng được khoanh', 'nút được khoanh'"),
            "hint_detailed": _string("Cấp 4 câu dẫn trước các thao tác"),
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Cấp 4: các thao tác theo thứ tự",
            },
            "alternative": {"type": ["string", "null"], "description": "Cách làm khác, null nếu không có"},
            "feedback": {"type": "array", "items": feedback_item},
            "reference_ids": _enum_array(list(reference_ids), "Đoạn giáo trình liên quan"),
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "skills", "completion_message", "steps"],
        "properties": {
            "summary": _string("Học viên cần làm gì trong bài, 1–3 câu"),
            "skills": _enum_array(SKILLS, "Nhóm kỹ năng của bài"),
            "completion_message": _string("Lời khen khi hoàn thành bài"),
            "steps": {"type": "array", "items": step},
        },
    }


class PlanFormatError(ValueError):
    """LLM trả về JSON không đúng lược đồ kế hoạch."""


def _short_message(error: ValidationError) -> str:
    """Lỗi lược đồ ngắn gọn: thông báo của jsonschema chép cả giá trị sai (AI lạc đề thì dài hàng chục KB)."""
    if error.validator == "type":
        return f"phải là kiểu {error.validator_value}, nhận được {type(error.instance).__name__}"
    if error.validator == "enum":
        return "giá trị không thuộc danh sách cho phép"
    message = error.message
    return message if len(message) <= MAX_ERROR_MESSAGE else message[:MAX_ERROR_MESSAGE] + "…"


def parse_plan(data: Any, schema: dict[str, Any]) -> Plan:
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        where = "/".join(str(p) for p in errors[0].absolute_path)
        raise PlanFormatError(f"Kế hoạch sai lược đồ tại /{where}: {_short_message(errors[0])}")
    steps = tuple(
        PlanStep(
            title=s["title"].strip(),
            task=s["task"].strip(),
            change_ids=tuple(dict.fromkeys(s["change_ids"])),
            ui_controls=tuple(dict.fromkeys(s["ui_controls"])),
            hint_orientation=s["hint_orientation"].strip(),
            hint_tool=s["hint_tool"].strip(),
            hint_location=s["hint_location"].strip(),
            hint_detailed=s["hint_detailed"].strip(),
            actions=tuple(a.strip() for a in s["actions"] if a.strip()),
            alternative=(s["alternative"] or "").strip() or None,
            feedback=tuple((f["code"], f["message"].strip()) for f in s["feedback"] if f["message"].strip()),
            reference_ids=tuple(dict.fromkeys(s["reference_ids"])),
        )
        for s in data["steps"]
    )
    return Plan(
        summary=data["summary"].strip(),
        skills=tuple(dict.fromkeys(data["skills"])),
        completion_message=data["completion_message"].strip(),
        steps=steps,
    )


def _procedure_issues(plan: Plan, analysis: ExerciseAnalysis) -> list[str]:
    """Bước quy trình trong đề (p1, p2…): mỗi thao tác một bước riêng, đúng thứ tự, trước mọi bước khác.

    Điều kiện của bước quy trình ghi theo trạng thái ngay sau thao tác; đổi thứ tự là điều kiện sai chỗ.
    """
    procedure = [c.id for c in analysis.changes if c.operation is not None]
    if not procedure:
        return []
    issues = []
    order = []
    for number, step in enumerate(plan.steps, start=1):
        mine = [c for c in step.change_ids if c in procedure]
        if mine and len(step.change_ids) > 1:
            issues.append(
                f"Bước {number} gộp {', '.join(step.change_ids)}: mỗi thao tác của quy trình "
                f"({', '.join(mine)}) phải là một bước riêng"
            )
        order += [(number, c) for c in mine] if mine else [(number, None)]
    ids = [c for _, c in order if c is not None]
    first_other = next((n for n, c in order if c is None), None)
    last_procedure = max((n for n, c in order if c is not None), default=0)
    if ids != [c for c in procedure if c in ids] or (
        first_other is not None and first_other < last_procedure
    ):
        issues.append(
            f"Các bước quy trình {', '.join(procedure)} phải đúng thứ tự đề ghi, đứng trước mọi bước khác"
        )
    return issues


def plan_issues(plan: Plan, analysis: ExerciseAnalysis) -> list[str]:
    """Lỗi chia bước: thay đổi chưa thuộc bước nào, thuộc hai bước, bước rỗng, quá nhiều bước."""
    issues = []
    seen: dict[str, int] = {}
    for number, step in enumerate(plan.steps, start=1):
        if not step.change_ids:
            issues.append(f"Bước {number} ({step.title}) không có thay đổi nào: gộp vào bước khác hoặc bỏ")
        for change_id in step.change_ids:
            if change_id in seen:
                issues.append(
                    f"Thay đổi {change_id} nằm ở cả bước {seen[change_id]} và bước {number}: chỉ để một bước"
                )
            seen.setdefault(change_id, number)
    issues += _procedure_issues(plan, analysis)
    missing = [c.id for c in analysis.changes if c.id not in seen]
    if missing:
        issues.append(
            f"Thay đổi {', '.join(missing)} chưa thuộc bước nào: mỗi thay đổi phải thuộc đúng một bước"
        )
    if not plan.steps:
        issues.append("Kế hoạch không có bước nào")
    if len(plan.steps) > MAX_STEPS:
        issues.append(f"Quá nhiều bước ({len(plan.steps)}), tối đa {MAX_STEPS}")
    return issues
