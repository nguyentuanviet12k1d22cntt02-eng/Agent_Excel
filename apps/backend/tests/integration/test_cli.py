"""Lệnh quản trị `python -m tutor_backend create-admin`."""

import io

import pytest
from fastapi.testclient import TestClient

from tutor_backend.__main__ import main
from tutor_backend.core.config import Settings


def test_create_admin_then_login(
    client: TestClient,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr("sys.stdin", io.StringIO("matkhau-quan-tri\n"))
    argv = ["create-admin", "--email", "Admin@Trung-Tam.vn", "--full-name", "Quản trị", "--password-stdin"]
    assert main(argv, settings) == 0
    assert "Đã tạo tài khoản quản trị admin@trung-tam.vn" in capsys.readouterr().out
    login = client.post(
        "/api/v1/auth/login", json={"email": "admin@trung-tam.vn", "password": "matkhau-quan-tri"}
    )
    assert login.status_code == 200
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.json()["role"] == "admin"


def test_create_admin_rejects_short_password(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("sys.stdin", io.StringIO("123\n"))
    argv = ["create-admin", "--email", "a@b.vn", "--full-name", "A", "--password-stdin"]
    assert main(argv, settings) == 2
