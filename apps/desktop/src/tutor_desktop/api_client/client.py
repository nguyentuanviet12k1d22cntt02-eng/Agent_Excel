"""Gọi API Backend (openapi.yaml). Lỗi problem+json đổi thành ApiError có thông báo tiếng Việt của Backend.

Access token giữ trong bộ nhớ; gặp 401 thì đổi refresh token lấy token mới một lần rồi gửi lại (như Web).
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

API_PREFIX = "/api/v1"
TIMEOUT_SECONDS = 60


class ApiError(RuntimeError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code = status, code


def _error(response: httpx.Response) -> ApiError:
    try:
        body = response.json()
    except ValueError:
        body = {}
    if isinstance(body, dict) and "message" in body:
        return ApiError(response.status_code, str(body.get("code", "")), str(body["message"]))
    return ApiError(
        response.status_code, f"http_{response.status_code}", f"Máy chủ báo lỗi {response.status_code}"
    )


class ApiClient:
    def __init__(self, base_url: str, transport: httpx.BaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url + API_PREFIX, timeout=TIMEOUT_SECONDS, transport=transport
        )
        self._access: str | None = None
        self._refresh: str | None = None
        self.user: Mapping[str, Any] | None = None

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------ đăng nhập
    def login(self, email: str, password: str) -> Mapping[str, Any]:
        try:
            response = self._http.post("/auth/login", json={"email": email, "password": password})
        except httpx.HTTPError as exc:
            raise ApiError(0, "network", f"Không kết nối được máy chủ {self.base_url}") from exc
        if response.status_code != httpx.codes.OK:
            raise _error(response)
        self._store_tokens(response.json())
        self.user = self.get("/auth/me")
        return self.user

    def _store_tokens(self, tokens: Mapping[str, Any]) -> None:
        self._access, self._refresh = tokens["access_token"], tokens["refresh_token"]

    def _refresh_tokens(self) -> bool:
        if not self._refresh:
            return False
        response = self._http.post("/auth/refresh", json={"refresh_token": self._refresh})
        if response.status_code != httpx.codes.OK:
            return False
        self._store_tokens(response.json())
        return True

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        def send() -> httpx.Response:
            headers = {"Authorization": f"Bearer {self._access}"} if self._access else {}
            try:
                return self._http.request(method, path, headers=headers, **kwargs)
            except httpx.HTTPError as exc:
                raise ApiError(0, "network", f"Không kết nối được máy chủ {self.base_url}") from exc

        response = send()
        if response.status_code == httpx.codes.UNAUTHORIZED and self._refresh_tokens():
            response = send()
        if response.is_error:
            raise _error(response)
        return response

    def get(self, path: str, **params: Any) -> Any:
        return self._send("GET", path, params=params or None).json()

    # ------------------------------------------------------------ chạy thử
    def exercises(self) -> list[Mapping[str, Any]]:
        return self.get("/exercises")

    def script_versions(self, exercise_id: str) -> list[Mapping[str, Any]]:
        return self.get(f"/exercises/{exercise_id}/scripts")

    def preview_bundle(self, version_id: str) -> Mapping[str, Any]:
        return self.get(f"/scripts/{version_id}/preview-bundle")

    def download_original_starter(self, exercise_id: str, target: Path) -> Path:
        response = self._send("GET", f"/exercises/{exercise_id}/original-starter-file")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        return target
