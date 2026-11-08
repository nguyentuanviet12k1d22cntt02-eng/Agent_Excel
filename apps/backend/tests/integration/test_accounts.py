"""Tài khoản, nhập CSV, lớp học và nhóm thực nghiệm (FR-W02)."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tutor_backend.models import Exercise, User


def test_admin_creates_and_lists_users(client: TestClient, make_user: Callable[..., User], auth):
    admin = make_user("admin")
    body = {
        "email": "Hoc.Vien@Test.vn",
        "full_name": "Nguyễn Văn A",
        "role": "student",
        "password": "matkhau123",
    }
    created = client.post("/api/v1/users", json=body, headers=auth(admin))
    assert created.status_code == 201
    assert created.json()["email"] == "hoc.vien@test.vn"
    assert "password" not in created.json() and "password_hash" not in created.json()
    again = client.post("/api/v1/users", json=body, headers=auth(admin))
    assert (again.status_code, again.json()["code"]) == (409, "email_taken")
    students = client.get("/api/v1/users", params={"role": "student"}, headers=auth(admin)).json()
    assert students["total"] == 1
    page = client.get("/api/v1/users", params={"page": 1, "page_size": 1}, headers=auth(admin)).json()
    assert (len(page["items"]), page["total"]) == (1, 2)


def test_user_payload_is_validated(client: TestClient, make_user: Callable[..., User], auth):
    admin = make_user("admin")
    bad = {"email": "khong-phai-email", "full_name": "", "role": "hieu_truong", "password": "123"}
    response = client.post("/api/v1/users", json=bad, headers=auth(admin))
    assert response.status_code == 422
    assert {e["path"] for e in response.json()["errors"]} == {
        "/body/email",
        "/body/full_name",
        "/body/role",
        "/body/password",
    }


def test_import_users_from_csv(client: TestClient, make_user: Callable[..., User], auth):
    admin = make_user("admin", email="admin@test.vn")
    csv_text = (
        "email,full_name,role,password\n"
        "hv1@test.vn,Trần Thị B,student,matkhau-hv1\n"
        "hv2@test.vn,Lê Văn C,,\n"  # vai trò mặc định student, mật khẩu tự tạo
        "admin@test.vn,Trùng,teacher,matkhau123\n"
        "sai-email,Không hợp lệ,student,\n"
        "hv3@test.vn,Phạm D,giam_doc,\n"
    )
    files = {"file": ("ds.csv", ("﻿" + csv_text).encode("utf-8"), "text/csv")}
    response = client.post("/api/v1/users/import", files=files, headers=auth(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 2
    assert [(s["line"], s["reason"]) for s in body["skipped"]] == [
        (4, "email đã có tài khoản"),
        (5, "email không hợp lệ"),
        (6, "vai trò không hợp lệ: giam_doc"),
    ]
    (generated,) = body["generated_passwords"]
    assert generated["email"] == "hv2@test.vn"
    login = client.post(
        "/api/v1/auth/login", json={"email": "hv2@test.vn", "password": generated["password"]}
    )
    assert login.status_code == 200


def test_import_rejects_csv_without_required_columns(
    client: TestClient, make_user: Callable[..., User], auth
):
    admin = make_user("admin")
    files = {"file": ("ds.csv", b"ten,lop\nA,B\n", "text/csv")}
    response = client.post("/api/v1/users/import", files=files, headers=auth(admin))
    assert (response.status_code, response.json()["code"]) == (422, "csv_columns")


def make_exercise(db: Session, owner: User, code: str = "b22-ham-tinh-tong") -> Exercise:
    exercise = Exercise(
        code=code,
        title="Hàm SUM",
        sheet_name="Bài 01",
        starter_file_path="de.xlsx",
        solution_file_path="dap-an.xlsx",
        created_by=owner.id,
    )
    db.add(exercise)
    db.commit()
    return exercise


def test_classes_members_and_assignments(
    client: TestClient, db: Session, make_user: Callable[..., User], auth
):
    admin, teacher, other_teacher = make_user("admin"), make_user("teacher"), make_user("teacher")
    student_a, student_b = make_user("student"), make_user("student")
    created = client.post(
        "/api/v1/classes",
        json={"name": "Tin học văn phòng K12", "teacher_id": str(teacher.id), "starts_on": "2027-01-04"},
        headers=auth(admin),
    )
    assert created.status_code == 201
    class_id = created.json()["id"]

    members = [
        {"student_id": str(student_a.id), "study_group": "experimental"},
        {"student_id": str(student_b.id), "study_group": "control"},
    ]
    assert (
        client.put(f"/api/v1/classes/{class_id}/members", json=members, headers=auth(admin)).status_code
        == 204
    )
    mine = client.get("/api/v1/classes", headers=auth(teacher)).json()
    assert [(c["id"], c["member_count"]) for c in mine] == [(class_id, 2)]
    assert client.get("/api/v1/classes", headers=auth(other_teacher)).json() == []

    exercise = make_exercise(db, teacher)
    assignment = {"exercise_id": str(exercise.id), "due_at": "2027-01-10T17:00:00+07:00"}
    url = f"/api/v1/classes/{class_id}/exercises"
    assert client.post(url, json=assignment, headers=auth(teacher)).status_code == 204
    denied = client.post(url, json=assignment, headers=auth(other_teacher))
    assert (denied.status_code, denied.json()["code"]) == (403, "not_class_teacher")


def test_members_must_be_students(client: TestClient, make_user: Callable[..., User], auth):
    admin, teacher = make_user("admin"), make_user("teacher")
    class_id = client.post(
        "/api/v1/classes", json={"name": "Lớp A", "teacher_id": str(teacher.id)}, headers=auth(admin)
    ).json()["id"]
    members = [{"student_id": str(teacher.id), "study_group": "control"}]
    response = client.put(f"/api/v1/classes/{class_id}/members", json=members, headers=auth(admin))
    assert (response.status_code, response.json()["code"]) == (422, "not_a_student")


def test_class_teacher_must_be_a_teacher(client: TestClient, make_user: Callable[..., User], auth):
    admin, student = make_user("admin"), make_user("student")
    response = client.post(
        "/api/v1/classes", json={"name": "Lớp B", "teacher_id": str(student.id)}, headers=auth(admin)
    )
    assert response.json()["code"] == "not_a_teacher"


def test_class_members_and_assignments_can_be_read_and_unassigned(
    client: TestClient, db: Session, make_user: Callable[..., User], auth
):
    admin, teacher, other_teacher = make_user("admin"), make_user("teacher"), make_user("teacher")
    student = make_user("student", full_name="Trần Thị B")
    class_id = client.post(
        "/api/v1/classes", json={"name": "Lớp A", "teacher_id": str(teacher.id)}, headers=auth(admin)
    ).json()["id"]
    members = [{"student_id": str(student.id), "study_group": "control"}]
    client.put(f"/api/v1/classes/{class_id}/members", json=members, headers=auth(admin))
    exercise = make_exercise(db, teacher)
    url = f"/api/v1/classes/{class_id}/exercises"
    client.post(url, json={"exercise_id": str(exercise.id)}, headers=auth(teacher))

    read = client.get(f"/api/v1/classes/{class_id}/members", headers=auth(teacher)).json()
    assigned = client.get(url, headers=auth(teacher)).json()

    assert [(m["full_name"], m["study_group"]) for m in read] == [("Trần Thị B", "control")]
    assert [(a["code"], a["published_revision"]) for a in assigned] == [(exercise.code, None)]
    assert client.get("/api/v1/classes", headers=auth(teacher)).json()[0]["teacher_name"] == teacher.full_name
    assert client.get(url, headers=auth(other_teacher)).status_code == 403
    assert client.delete(f"{url}/{exercise.id}", headers=auth(teacher)).status_code == 204
    assert client.get(url, headers=auth(teacher)).json() == []
    assert (
        client.delete(f"{url}/{exercise.id}", headers=auth(teacher)).json()["code"] == "assignment_not_found"
    )
