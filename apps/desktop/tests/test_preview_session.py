"""Phiên chạy thử: chấm theo bước, tự chuyển bước, gợi ý từng cấp, nhắc khi phá dữ liệu gốc."""

import json
from dataclasses import replace
from pathlib import Path

from excel_core.checks import CheckStatus, reference_requests
from excel_core.readers import full_request, read_workbook
from excel_core.snapshot import CellSnapshot, snapshot_to_dict
from tutor_desktop.agent.preview_session import PreviewSession

REPO = Path(__file__).resolve().parents[3]
B22 = REPO / "packages" / "excel_core" / "tests" / "fixtures" / "b22"
SCRIPT = json.loads(
    (REPO / "schemas/tutor-script/v1/examples/b22-ham-tinh-tong.json").read_text(encoding="utf-8")
)


def session() -> PreviewSession:
    checks = [*SCRIPT["global_checks"], *(c for s in SCRIPT["steps"] for c in s["checks"])]
    files = {"starter": B22 / "de.xlsx", "solution": B22 / "dap-an.xlsx"}
    references = {
        source: snapshot_to_dict(read_workbook(files[source], request))
        for source, request in reference_requests(checks, SCRIPT["exercise"]["sheet"]).items()
    }
    return PreviewSession(SCRIPT, references)


def read(name: str):
    path = B22 / name
    return read_workbook(path, full_request(path))


def test_untouched_file_stays_on_first_step_without_feedback():
    preview = session()

    result = preview.evaluate(read("de.xlsx"))

    assert (result.step_index, result.status, result.advanced) == (0, CheckStatus.FAILED, False)
    assert result.feedback is None  # chưa sửa gì: không nhắc lỗi
    assert result.global_violations == ()


def test_finished_file_walks_through_every_step():
    preview = session()
    solution = read("dap-an.xlsx")

    passed = []
    while not preview.finished:
        result = preview.evaluate(solution)
        assert result.advanced
        passed.append(result.step_index)

    assert passed == [0, 1, 2]
    assert preview.done == {s["id"] for s in SCRIPT["steps"]}
    assert preview.evaluate(solution).finished


def test_feedback_follows_error_code_after_a_change():
    preview = session()
    starter = read("de.xlsx")
    sheet = starter.sheets["Bài 01"]
    # Gõ =C9+D9+E9 (không dùng SUM): đúng giá trị nhưng sai cách
    f9 = CellSnapshot(
        value=95000.0, value_kind="number", formula="=C9+D9+E9", formula_r1c1="=RC[-3]+RC[-2]+RC[-1]"
    )
    typed = replace(starter, sheets={"Bài 01": replace(sheet, cells={**sheet.cells, "F9": f9})})
    preview.note_change()

    result = preview.evaluate(typed)

    assert result.status == CheckStatus.FAILED
    assert result.feedback is not None and result.feedback["code"] == "used_operator_instead"


def test_overwriting_source_data_is_reported_at_once():
    preview = session()
    starter = read("de.xlsx")
    sheet = starter.sheets["Bài 01"]
    broken = replace(
        starter,
        sheets={
            "Bài 01": replace(
                sheet, cells={**sheet.cells, "C9": CellSnapshot(value=1.0, value_kind="number")}
            )
        },
    )

    result = preview.evaluate(broken)

    assert [v.check["type"] for v in result.global_violations] == ["data_unchanged"]


def test_hints_go_up_one_level_at_a_time_and_location_level_highlights():
    preview = session()

    levels = [preview.next_hint()["level"] for _ in range(5)]  # type: ignore[index]

    assert levels == [1, 2, 3, 4, 4]
    marks = preview.highlights()
    assert [m.range or m.control for m in marks] == ["F9", "C9:E9", "AutoSum"]
    targets = preview.highlights(show_targets=True)
    assert [(m.range, m.role) for m in targets[:2]] == [("F9", "target"), ("C9:E9", "source")]


def test_navigation_resets_hint_level():
    preview = session()
    preview.next_hint()
    preview.skip()
    assert (preview.index, preview.hint_level) == (1, 0)
    preview.back()
    preview.back()
    assert preview.index == 0
    preview.go_to(99)
    assert preview.finished and preview.highlights() == []
