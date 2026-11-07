"""Lỗi trả về dạng Problem với `code` ổn định (openapi.yaml components/schemas/Problem)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from tutor_backend.core.errors import ConflictError


class _Body(BaseModel):
    email: str
    age: int


def _add_probe_routes(app: FastAPI) -> None:
    @app.post("/__probe/validate")
    def validate(body: _Body) -> dict[str, str]:
        return {"email": body.email}

    @app.get("/__probe/conflict")
    def conflict() -> None:
        raise ConflictError("Mã bài đã tồn tại", code="exercise_code_taken")

    @app.get("/__probe/crash")
    def crash() -> None:
        raise RuntimeError("lỗi giả")


def test_unknown_route_is_problem_json(client: TestClient):
    response = client.get("/api/v1/khong-co")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "not_found"


def test_app_error_keeps_its_code(app: FastAPI, client: TestClient):
    _add_probe_routes(app)
    response = client.get("/__probe/conflict")
    assert response.status_code == 409
    assert response.json() == {"code": "exercise_code_taken", "message": "Mã bài đã tồn tại"}


def test_validation_error_lists_paths(app: FastAPI, client: TestClient):
    _add_probe_routes(app)
    response = client.post("/__probe/validate", json={"email": "a@b.c", "age": "nhiều"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert [e["path"] for e in body["errors"]] == ["/body/age"]


def test_unexpected_error_hides_details(app: FastAPI):
    _add_probe_routes(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__probe/crash")
    assert response.status_code == 500
    assert response.json() == {"code": "internal_error", "message": "Lỗi máy chủ, vui lòng thử lại sau"}
