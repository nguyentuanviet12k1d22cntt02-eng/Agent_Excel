"""Tầng 2: ràng buộc mà lược đồ JSON không diễn tả được (luoc-do-kich-ban.md mục 3).

Chạy được khi không có file Excel: Backend trước khi lưu, Desktop sau khi tải.
"""

from collections import Counter
from collections.abc import Iterator, Mapping
from typing import Any

from excel_core.address import AddressError, parse_range
from excel_core.checks import codes_for
from excel_core.script.schema import ScriptIssue

type Script = Mapping[str, Any]


def _duplicates(values: list[str]) -> set[str]:
    return {value for value, count in Counter(values).items() if count > 1}


def _check_issues(path: str, check: Mapping[str, Any]) -> Iterator[ScriptIssue]:
    expected = check.get("expected", {})
    if expected.get("from") == "range" and "range" in check:
        source, target = parse_range(expected["range"]), parse_range(check["range"])
        if (source.width, source.height) != (target.width, target.height):
            yield ScriptIssue(f"{path}/expected", f"vùng {source} khác kích thước vùng kiểm {target}")
    if check.get("type") == "visible_rows" and expected.get("from") != "solution":
        yield ScriptIssue(f"{path}/expected", "visible_rows chỉ nhận expected: {from: solution}")


def _target_issues(path: str, step: Mapping[str, Any], default_sheet: str) -> Iterator[ScriptIssue]:
    """Vùng/nút được khoanh ở gợi ý cấp 3 phải nằm trong targets của bước."""
    targets = [
        (cell.get("sheet") or default_sheet, parse_range(cell["range"])) for cell in step["targets"]["cells"]
    ]
    controls = {ui["control"] for ui in step["targets"].get("ui", [])}
    for index, hint in enumerate(step["hints"]):
        for h, item in enumerate(hint.get("highlight", [])):
            where = f"{path}/hints/{index}/highlight/{h}"
            if "cells" in item:
                sheet = item["cells"].get("sheet") or default_sheet
                rng = parse_range(item["cells"]["range"])
                if not any(s == sheet and t.contains(rng) for s, t in targets):
                    yield ScriptIssue(where, f"vùng {rng} không nằm trong targets.cells của bước")
            if "ui" in item and item["ui"]["control"] not in controls:
                yield ScriptIssue(where, f"nút {item['ui']['control']} không có trong targets.ui của bước")


def _code_issues(path: str, step: Mapping[str, Any], global_codes: set[str]) -> Iterator[ScriptIssue]:
    """Mã lỗi trong feedback và immediate_codes phải là mã mà điều kiện thật sự trả về được."""
    codes = set(global_codes)
    for check in step["checks"]:
        codes.update(codes_for(check["type"]))
    feedback_codes = [f["code"] for f in step.get("feedback", [])]
    for code in sorted(_duplicates(feedback_codes)):
        yield ScriptIssue(f"{path}/feedback", f"mã {code} có hơn một phản hồi")
    for i, code in enumerate(feedback_codes):
        if code not in codes:
            yield ScriptIssue(f"{path}/feedback/{i}/code", f"không điều kiện nào của bước trả mã {code}")
    for code in step.get("signals", {}).get("immediate_codes", []):
        if code not in codes:
            yield ScriptIssue(
                f"{path}/signals/immediate_codes", f"không điều kiện nào của bước trả mã {code}"
            )


def _reference_issues(path: str, step: Mapping[str, Any], reference_ids: set[str]) -> Iterator[ScriptIssue]:
    used = list(step.get("reference_ids", []))
    for hint in step["hints"]:
        used += hint.get("reference_ids", [])
    for ref in used:
        if ref not in reference_ids:
            yield ScriptIssue(path, f"không có nguồn trích dẫn {ref}")


def _step_issues(script: Script) -> Iterator[ScriptIssue]:
    default_sheet = script["exercise"]["sheet"]
    reference_ids = {r["id"] for r in script.get("references", [])}
    global_codes = {code for check in script.get("global_checks", []) for code in codes_for(check["type"])}
    for s, step in enumerate(script["steps"]):
        path = f"/steps/{s}"
        for i, hint in enumerate(step["hints"], start=1):
            if hint.get("level") != i:
                yield ScriptIssue(f"{path}/hints/{i - 1}", f"gợi ý thứ {i} có cấp {hint.get('level')}")
        for c, check in enumerate(step["checks"]):
            yield from _check_issues(f"{path}/checks/{c}", check)
        yield from _target_issues(path, step, default_sheet)
        yield from _code_issues(path, step, global_codes)
        yield from _reference_issues(path, step, reference_ids)


def cross_reference_issues(script: Script) -> list[ScriptIssue]:
    """Tầng 2. Gọi sau khi kịch bản đã qua tầng 1 (lược đồ)."""
    issues: list[ScriptIssue] = []
    step_ids = [s["id"] for s in script["steps"]]
    for step_id in sorted(_duplicates(step_ids)):
        issues.append(ScriptIssue("/steps", f"trùng id bước {step_id}"))
    all_checks = [*script.get("global_checks", []), *(c for s in script["steps"] for c in s["checks"])]
    for check_id in sorted(_duplicates([c["id"] for c in all_checks if "id" in c])):
        issues.append(ScriptIssue("/", f"trùng id điều kiện {check_id}"))
    for g, check in enumerate(script.get("global_checks", [])):
        issues.extend(_check_issues(f"/global_checks/{g}", check))
    try:
        issues.extend(_step_issues(script))
    except AddressError as exc:
        issues.append(ScriptIssue("/steps", f"địa chỉ không hợp lệ: {exc}"))
    for c, criterion in enumerate(script.get("completion", {}).get("criteria", [])):
        for step_id in criterion["step_ids"]:
            if step_id not in step_ids:
                issues.append(ScriptIssue(f"/completion/criteria/{c}", f"trỏ tới bước không có: {step_id}"))
    return issues
