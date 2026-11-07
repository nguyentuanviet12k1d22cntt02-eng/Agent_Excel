"""Chuyển snapshot ↔ JSON gọn.

Dùng cho: nhật ký thực hành (snapshot.md mục 7) và **snapshot tham chiếu** của file đề/đáp án mà Backend gửi
kèm kịch bản cho Desktop (Desktop không có file đáp án nhưng điều kiện `expected: solution`, `data_unchanged`
cần giá trị của chúng).
"""

import dataclasses
import types
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from excel_core.snapshot.model import CellValue, ErrorValue, WorkbookSnapshot
from excel_core.snapshot.request import PropertyGroup

FORMAT_VERSION = 1
_DATETIME_TAG = "$datetime"
_ERROR_TAG = "$error"


class SnapshotFormatError(ValueError):
    """Dữ liệu JSON không đúng định dạng snapshot."""


def _encode(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, PropertyGroup):
        return value.value
    if isinstance(value, datetime):
        return {_DATETIME_TAG: value.isoformat()}
    if isinstance(value, ErrorValue):
        return {_ERROR_TAG: value.code}
    if dataclasses.is_dataclass(value):
        out = {}
        for f in dataclasses.fields(value):
            item = getattr(value, f.name)
            if f.default is not dataclasses.MISSING and item == f.default:
                continue  # bỏ trường mang giá trị mặc định cho gọn
            out[f.name] = _encode(item)
        return out
    if isinstance(value, Mapping):
        return {str(k): _encode(v) for k, v in value.items()}
    if isinstance(value, frozenset | set):
        return sorted(_encode(v) for v in value)
    if isinstance(value, tuple | list):
        return [_encode(v) for v in value]
    raise SnapshotFormatError(f"Không chuyển được kiểu {type(value).__name__}")


def snapshot_to_dict(snapshot: WorkbookSnapshot) -> dict[str, Any]:
    """WorkbookSnapshot → dict chỉ gồm kiểu JSON."""
    return {"format_version": FORMAT_VERSION, "snapshot": _encode(snapshot)}


def _decode_cell_value(data: Any) -> CellValue:
    if isinstance(data, dict):
        if _DATETIME_TAG in data:
            return datetime.fromisoformat(data[_DATETIME_TAG])
        if _ERROR_TAG in data:
            return ErrorValue(data[_ERROR_TAG])
        raise SnapshotFormatError(f"Giá trị ô lạ: {data!r}")
    if isinstance(data, int) and not isinstance(data, bool):
        return float(data)
    return data


def _decode(hint: Any, data: Any) -> Any:
    if hint is CellValue or hint == CellValue.__value__:
        return _decode_cell_value(data)
    origin = get_origin(hint)
    if origin in (Union, types.UnionType):
        if data is None:
            return None
        options = [a for a in get_args(hint) if a is not type(None)]
        return _decode(options[0], data) if len(options) == 1 else data
    if origin is Literal:
        return data
    if dataclasses.is_dataclass(hint):
        hints = get_type_hints(hint)
        kwargs = {name: _decode(hints[name], value) for name, value in data.items()}
        return hint(**kwargs)
    if origin is tuple:
        args = get_args(hint)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(args[0], v) for v in data)
        return tuple(_decode(a, v) for a, v in zip(args, data, strict=True))
    if origin is frozenset:
        return frozenset(_decode(get_args(hint)[0], v) for v in data)
    if origin in (Mapping, dict):
        key_type, value_type = get_args(hint)
        return {_decode(key_type, k): _decode(value_type, v) for k, v in data.items()}
    if hint is PropertyGroup:
        return PropertyGroup(data)
    if hint is datetime:
        return datetime.fromisoformat(data[_DATETIME_TAG])
    if hint is float and isinstance(data, int):
        return float(data)
    if hint is int and isinstance(data, str):
        return int(data)
    return data


def snapshot_from_dict(data: Mapping[str, Any]) -> WorkbookSnapshot:
    """Ngược lại của `snapshot_to_dict`."""
    if data.get("format_version") != FORMAT_VERSION:
        raise SnapshotFormatError(
            f"Phiên bản định dạng snapshot không hỗ trợ: {data.get('format_version')!r}"
        )
    try:
        return _decode(WorkbookSnapshot, data["snapshot"])
    except (KeyError, TypeError, AttributeError) as exc:
        raise SnapshotFormatError(f"Snapshot hỏng: {exc}") from exc
