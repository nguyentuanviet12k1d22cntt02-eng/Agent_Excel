"""Client Desktop giả chạy trọn luồng học viên qua API (T5.7: "kiểm tra được bằng một client giả").

Kiểm cả thiết kế snapshot tham chiếu: Desktop chỉ có kịch bản + gói `references` (không có file đáp án) mà vẫn
chấm được bài bằng excel_core giống hệt Backend.
"""

import json
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from excel_core.checks import CheckContext, read_requests, run_check
from excel_core.readers import read_workbook
from excel_core.script import validate_script
from excel_core.snapshot import merge_requests, snapshot_from_dict
from tutor_backend.models import SurveyResponse, User

EXAMPLE = (
    Path(__file__).resolve().parents[4]
    / "schemas"
    / "tutor-script"
    / "v1"
    / "examples"
    / "b22-ham-tinh-tong.json"
)
FIXTURES = Path(__file__).resolve().parents[4] / "packages" / "excel_core" / "tests" / "fixtures" / "b22"
CODE = "b22-ham-tinh-tong"


@pytest.fixture
def world(client: TestClient, make_user: Callable[..., User], auth, exercise_files) -> dict:
    """Quản trị tạo lớp, giảng viên phát hành bài b22 và giao cho lớp (2 học viên: thực nghiệm, đối chứng)."""
    admin, teacher = make_user("admin"), make_user("teacher")
    tutor_student, control_student = make_user("student"), make_user("student")
    staff = auth(teacher)
    data = {"code": CODE, "title": "Hàm tính tổng SUM", "sheet_name": "Bài 01"}
    exercise = client.post("/api/v1/exercises", data=data, files=exercise_files("b22"), headers=staff).json()
    content = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    version = client.post(
        f"/api/v1/exercises/{exercise['id']}/scripts", json={"content": content}, headers=staff
    ).json()
    for action in ("submit", "approve", "publish"):
        assert client.post(f"/api/v1/scripts/{version['id']}/{action}", headers=staff).status_code == 200
    class_id = client.post(
        "/api/v1/classes",
        json={"name": "Lớp thực nghiệm", "teacher_id": str(teacher.id)},
        headers=auth(admin),
    ).json()["id"]
    members = [
        {"student_id": str(tutor_student.id), "study_group": "experimental"},
        {"student_id": str(control_student.id), "study_group": "control"},
    ]
    client.put(f"/api/v1/classes/{class_id}/members", json=members, headers=auth(admin))
    assignment = {"exercise_id": exercise["id"], "due_at": "2027-01-15T17:00:00+07:00"}
    client.post(f"/api/v1/classes/{class_id}/exercises", json=assignment, headers=staff)
    return {
        "student": auth(tutor_student),
        "control": auth(control_student),
        "exercise": exercise,
        "version_id": version["id"],
    }


def test_desktop_downloads_assignment_file_and_script(client: TestClient, world: dict, tmp_path: Path):
    (assignment,) = client.get("/api/v1/desktop/assignments", headers=world["student"]).json()
    assert (assignment["exercise_code"], assignment["revision"], assignment["mode"]) == (CODE, 1, "tutor")
    control = client.get("/api/v1/desktop/assignments", headers=world["control"]).json()
    assert control[0]["mode"] == "control"

    # Tải file đề rồi đọc mã bài nhúng trong file, như monitor của Desktop (FR-D02)
    starter = tmp_path / "de.xlsx"
    starter.write_bytes(client.get(assignment["starter_file_url"], headers=world["student"]).content)
    assert read_workbook(starter).exercise_id == CODE

    response = client.get(f"/api/v1/desktop/exercises/{CODE}/script", headers=world["student"])
    assert response.status_code == 200
    etag = response.headers["etag"]
    assert etag == f'"{world["version_id"]}"'
    script = response.json()
    assert validate_script(script["content"]).ok  # Desktop tự kiểm tầng 1–2 sau khi tải (FR-D03)
    assert set(script["references"]) == {"starter", "solution"}
    again = client.get(
        f"/api/v1/desktop/exercises/{CODE}/script", headers={**world["student"], "If-None-Match": etag}
    )
    assert again.status_code == 304


def _grade(content: dict, references: dict, workbook: Path) -> list[bool]:
    """Desktop chấm mọi điều kiện của mọi bước bằng excel_core, chỉ với gói references từ Backend."""
    sheet = content["exercise"]["sheet"]
    checks = [*content.get("global_checks", []), *(c for s in content["steps"] for c in s["checks"])]
    current = read_workbook(workbook, merge_requests([read_requests(checks, sheet)["current"]]))
    ctx = CheckContext(
        current=current,
        default_sheet=sheet,
        starter=snapshot_from_dict(references["starter"]),
        solution=snapshot_from_dict(references["solution"]),
    )
    return [run_check(check, ctx).passed for step in content["steps"] for check in step["checks"]]


def test_reference_snapshots_are_enough_to_grade_on_desktop(client: TestClient, world: dict):
    script = client.get(f"/api/v1/desktop/exercises/{CODE}/script", headers=world["student"]).json()
    finished = _grade(script["content"], script["references"], FIXTURES / "dap-an.xlsx")
    untouched = _grade(script["content"], script["references"], FIXTURES / "de.xlsx")
    assert all(finished)  # học viên làm đúng như đáp án: mọi điều kiện đạt
    assert not any(untouched)  # chưa làm gì: không điều kiện nào đạt


def test_unassigned_student_cannot_get_script(client: TestClient, world: dict, make_user, auth):
    stranger = auth(make_user("student"))
    response = client.get(f"/api/v1/desktop/exercises/{CODE}/script", headers=stranger)
    assert (response.status_code, response.json()["code"]) == (404, "script_not_found")


def _session_body(world: dict, **extra: object) -> dict:
    body = {
        "exercise_code": CODE,
        "script_version_id": world["version_id"],
        "mode": "tutor",
        "status": "in_progress",
        "started_at": "2027-01-10T08:00:00+07:00",
        "client_info": {
            "app_version": "0.1.0",
            "excel_version": "16.0",
            "office_ui_language": 1066,
            "dpi": 144,
        },
    }
    body.update(extra)
    return body


def test_session_progress_events_and_skills(client: TestClient, world: dict):
    headers = world["student"]
    session_id = str(uuid.uuid4())  # Desktop tự sinh id: tạo được cả khi mất mạng
    url = f"/api/v1/sessions/{session_id}"
    assert client.put(url, json=_session_body(world), headers=headers).status_code == 201
    assert client.put(url, json=_session_body(world, status="completed"), headers=headers).status_code == 200

    step = {"status": "done", "fail_count": 0, "max_hint_level": 0, "help_count": 0, "idle_seconds": 12}
    assert client.put(f"{url}/steps/s1_first_total", json=step, headers=headers).status_code == 204
    # Gửi lại bước đã xong (mạng chập chờn) không làm tính điểm hai lần
    assert client.put(f"{url}/steps/s1_first_total", json=step, headers=headers).status_code == 204
    hard = {**step, "max_hint_level": 4, "fail_count": 3}
    assert client.put(f"{url}/steps/s2_copy_down", json=hard, headers=headers).status_code == 204
    skills = client.get("/api/v1/desktop/skill-states", headers=headers).json()
    assert skills == {"formula_basics": "developing", "function_math_stat": "developing"}  # điểm 2 và 0
    unknown = client.put(f"{url}/steps/s9_khong_co", json=step, headers=headers)
    assert unknown.json()["code"] == "unknown_step"

    events = [
        {
            "seq": i,
            "occurred_at": "2027-01-10T08:01:00+07:00",
            "kind": "hint_shown",
            "step_id": "s1_first_total",
        }
        for i in range(5)
    ]
    first = client.post(f"{url}/events", json={"events": events}, headers=headers).json()
    resent = client.post(f"{url}/events", json={"events": events}, headers=headers).json()
    assert first == {"accepted": 5, "duplicates": 0}
    assert resent == {"accepted": 0, "duplicates": 5}


def test_session_cannot_switch_script_revision(client: TestClient, world: dict):
    headers = world["student"]
    url = f"/api/v1/sessions/{uuid.uuid4()}"
    client.put(url, json=_session_body(world), headers=headers)
    other = _session_body(world, script_version_id=str(uuid.uuid4()))
    assert client.put(url, json=other, headers=headers).json()["code"] == "script_mismatch"


def test_surveys_are_scored(client: TestClient, world: dict, db: Session):
    headers = world["student"]
    assert (
        client.post("/api/v1/surveys", json={"instrument": "paas", "answers": 5}, headers=headers).status_code
        == 201
    )
    sus = {"instrument": "sus", "answers": [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]}
    assert client.post("/api/v1/surveys", json=sus, headers=headers).status_code == 201
    bad = client.post("/api/v1/surveys", json={"instrument": "paas", "answers": 12}, headers=headers)
    assert bad.json()["code"] == "survey_invalid"
    scores = sorted(float(s) for s in db.scalars(select(SurveyResponse.score)))
    assert scores == [5.0, 100.0]  # SUS tốt nhất = 100
