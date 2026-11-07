"""Ghi thuộc tính tài liệu tùy chỉnh (docProps/custom.xml) vào file .xlsx mà không mở/lưu lại workbook.

Dùng khi phát hành kịch bản: nhúng mã bài `tutor_exercise_id` vào file đề (kien-truc.md A5, T5.6). Không
dùng openpyxl để lưu vì openpyxl làm mất text box, hình vẽ… (đề của trung tâm có hướng dẫn trong text box).
Chỉ sửa 3 phần của gói ZIP; mọi phần khác giữ nguyên từng byte.
"""

import zipfile
from collections.abc import Mapping
from pathlib import Path
from xml.etree import ElementTree as ET

CUSTOM_PART = "docProps/custom.xml"
CONTENT_TYPES = "[Content_Types].xml"
ROOT_RELS = "_rels/.rels"
CUSTOM_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
CUSTOM_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
PROPERTY_FORMAT_ID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"  # định danh cố định cho thuộc tính người dùng

_PROPS_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
_VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_FIRST_PID = 2  # pid 0 và 1 dành riêng


class PackageError(ValueError):
    """File không phải gói .xlsx hợp lệ."""


def _custom_xml(existing: bytes | None, properties: Mapping[str, str]) -> bytes:
    ET.register_namespace("", _PROPS_NS)
    ET.register_namespace("vt", _VT_NS)
    root = ET.fromstring(existing) if existing else ET.Element(f"{{{_PROPS_NS}}}Properties")
    by_name = {prop.get("name"): prop for prop in root.findall(f"{{{_PROPS_NS}}}property")}
    next_pid = max([int(p.get("pid", "1")) for p in by_name.values()] + [_FIRST_PID - 1]) + 1
    for name, value in properties.items():
        prop = by_name.get(name)
        if prop is None:
            prop = ET.SubElement(
                root,
                f"{{{_PROPS_NS}}}property",
                {"fmtid": PROPERTY_FORMAT_ID, "pid": str(next_pid), "name": name},
            )
            next_pid += 1
        for child in list(prop):
            prop.remove(child)
        ET.SubElement(prop, f"{{{_VT_NS}}}lpwstr").text = value
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def _content_types(data: bytes) -> bytes:
    ET.register_namespace("", _TYPES_NS)
    root = ET.fromstring(data)
    part = f"/{CUSTOM_PART}"
    if not any(o.get("PartName") == part for o in root.findall(f"{{{_TYPES_NS}}}Override")):
        ET.SubElement(
            root, f"{{{_TYPES_NS}}}Override", {"PartName": part, "ContentType": CUSTOM_CONTENT_TYPE}
        )
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def _root_rels(data: bytes) -> bytes:
    ET.register_namespace("", _RELS_NS)
    root = ET.fromstring(data)
    relations = root.findall(f"{{{_RELS_NS}}}Relationship")
    if not any(r.get("Type") == CUSTOM_REL_TYPE for r in relations):
        used = {r.get("Id") for r in relations}
        number = 1
        while f"rId{number}" in used:
            number += 1
        attributes = {"Id": f"rId{number}", "Type": CUSTOM_REL_TYPE, "Target": CUSTOM_PART}
        ET.SubElement(root, f"{{{_RELS_NS}}}Relationship", attributes)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def set_custom_properties(source: Path | str, target: Path | str, properties: Mapping[str, str]) -> None:
    """Chép `source` sang `target`, thêm/ghi đè các thuộc tính tùy chỉnh dạng chuỗi."""
    try:
        with zipfile.ZipFile(source) as package:
            entries = [(info, package.read(info.filename)) for info in package.infolist()]
    except (zipfile.BadZipFile, OSError) as exc:
        raise PackageError(f"Không đọc được file {source}: {exc}") from exc
    names = {info.filename for info, _ in entries}
    if CONTENT_TYPES not in names or ROOT_RELS not in names:
        raise PackageError("File thiếu [Content_Types].xml hoặc _rels/.rels: không phải gói Office")
    existing = next((data for info, data in entries if info.filename == CUSTOM_PART), None)
    replaced = {
        CUSTOM_PART: _custom_xml(existing, properties),
        CONTENT_TYPES: _content_types(next(d for i, d in entries if i.filename == CONTENT_TYPES)),
        ROOT_RELS: _root_rels(next(d for i, d in entries if i.filename == ROOT_RELS)),
    }
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
        for info, data in entries:
            package.writestr(info, replaced.pop(info.filename, data))
        for name, data in replaced.items():  # custom.xml chưa có trong file gốc
            package.writestr(name, data)
