"""Xem trước trang tính cho lưới mô phỏng trên Web (T6.4)."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from tutor_backend.models import User


def create_b09(client: TestClient, headers, exercise_files) -> dict:
    data = {
        "code": "b09-du-lieu-dang-so",
        "title": "Định dạng dữ liệu số",
        "sheet_name": "2. Bang_Ke_Ban_Hang",
    }
    response = client.post("/api/v1/exercises", data=data, files=exercise_files("b09"), headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def cells_by_address(preview: dict) -> dict[str, dict]:
    return {cell["address"]: cell for cell in preview["cells"]}


def test_preview_shows_starter_and_solution_of_work_sheet(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files
):
    headers = auth(make_user("teacher"))
    exercise = create_b09(client, headers, exercise_files)
    url = f"/api/v1/exercises/{exercise['id']}/sheet-preview"

    starter = client.get(url, headers=headers).json()
    solution = client.get(url, params={"file": "solution"}, headers=headers).json()

    assert (starter["sheet"], starter["range"], starter["truncated"]) == (
        "2. Bang_Ke_Ban_Hang",
        "A1:I22",
        False,
    )
    assert "2. Bang_Ke_Ban_Hang" in starter["sheet_names"]
    assert "B2:I2" in starter["merged"]
    assert "F10" not in cells_by_address(starter)  # đề: học viên phải nhập số lượng
    f10, h10 = cells_by_address(solution)["F10"], cells_by_address(solution)["H10"]
    assert (f10["text"], f10["number"], f10["align"]) == ("1.250", True, "right")
    assert (h10["text"], h10["formula"]) == ("4.375,00", "=F10*G10")


def test_preview_other_sheet_and_errors(
    client: TestClient, make_user: Callable[..., User], auth, exercise_files
):
    headers = auth(make_user("teacher"))
    exercise = create_b09(client, headers, exercise_files)
    url = f"/api/v1/exercises/{exercise['id']}/sheet-preview"

    missing = client.get(url, params={"sheet": "Không có"}, headers=headers)
    wrong_file = client.get(url, params={"file": "other"}, headers=headers)
    student = client.get(url, headers=auth(make_user("student", email="hv@tdmu.edu.vn")))

    assert (missing.status_code, missing.json()["code"]) == (422, "sheet_not_found")
    assert wrong_file.status_code == 422
    assert student.status_code == 403
