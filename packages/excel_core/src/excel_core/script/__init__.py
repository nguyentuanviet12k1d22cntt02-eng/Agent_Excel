"""Đọc và kiểm tra kịch bản JSON theo 3 tầng (T4.5). Thiết kế: docs/thiet-ke/luoc-do-kich-ban.md mục 3.

- Tầng 1 + 2 (`validate_script`): chạy ở Backend trước khi lưu và ở Desktop sau khi tải; không cần file Excel.
- Tầng 3 (`self_check_files`): chỉ Backend, cần file đề và file đáp án.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from excel_core.script.cross_reference import cross_reference_issues
from excel_core.script.schema import ScriptIssue, find_schema_file, schema_issues
from excel_core.script.self_check import (
    CheckOutcome,
    SelfCheckReport,
    self_check,
    self_check_files,
    self_check_request,
)


@dataclass(frozen=True)
class ScriptValidation:
    """Kết quả tầng 1 và 2."""

    schema_issues: tuple[ScriptIssue, ...]
    cross_reference_issues: tuple[ScriptIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.schema_issues and not self.cross_reference_issues

    @property
    def schema_ok(self) -> bool:
        return not self.schema_issues


def validate_script(script: Mapping[str, Any]) -> ScriptValidation:
    """Tầng 1 (lược đồ); qua tầng 1 mới chạy tầng 2 (tham chiếu chéo), vì tầng 2 dựa vào cấu trúc đúng."""
    first = tuple(schema_issues(script))
    if first:
        return ScriptValidation(first, ())
    return ScriptValidation((), tuple(cross_reference_issues(script)))


def load_script(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


__all__ = [
    "CheckOutcome",
    "ScriptIssue",
    "ScriptValidation",
    "SelfCheckReport",
    "cross_reference_issues",
    "find_schema_file",
    "load_script",
    "schema_issues",
    "self_check",
    "self_check_files",
    "self_check_request",
    "validate_script",
]
