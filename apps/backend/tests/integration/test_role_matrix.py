"""Quyền của từng API khớp `x-roles` trong docs/thiet-ke/openapi.yaml (T5.2: API chặn đúng khi sai quyền).

Đối chiếu tự động: mỗi route trong ứng dụng phải có trong đặc tả, và vai trò được phép (RoleGuard) phải đúng
bằng `x-roles` của thao tác đó. Thêm API mới mà quên ghi vào đặc tả, hoặc ghi sai quyền, thì test này đỏ.
"""

from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from tutor_backend.api.deps import RoleGuard
from tutor_backend.main import API_PREFIX

SPEC = yaml.safe_load(
    (Path(__file__).resolve().parents[4] / "docs" / "thiet-ke" / "openapi.yaml").read_text(encoding="utf-8")
)
PUBLIC = {("POST", "/auth/login"), ("POST", "/auth/refresh")}  # security: []
# /auth/me không ghi x-roles trong đặc tả: mọi vai trò đã đăng nhập
EVERY_ROLE = frozenset({"admin", "teacher", "student"})


def _spec_roles(method: str, path: str) -> frozenset[str] | None:
    operation = SPEC["paths"].get(path, {}).get(method.lower())
    if operation is None:
        return None
    return frozenset(operation.get("x-roles", EVERY_ROLE))


def _guard_roles(dependant: Dependant) -> frozenset[str] | None:
    for dependency in dependant.dependencies:
        if isinstance(dependency.call, RoleGuard):
            return frozenset(str(role) for role in dependency.call.roles)
        found = _guard_roles(dependency)
        if found is not None:
            return found
    return None


def _api_routes(app: FastAPI) -> list[tuple[str, str, APIRoute]]:
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith(API_PREFIX):
            for method in sorted(route.methods):
                routes.append((method, route.path.removeprefix(API_PREFIX), route))
    return routes


def test_every_route_is_documented_with_matching_roles(app: FastAPI):
    problems = []
    for method, path, route in _api_routes(app):
        spec = _spec_roles(method, path)
        if spec is None:
            problems.append(f"{method} {path}: chưa có trong openapi.yaml")
            continue
        guard = _guard_roles(route.dependant)
        if (method, path) in PUBLIC:
            if guard is not None:
                problems.append(f"{method} {path}: API công khai nhưng có kiểm vai trò")
        elif guard != spec:
            problems.append(f"{method} {path}: code cho {sorted(guard or [])}, đặc tả ghi {sorted(spec)}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("path", ["/users", "/classes"])
def test_student_is_blocked_from_staff_api(client, make_user, auth, path: str):
    response = client.get(f"{API_PREFIX}{path}", headers=auth(make_user("student")))
    assert response.status_code == 403
