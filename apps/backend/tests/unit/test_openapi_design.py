"""Đặc tả API thiết kế (T3.7) luôn hợp lệ theo OpenAPI 3.1, kể cả tham chiếu tới lược đồ kịch bản."""

from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

SPEC = Path(__file__).resolve().parents[4] / "docs" / "thiet-ke" / "openapi.yaml"
METHODS = {"get", "post", "put", "patch", "delete"}


def load() -> dict:
    spec, base_uri = read_from_filename(str(SPEC))
    validate(spec, base_uri=base_uri)
    return spec


def test_design_spec_is_valid_openapi():
    assert load()["openapi"] == "3.1.0"


def test_every_operation_declares_roles_except_auth():
    spec = load()
    missing = [
        f"{method.upper()} {path}"
        for path, item in spec["paths"].items()
        for method, op in item.items()
        if method in METHODS and not path.startswith("/auth/") and "x-roles" not in op
    ]
    assert missing == []


def test_desktop_never_gets_generation_endpoints():
    """Desktop (vai trò student) không được gọi sinh kịch bản: Desktop không gọi AI."""
    spec = load()
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method in METHODS and "generation" in path:
                assert "student" not in op.get("x-roles", []), f"{method.upper()} {path}"
