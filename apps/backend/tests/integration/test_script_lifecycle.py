"""Vòng đời kịch bản: lưu revision, gửi duyệt, duyệt, từ chối, phát hành, tải file đề (T5.6)."""

import copy
import io
import json
from collections.abc import Callable
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

from tutor_backend.models import User

EXAMPLE = (
    Path(__file__).resolve().parents[4]
    / "schemas"
    / "tutor-script"
    / "v1"
    / "examples"
    / "b22-ham-tinh-tong.json"
)


@pytest.fixture
def b22_script() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def setup(client: TestClient, make_user: Callable[..., User], auth, exercise_files):
    teacher = make_user("teacher")
    headers = auth(teacher)
    data = {"code": "b22-ham-tinh-tong", "title": "Hàm tính tổng SUM", "sheet_name": "Bài 01"}
    exercise = client.post(
        "/api/v1/exercises", data=data, files=exercise_files("b22"), headers=headers
    ).json()
    return headers, exercise


def save(client: TestClient, setup, content: dict, parent: str | None = None):
    headers, exercise = setup
    body = {"content": content, "parent_version_id": parent}
    return client.post(f"/api/v1/exercises/{exercise['id']}/scripts", json=body, headers=headers)


def act(client: TestClient, setup, version_id: str, action: str, body: dict | None = None):
    headers, _ = setup
    return client.post(f"/api/v1/scripts/{version_id}/{action}", json=body, headers=headers)


def test_full_lifecycle_and_starter_file(client: TestClient, setup, b22_script: dict):
    headers, exercise = setup
    saved = save(client, setup, b22_script)
    assert saved.status_code == 201, saved.json()
    version = saved.json()
    assert (version["status"], version["origin"], version["revision"]) == ("draft", "teacher", 1)
    assert version["content"]["revision"] == 1
    assert version["self_check_report"]["schema_ok"] is True
    assert client.get(f"/api/v1/exercises/{exercise['id']}/starter-file", headers=headers).status_code == 404

    assert act(client, setup, version["id"], "submit").json()["status"] == "pending_review"
    assert act(client, setup, version["id"], "approve").json()["status"] == "approved"
    published = act(client, setup, version["id"], "publish").json()
    assert published["status"] == "published" and published["published_at"]

    download = client.get(f"/api/v1/exercises/{exercise['id']}/starter-file", headers=headers)
    assert download.status_code == 200
    assert 'filename="b22-ham-tinh-tong.xlsx"' in download.headers["content-disposition"]
    props = {
        p.name: p.value for p in openpyxl.load_workbook(io.BytesIO(download.content)).custom_doc_props.props
    }
    assert props == {"tutor_exercise_id": "b22-ham-tinh-tong", "tutor_script_revision": "1"}


def test_publishing_new_revision_archives_old_one(client: TestClient, setup, b22_script: dict):
    first = save(client, setup, b22_script).json()
    for action in ("submit", "approve", "publish"):
        act(client, setup, first["id"], action)
    edited = copy.deepcopy(b22_script)
    edited["steps"][0]["task"] = "Tính Tổng tiền ngày đầu tiên bằng hàm SUM (bản sửa)."
    second = save(client, setup, edited, parent=first["id"]).json()
    assert (second["revision"], second["origin"], second["parent_version_id"]) == (2, "teacher", first["id"])
    for action in ("submit", "approve", "publish"):
        act(client, setup, second["id"], action)
    headers, exercise = setup
    versions = client.get(f"/api/v1/exercises/{exercise['id']}/scripts", headers=headers).json()
    assert [(v["revision"], v["status"]) for v in versions] == [(2, "published"), (1, "archived")]
    detail = client.get(f"/api/v1/exercises/{exercise['id']}", headers=headers).json()
    assert detail["published_version"]["revision"] == 2


def test_invalid_script_is_rejected_with_paths(client: TestClient, setup, b22_script: dict):
    broken = copy.deepcopy(b22_script)
    broken["steps"][0]["hints"].pop()
    response = save(client, setup, broken)
    assert (response.status_code, response.json()["code"]) == (422, "script_invalid")
    assert any(e["path"].startswith("/steps/0/hints") for e in response.json()["errors"])


def test_script_for_another_exercise_is_rejected(client: TestClient, setup, b22_script: dict):
    other = copy.deepcopy(b22_script)
    other["exercise"]["id"] = "b09-du-lieu-dang-so"
    assert save(client, setup, other).json()["code"] == "exercise_mismatch"


def test_submit_requires_passing_self_check(client: TestClient, setup, b22_script: dict):
    wrong = copy.deepcopy(b22_script)
    # Hợp lệ lược đồ nhưng sai trên file đáp án: hàm yêu cầu không phải hàm đáp án dùng
    wrong["steps"][0]["checks"][1]["functions"] = ["AVERAGE"]
    version = save(client, setup, wrong).json()
    response = act(client, setup, version["id"], "submit")
    assert (response.status_code, response.json()["code"]) == (409, "self_check_failed")
    assert any("không đạt trên đáp án" in e["message"] for e in response.json()["errors"])
    headers, _ = setup
    status = client.get(f"/api/v1/scripts/{version['id']}", headers=headers).json()["status"]
    assert status == "draft"


def test_invalid_transitions_and_reject(client: TestClient, setup, b22_script: dict):
    version = save(client, setup, b22_script).json()
    skipped = act(client, setup, version["id"], "approve")
    assert (skipped.status_code, skipped.json()["code"]) == (409, "invalid_transition")
    assert act(client, setup, version["id"], "publish").json()["code"] == "invalid_transition"
    act(client, setup, version["id"], "submit")
    rejected = act(
        client, setup, version["id"], "reject", {"note": "Gợi ý cấp 2 nên nhắc nút AutoSum."}
    ).json()
    assert (rejected["status"], rejected["review_note"]) == ("draft", "Gợi ý cấp 2 nên nhắc nút AutoSum.")
    # Ghi người và thời điểm duyệt/từ chối (FR-W10): Web hiện tên, không cần quyền xem danh sách tài khoản
    assert (rejected["reviewed_by_name"], rejected["created_by_name"]) == ("Người dùng teacher",) * 2
    assert rejected["reviewed_at"] is not None


def test_ai_draft_edited_by_teacher_is_marked(client: TestClient, setup, fake_llm, b22_plan_factory):
    headers, exercise = setup
    fake_llm([b22_plan_factory()])
    job = client.post(f"/api/v1/exercises/{exercise['id']}/generation-jobs", json={}, headers=headers).json()
    ai_version = client.get(f"/api/v1/scripts/{job['result_version_id']}", headers=headers).json()
    edited = save(client, setup, ai_version["content"], parent=ai_version["id"]).json()
    assert (edited["origin"], edited["revision"]) == ("ai_edited", 2)


def test_self_check_endpoint_returns_report(client: TestClient, setup, b22_script: dict):
    headers, _ = setup
    version = save(client, setup, b22_script).json()
    report = client.post(f"/api/v1/scripts/{version['id']}/self-check", headers=headers).json()
    assert report["schema_ok"] is True
    assert report["diff_coverage"] == 1.0
    assert report["errors"] == []


def test_students_get_starter_file_only_when_assigned(
    client: TestClient, setup, b22_script: dict, make_user: Callable[..., User], auth
):
    headers, exercise = setup
    version = save(client, setup, b22_script).json()
    for action in ("submit", "approve", "publish"):
        act(client, setup, version["id"], action)
    student = make_user("student")
    url = f"/api/v1/exercises/{exercise['id']}/starter-file"
    assert client.get(url, headers=auth(student)).status_code == 404
    admin = make_user("admin")
    me = client.get("/api/v1/auth/me", headers=headers).json()
    class_id = client.post(
        "/api/v1/classes", json={"name": "Lớp thử", "teacher_id": me["id"]}, headers=auth(admin)
    ).json()["id"]
    members = [{"student_id": str(student.id), "study_group": "experimental"}]
    client.put(f"/api/v1/classes/{class_id}/members", json=members, headers=auth(admin))
    client.post(
        f"/api/v1/classes/{class_id}/exercises", json={"exercise_id": exercise["id"]}, headers=headers
    )
    assert client.get(url, headers=auth(student)).status_code == 200
