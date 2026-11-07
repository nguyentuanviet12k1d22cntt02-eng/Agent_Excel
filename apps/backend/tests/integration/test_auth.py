"""Đăng nhập, token, phân quyền (T5.2: đăng nhập trả token; API chặn đúng khi sai quyền)."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tutor_backend.core.config import Settings
from tutor_backend.core.security import TokenType, create_token
from tutor_backend.models import User

PASSWORD = "matkhau-test-123"


def login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_returns_token_pair(client: TestClient, make_user: Callable[..., User]):
    make_user("teacher", email="gv.lan@test.vn")
    response = login(client, "GV.Lan@Test.vn")  # email không phân biệt hoa thường
    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 60 * 60
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["email"] == "gv.lan@test.vn"
    assert me.json()["role"] == "teacher"


def test_wrong_password_and_unknown_email_look_the_same(client: TestClient, make_user: Callable[..., User]):
    make_user("teacher", email="gv@test.vn")
    wrong_password = login(client, "gv@test.vn", "sai-mat-khau")
    unknown = login(client, "khong-co@test.vn")
    assert wrong_password.status_code == unknown.status_code == 401
    assert (
        wrong_password.json()
        == unknown.json()
        == {
            "code": "invalid_credentials",
            "message": "Email hoặc mật khẩu không đúng",
        }
    )


def test_disabled_account_cannot_login(client: TestClient, make_user: Callable[..., User]):
    make_user("student", email="hv@test.vn", is_active=False)
    assert login(client, "hv@test.vn").json()["code"] == "account_disabled"


def test_refresh_gives_new_access_token(client: TestClient, make_user: Callable[..., User]):
    make_user("student", email="hv@test.vn")
    tokens = login(client, "hv@test.vn").json()
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


def test_refresh_token_cannot_be_used_as_access_token(client: TestClient, make_user: Callable[..., User]):
    make_user("student", email="hv@test.vn")
    tokens = login(client, "hv@test.vn").json()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert (response.status_code, response.json()["code"]) == (401, "token_invalid")


def test_missing_and_expired_tokens(
    client: TestClient, app: FastAPI, settings: Settings, make_user: Callable[..., User]
):
    assert client.get("/api/v1/auth/me").json()["code"] == "not_authenticated"
    user = make_user("student")
    expired_settings = settings.model_copy(update={"access_token_minutes": -1})
    token = create_token(user.id, user.role, TokenType.ACCESS, expired_settings)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert (response.status_code, response.json()["code"]) == (401, "token_expired")
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_signed_with_other_secret_is_rejected(
    client: TestClient, settings: Settings, make_user: Callable[..., User]
):
    user = make_user("admin")
    other = settings.model_copy(update={"jwt_secret": SecretStr("khoa-cua-ke-gia-mao-dai-du-32-ky-tu")})
    forged = create_token(user.id, "admin", TokenType.ACCESS, other)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {forged}"})
    assert response.json()["code"] == "token_invalid"


def test_wrong_role_is_forbidden(client: TestClient, make_user: Callable[..., User], auth):
    teacher = make_user("teacher")
    response = client.get("/api/v1/users", headers=auth(teacher))
    assert (response.status_code, response.json()["code"]) == (403, "forbidden_role")
