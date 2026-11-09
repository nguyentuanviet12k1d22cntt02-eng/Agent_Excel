"""Kịch bản theo quy trình trong đề (T5.9): AI chép quy trình, code làm thử trên file đề và kiểm khớp đáp án,
mỗi thao tác thành một bước kiểm theo trạng thái ngay sau thao tác. Bài nhỏ kiểu bài 06: hiện cột E đang ẩn
rồi xóa hai cột trống D, E."""

from pathlib import Path
from typing import Any

import openpyxl
import pytest

from excel_core.procedure import ProcedureError
from tutor_backend.ai.exercise_analysis import analyze_exercise
from tutor_backend.ai.llm_client import LLMResponse
from tutor_backend.ai.plan import Plan, PlanStep, plan_issues
from tutor_backend.ai.procedure import extract_procedure, parse_procedure, wants_procedure
from tutor_backend.ai.script_agent import generate_script
from tutor_backend.ai.script_builder import ExerciseInfo

SHEET = "Bài tập"
HEADERS = ("Mã hàng", "Tên hàng", "Số lượng", "Đơn giá")
PROMPT = "Hiển thị cột E. Xóa các cột trống D, E."


def build(path: Path, gap: int, hidden: str | None = None) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = SHEET
    ws["B2"] = "DANH SÁCH HÀNG"
    ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=5 + gap)
    rows = (HEADERS, ("A01", "Bút", 10, 5000), ("A02", "Vở", 20, 12000))
    for row, values in enumerate(rows, start=4):
        for index, value in enumerate(values):
            ws.cell(row, 2 + index + (gap if index >= 2 else 0), value)
    if hidden:
        ws.column_dimensions[hidden].hidden = True
    wb.save(path)
    return path


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path]:
    return build(tmp_path / "de.xlsx", gap=2, hidden="E"), build(tmp_path / "dap-an.xlsx", gap=0)


def operation(instruction: str, action: str, lines: list[str], side: str = "none") -> dict[str, Any]:
    return {
        "instruction": instruction,
        "action": action,
        "axis": "cols",
        "lines": lines,
        "side": side,
        "count": None,
        "size": None,
    }


RIGHT = {
    "operations": [
        operation("Hiển thị cột E", "unhide", ["E"]),
        operation("Xóa các cột trống D, E", "delete", ["D", "E"]),
    ]
}
FORGOT_UNHIDE_AND_E = {"operations": [operation("Xóa cột trống", "delete", ["D"])]}


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str, schema: dict, schema_name: str) -> LLMResponse:
        self.requests.append((schema_name, user))
        return LLMResponse(self.responses.pop(0), prompt_tokens=100, completion_tokens=50, duration_ms=5)


def test_insert_after_a_column_becomes_insert_before_the_next():
    (step,) = parse_procedure({"operations": [operation("Chèn cột sau G", "insert", ["G"], "after")]})
    assert step.operation.to_json() == {"action": "insert", "axis": "cols", "lines": ["H"]}
    with pytest.raises(ProcedureError, match="thao tác 1"):
        parse_procedure({"operations": [operation("Ẩn cột", "hide", ["G7"])]})


def test_wrong_procedure_is_sent_back_and_the_fixed_one_becomes_steps(files: tuple[Path, Path]):
    analysis = analyze_exercise(*files, SHEET)
    assert wants_procedure(analysis, PROMPT)
    llm = FakeLLM([FORGOT_UNHIDE_AND_E, RIGHT])

    outcome = extract_procedure(analysis, "Bài cột", PROMPT, None, llm, max_attempts=3)

    assert outcome.attempts == 2 and outcome.operations == 2 and outcome.issues == []
    assert "còn phải" in llm.requests[1][1]  # lỗi gửi lại AI: làm hết mà bảng vẫn khác đáp án
    assert outcome.analysis is not None
    p1, p2 = outcome.analysis.changes  # không còn khác biệt nào ngoài quy trình
    assert (p1.id, p1.kind, p1.operation) == (
        "p1",
        "col_hidden",
        {"action": "unhide", "axis": "cols", "lines": ["E"]},
    )
    assert p1.range == "D2:F6" and "kẹp cột E" in p1.label  # khoanh hai cột kẹp cột đang ẩn
    assert p1.checks == (
        {"type": "row_col_hidden", "cols": "E", "hidden": False, "description": "Cột E đang hiện."},
    )
    assert p2.operation == {"action": "delete", "axis": "cols", "lines": ["D", "E"]}
    assert [c["range"] for c in p2.checks] == ["C4", "D4", "E4"]  # Tên hàng giữ chỗ, Số lượng/Đơn giá dời
    assert p2.codes() == ["wrong_value", "empty"]
    assert (
        outcome.analysis.global_checks == ()
    )  # dữ liệu dời chỗ giữa chừng: không kiểm giữ nguyên theo địa chỉ


def plan_step(title: str, ids: tuple[str, ...]) -> PlanStep:
    return PlanStep(
        title=title,
        task=f"{title}.",
        change_ids=ids,
        ui_controls=("FormatCellsMenu",),
        hint_orientation="Nhớ lại yêu cầu của đề.",
        hint_tool="Dùng nhóm Cells trên thẻ Home.",
        hint_location="Chọn vùng được khoanh rồi bấm nút được khoanh.",
        hint_detailed="Làm như sau:",
        actions=("Kéo chọn các cột được khoanh.", "Bấm lệnh trên thẻ Home."),
        alternative=None,
        feedback=(),
        reference_ids=(),
    )


def test_procedure_steps_must_stay_separate_and_in_order(files: tuple[Path, Path]):
    analysis = extract_procedure(
        analyze_exercise(*files, SHEET), "Bài cột", PROMPT, None, FakeLLM([RIGHT]), 1
    ).analysis
    assert analysis is not None

    def issues(*steps: PlanStep) -> list[str]:
        return plan_issues(Plan("Tóm tắt", (), "Xong", steps), analysis)

    assert issues(plan_step("Hiện cột E", ("p1",)), plan_step("Xóa cột", ("p2",))) == []
    assert any("bước riêng" in i for i in issues(plan_step("Cả hai", ("p1", "p2"))))
    assert any("đúng thứ tự" in i for i in issues(plan_step("Xóa cột", ("p2",)), plan_step("Hiện", ("p1",))))


def plan_json(*steps: tuple[str, list[str]], feedback: bool = True) -> dict[str, Any]:
    return {
        "summary": "Thao tác với cột.",
        "skills": ["sheet_structure"],
        "completion_message": "Xong rồi!",
        "steps": [
            {
                "title": title,
                "task": f"{title}.",
                "change_ids": ids,
                "ui_controls": ["FormatCellsMenu"],
                "hint_orientation": "Nhớ lại yêu cầu của đề.",
                "hint_tool": "Dùng nhóm Cells trên thẻ Home.",
                "hint_location": "Chọn vùng được khoanh rồi bấm nút được khoanh.",
                "hint_detailed": "Làm như sau:",
                "actions": ["Kéo chọn các cột được khoanh.", "Bấm lệnh trên thẻ Home."],
                "alternative": None,
                "feedback": [{"code": "wrong_value", "message": "Các cột chưa xóa đúng."}]
                if feedback
                else [],
                "reference_ids": [],
            }
            for title, ids in steps
        ],
    }


def test_generated_script_follows_the_procedure_and_passes_self_check(files: tuple[Path, Path]):
    llm = FakeLLM([RIGHT, plan_json(("Hiện cột E", ["p1"]), ("Xóa các cột trống", ["p2"]))])
    info = ExerciseInfo("bai-cot", "Bài cột", SHEET, PROMPT)
    stages: list[str] = []

    outcome = generate_script(analyze_exercise(*files, SHEET), info, [], llm, files, 3, stages.append)

    assert outcome.ok, outcome.remaining_issues
    assert stages == ["procedure", "llm", "self_check"]
    assert outcome.script is not None
    assert [s.get("operation", {}).get("action") for s in outcome.script["steps"]] == ["unhide", "delete"]
    assert [t["range"] for t in outcome.script["steps"][1]["targets"]["cells"]] == ["D2:E6"]
    assert outcome.report is not None and outcome.report["generation"]["procedure"]["operations"] == 2
    assert outcome.prompt_tokens == 200  # gồm cả lần AI chép quy trình


def test_procedure_that_never_matches_falls_back_to_the_diff(files: tuple[Path, Path]):
    analysis = analyze_exercise(*files, SHEET)
    ids = [c.id for c in analysis.changes]
    llm = FakeLLM(
        [FORGOT_UNHIDE_AND_E, FORGOT_UNHIDE_AND_E, plan_json(("Xóa các cột trống", ids), feedback=False)]
    )
    info = ExerciseInfo("bai-cot", "Bài cột", SHEET, PROMPT)

    outcome = generate_script(analysis, info, [], llm, files, 2)

    assert outcome.script is not None and all("operation" not in s for s in outcome.script["steps"])
    assert outcome.report is not None
    assert any("chưa dựng được" in w for w in outcome.report["warnings"])
