"""Học liệu: giáo trình và bài tập (T5.3: tải lên và tải về được; FR-W03 – FR-W05)."""

import io
import zipfile
from collections.abc import Callable
from pathlib import Path

import openpyxl
from fastapi.testclient import TestClient

from tutor_backend.core.config import Settings
from tutor_backend.models import User

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def minimal_docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
        archive.writestr("[Content_Types].xml", "<Types/>")
    return buffer.getvalue()


def xlsx_bytes(cells: dict[str, object], sheet: str = "Bài 01") -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    for address, value in cells.items():
        ws[address] = value
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def upload_textbook(client: TestClient, headers, data: bytes = MINIMAL_PDF, name: str = "gt.pdf"):
    return client.post(
        "/api/v1/textbooks",
        data={"title": "Giáo trình Excel cơ bản"},
        files={"file": (name, data)},
        headers=headers,
    )


def test_textbook_upload_list_delete(
    client: TestClient, settings: Settings, make_user: Callable[..., User], auth
):
    teacher = make_user("teacher")
    created = upload_textbook(client, auth(teacher))
    assert created.status_code == 202
    body = created.json()
    assert (body["file_type"], body["status"], body["chunk_count"]) == ("pdf", "uploaded", 0)
    docx = upload_textbook(client, auth(teacher), minimal_docx(), "gt.docx").json()
    assert docx["file_type"] == "docx"
    listed = client.get("/api/v1/textbooks", headers=auth(teacher)).json()
    assert {t["id"] for t in listed} == {body["id"], docx["id"]}
    stored = list((settings.files_dir / "textbooks").iterdir())
    assert len(stored) == 2
    assert client.delete(f"/api/v1/textbooks/{body['id']}", headers=auth(teacher)).status_code == 204
    assert client.get(f"/api/v1/textbooks/{body['id']}", headers=auth(teacher)).status_code == 404
    assert len(list((settings.files_dir / "textbooks").iterdir())) == 1


def test_textbook_type_is_checked_by_content(client: TestClient, make_user: Callable[..., User], auth):
    teacher = make_user("teacher")
    # Đổi đuôi .pdf cho file Excel không qua được: nhận dạng theo nội dung
    response = upload_textbook(client, auth(teacher), xlsx_bytes({"A1": 1}), "gia-mao.pdf")
    assert (response.status_code, response.json()["code"]) == (422, "file_type_invalid")


def create_exercise(client: TestClient, headers, files, code: str = "b09-du-lieu-dang-so", **form):
    data = {"code": code, "title": "Định dạng dữ liệu số", "sheet_name": "2. Bang_Ke_Ban_Hang", **form}
    return client.post("/api/v1/exercises", data=data, files=files, headers=headers)


def test_create_exercise_from_b09(
    client: TestClient, settings: Settings, make_user: Callable[..., User], auth, exercise_files
):
    teacher = make_user("teacher")
    textbook = upload_textbook(client, auth(teacher)).json()
    response = create_exercise(
        client,
        auth(teacher),
        exercise_files("b09"),
        prompt_text="Định dạng các cột số",
        textbook_ids=[textbook["id"]],
    )
    assert response.status_code == 201, response.json()
    exercise = response.json()
    assert exercise["warnings"] == []
    assert exercise["textbook_ids"] == [textbook["id"]]
    assert exercise["latest_version"] is None
    folder = settings.files_dir / "exercises" / exercise["id"]
    assert {p.name for p in folder.iterdir()} == {"de.xlsx", "dap-an.xlsx"}

    again = create_exercise(client, auth(teacher), exercise_files("b09"))
    assert (again.status_code, again.json()["code"]) == (409, "exercise_code_taken")
    linked = client.delete(f"/api/v1/textbooks/{textbook['id']}", headers=auth(teacher))
    assert (linked.status_code, linked.json()["code"]) == (409, "textbook_in_use")


def test_create_exercise_requires_work_sheet(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files
):
    response = create_exercise(
        client, auth(make_user("teacher")), exercise_files("b09"), sheet_name="Không có"
    )
    assert (response.status_code, response.json()["code"]) == (422, "sheet_not_found")


def test_solution_must_be_calculated_by_excel(client: TestClient, make_user: Callable[..., User], auth):
    files = {
        "starter_file": ("de.xlsx", xlsx_bytes({"A1": 2, "A2": 3}), XLSX),
        "solution_file": ("dap-an.xlsx", xlsx_bytes({"A1": 2, "A2": 3, "A3": "=A1+A2"}), XLSX),
    }
    response = create_exercise(client, auth(make_user("teacher")), files, sheet_name="Bài 01")
    assert (response.status_code, response.json()["code"]) == (422, "solution_not_calculated")
    assert response.json()["errors"][0]["message"] == "Bài 01!A3"


def test_layout_mismatch_is_a_warning(client: TestClient, make_user: Callable[..., User], auth):
    files = {
        "starter_file": ("de.xlsx", xlsx_bytes({"A1": "Tên hàng", "B1": "Số lượng"}), XLSX),
        "solution_file": ("dap-an.xlsx", xlsx_bytes({"A1": "Mặt hàng", "B1": "Số lượng", "B2": 5}), XLSX),
    }
    response = create_exercise(client, auth(make_user("teacher")), files, sheet_name="Bài 01")
    assert response.status_code == 201
    assert response.json()["warnings"] == [
        "Ô chữ khác nhau giữa đề và đáp án ở A1: kiểm tra hai file có cùng bố cục"
    ]


def test_wrong_file_type_for_exercise(client: TestClient, make_user: Callable[..., User], auth):
    files = {
        "starter_file": ("de.xlsx", MINIMAL_PDF, XLSX),
        "solution_file": ("dap-an.xlsx", xlsx_bytes({"A1": 1}), XLSX),
    }
    response = create_exercise(client, auth(make_user("teacher")), files)
    assert response.json()["errors"][0]["path"] == "/starter_file"


def test_upload_size_limit(app, client: TestClient, make_user: Callable[..., User], auth):
    app.state.settings = app.state.settings.model_copy(update={"max_upload_mb": 1})
    response = upload_textbook(client, auth(make_user("teacher")), MINIMAL_PDF + b"0" * (1024 * 1024))
    assert (response.status_code, response.json()["code"]) == (422, "file_too_large")


def test_exercise_list_update_delete(
    client: TestClient, settings: Settings, make_user: Callable[..., User], auth, exercise_files
):
    teacher = make_user("teacher")
    b09 = create_exercise(client, auth(teacher), exercise_files("b09")).json()
    create_exercise(
        client, auth(teacher), exercise_files("b22"), code="b22-ham-tinh-tong", sheet_name="Bài 01"
    )
    found = client.get("/api/v1/exercises", params={"q": "B22"}, headers=auth(teacher)).json()
    assert [e["code"] for e in found] == ["b22-ham-tinh-tong"]

    patched = client.patch(
        f"/api/v1/exercises/{b09['id']}", json={"title": "Bài 09 — định dạng số"}, headers=auth(teacher)
    )
    assert patched.json()["title"] == "Bài 09 — định dạng số"
    assert client.delete(f"/api/v1/exercises/{b09['id']}", headers=auth(teacher)).status_code == 204
    assert not Path(settings.files_dir / "exercises" / b09["id"]).exists()


def test_students_cannot_manage_materials(client: TestClient, make_user: Callable[..., User], auth):
    student = make_user("student")
    assert client.get("/api/v1/exercises", headers=auth(student)).status_code == 403
    assert upload_textbook(client, auth(student)).status_code == 403
