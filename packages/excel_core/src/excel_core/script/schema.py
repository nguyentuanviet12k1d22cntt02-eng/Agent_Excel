"""Tầng 1: kiểm kịch bản theo lược đồ JSON (schemas/tutor-script/v1/, luoc-do-kich-ban.md mục 3)."""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_FILE = Path("schemas") / "tutor-script" / "v1" / "tutor-script.schema.json"


@dataclass(frozen=True)
class ScriptIssue:
    """Một lỗi của kịch bản, có vị trí dạng JSON pointer (ví dụ "/steps/0/hints/2")."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path or '/'}: {self.message}"


def find_schema_file() -> Path:
    """Tìm lược đồ v1 từ thư mục chứa package đi lên.

    Khi phát triển là thư mục gốc repo; khi đóng gói Desktop (T7.x) phải kèm thư mục schemas/.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / SCHEMA_FILE
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Không tìm thấy {SCHEMA_FILE.as_posix()} ở các thư mục cha của excel_core")


@cache
def _validator(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def schema_issues(script: Any, schema_file: Path | None = None) -> list[ScriptIssue]:
    """Mọi chỗ kịch bản không khớp lược đồ, sắp theo vị trí."""
    validator = _validator(schema_file or find_schema_file())
    issues = [
        ScriptIssue("/" + "/".join(str(p) for p in error.absolute_path), error.message)
        for error in validator.iter_errors(script)
    ]
    return sorted(issues, key=lambda issue: issue.path)
