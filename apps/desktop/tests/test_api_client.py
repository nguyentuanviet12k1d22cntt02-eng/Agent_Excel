"""Client API của Desktop: đăng nhập, tự làm mới token, lỗi tiếng Việt của Backend."""

import json
from pathlib import Path

import httpx
import pytest

from tutor_desktop.api_client.client import ApiClient, ApiError


class FakeBackend:
    def __init__(self) -> None:
        self.issued = 0
        self.expired = False
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/api/v1")
        if path == "/auth/login":
            body = json.loads(request.content)
            if body["password"] != "matkhau123":
                return httpx.Response(
                    401, json={"code": "invalid_credentials", "message": "Email hoặc mật khẩu không đúng"}
                )
            return self.tokens()
        if path == "/auth/refresh":
            self.expired = False
            return self.tokens()
        if request.headers.get("Authorization") != f"Bearer access-{self.issued}" or self.expired:
            return httpx.Response(401, json={"code": "token_expired", "message": "Token đã hết hạn"})
        if path == "/auth/me":
            return httpx.Response(200, json={"email": "gv@tdmu.edu.vn", "role": "teacher"})
        if path == "/exercises/e1/original-starter-file":
            return httpx.Response(200, content=b"PK-file-de")
        if path == "/scripts/v1/preview-bundle":
            return httpx.Response(200, json={"version_id": "v1", "content": {}, "references": {}})
        return httpx.Response(404, json={"code": "not_found", "message": "Không tìm thấy"})

    def tokens(self) -> httpx.Response:
        self.issued += 1
        return httpx.Response(
            200, json={"access_token": f"access-{self.issued}", "refresh_token": "r", "expires_in": 3600}
        )


def client(backend: FakeBackend) -> ApiClient:
    return ApiClient("http://may-chu:8000", transport=httpx.MockTransport(backend.handler))


def test_login_then_calls_carry_token_and_refresh_once_when_expired(tmp_path: Path):
    backend = FakeBackend()
    api = client(backend)

    assert api.login("gv@tdmu.edu.vn", "matkhau123")["role"] == "teacher"
    backend.expired = True
    bundle = api.preview_bundle("v1")
    saved = api.download_original_starter("e1", tmp_path / "chay-thu" / "de.xlsx")

    assert bundle["version_id"] == "v1"
    assert saved.read_bytes() == b"PK-file-de"
    assert [r.url.path for r in backend.requests].count("/api/v1/auth/refresh") == 1


def test_errors_carry_backend_message():
    api = client(FakeBackend())
    with pytest.raises(ApiError) as wrong:
        api.login("gv@tdmu.edu.vn", "sai")
    assert (wrong.value.code, str(wrong.value)) == ("invalid_credentials", "Email hoặc mật khẩu không đúng")

    api.login("gv@tdmu.edu.vn", "matkhau123")
    with pytest.raises(ApiError) as missing:
        api.get("/khong-co")
    assert missing.value.status == 404


def test_network_error_is_explained():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    api = ApiClient("http://may-chu:8000", transport=httpx.MockTransport(refuse))
    with pytest.raises(ApiError, match="Không kết nối được máy chủ http://may-chu:8000"):
        api.login("gv@tdmu.edu.vn", "matkhau123")
