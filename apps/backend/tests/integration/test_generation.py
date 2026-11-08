"""Sinh kịch bản chạy nền qua API, dùng LLM giả (T5.5; FR-W06)."""

import copy
import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tutor_backend.ai.llm_client import LLMError
from tutor_backend.models import GenerationJob, User
from tutor_backend.models.enums import JobStatus


def create_b22(client: TestClient, headers, exercise_files) -> dict:
    data = {"code": "b22-ham-tinh-tong", "title": "Hàm tính tổng SUM", "sheet_name": "Bài 01"}
    response = client.post("/api/v1/exercises", data=data, files=exercise_files("b22"), headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def generate(client: TestClient, exercise_id: str, headers, body: dict | None = None) -> dict:
    response = client.post(
        f"/api/v1/exercises/{exercise_id}/generation-jobs", json=body or {}, headers=headers
    )
    assert response.status_code == 202, response.json()
    return response.json()


def test_generation_saves_a_valid_draft(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files, fake_llm, b22_plan_factory
):
    headers = auth(make_user("teacher"))
    exercise = create_b22(client, headers, exercise_files)
    llm = fake_llm([b22_plan_factory()])
    job = generate(client, exercise["id"], headers, {"instructions": "Nhấn mạnh sao chép công thức."})
    assert (job["status"], job["attempts"], job["model"]) == ("succeeded", 1, "mercury-3")
    assert (job["prompt_tokens"], job["completion_tokens"]) == (1000, 2000)
    assert "Nhấn mạnh sao chép công thức." in llm.requests[0]
    assert "C9" not in llm.requests[0]  # prompt không chứa địa chỉ ô

    detail = client.get(f"/api/v1/exercises/{exercise['id']}", headers=headers).json()
    latest = detail["latest_version"]
    assert (latest["id"], latest["status"], latest["origin"], latest["revision"]) == (
        job["result_version_id"],
        "draft",
        "ai",
        1,
    )
    polled = client.get(f"/api/v1/generation-jobs/{job['id']}", headers=headers).json()
    assert polled == job


def test_generation_repairs_plan_with_issues(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files, fake_llm, b22_plan_factory
):
    headers = auth(make_user("teacher"))
    exercise = create_b22(client, headers, exercise_files)
    broken = b22_plan_factory()
    broken["steps"][0]["hint_tool"] = "Gõ =SUM(C9:E9) vào ô F9."  # địa chỉ ô trong chữ gợi ý
    broken["steps"].pop()  # bỏ sót thay đổi c2
    llm = fake_llm([broken, b22_plan_factory()])
    job = generate(client, exercise["id"], headers)
    assert (job["status"], job["attempts"]) == ("succeeded", 2)
    repair_request = llm.requests[1]
    assert "Thay đổi c2 chưa thuộc bước nào" in repair_request
    assert '"F9"' in repair_request or "F9" in repair_request


def test_generation_keeps_draft_when_issues_remain(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files, fake_llm, b22_plan_factory
):
    headers = auth(make_user("teacher"))
    exercise = create_b22(client, headers, exercise_files)
    broken = b22_plan_factory()
    broken["steps"].pop()
    fake_llm([copy.deepcopy(broken) for _ in range(3)])
    job = generate(client, exercise["id"], headers)
    assert (job["status"], job["attempts"]) == ("succeeded", 3)
    version = client.get(f"/api/v1/exercises/{exercise['id']}", headers=headers).json()["latest_version"]
    assert version is not None  # vẫn lưu nháp để giảng viên sửa, kèm lỗi trong báo cáo


def test_llm_failure_marks_job_failed(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files, fake_llm
):
    headers = auth(make_user("teacher"))
    exercise = create_b22(client, headers, exercise_files)
    fake_llm([LLMError("Dịch vụ AI không trả lời kịp (quá thời gian chờ)")])
    job = generate(client, exercise["id"], headers)
    assert (job["status"], job["error"]) == ("failed", "Dịch vụ AI không trả lời kịp (quá thời gian chờ)")
    assert job["result_version_id"] is None


def test_missing_api_key_is_reported(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files
):
    headers = auth(make_user("teacher"))
    exercise = create_b22(client, headers, exercise_files)
    job = generate(client, exercise["id"], headers)  # LLM thật, settings test không có key
    assert (job["status"], job["error"]) == ("failed", "Chưa cấu hình LLM_API_KEY trong apps/backend/.env")


def test_cannot_start_second_generation_while_running(
    client: TestClient, db: Session, make_user: Callable[..., User], auth, exercise_files
):
    teacher = make_user("teacher")
    headers = auth(teacher)
    exercise = create_b22(client, headers, exercise_files)
    db.add(
        GenerationJob(
            exercise_id=uuid.UUID(exercise["id"]),
            requested_by=teacher.id,
            status=JobStatus.RUNNING,
            model="m",
        )
    )
    db.commit()
    response = client.post(f"/api/v1/exercises/{exercise['id']}/generation-jobs", json={}, headers=headers)
    assert (response.status_code, response.json()["code"]) == (409, "generation_in_progress")


def test_job_history_lists_newest_first_with_result_version(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files, fake_llm, b22_plan_factory
):
    headers = auth(make_user("teacher"))
    exercise = create_b22(client, headers, exercise_files)
    url = f"/api/v1/exercises/{exercise['id']}/generation-jobs"
    assert client.get(url, headers=headers).json() == []
    fake_llm([b22_plan_factory()])
    first = generate(client, exercise["id"], headers, {"instructions": "Ngắn gọn."})
    fake_llm([LLMError("mất kết nối")])  # lần sinh thứ hai thất bại

    second = generate(client, exercise["id"], headers)

    history = client.get(url, headers=headers).json()
    assert [j["id"] for j in history] == [second["id"], first["id"]]
    assert history[1]["result_version_id"] == first["result_version_id"] is not None
    assert (history[1]["instructions"], history[0]["status"]) == ("Ngắn gọn.", "failed")
    assert history[1]["created_at"] <= history[1]["started_at"] <= history[1]["finished_at"]
    student = auth(make_user("student", email="hv@tdmu.edu.vn"))
    assert client.get(url, headers=student).status_code == 403
