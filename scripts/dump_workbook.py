"""Xuất nội dung một file Excel ra dạng văn bản dễ đọc (dùng cho T1.2, T1.3, T1.4).

In ra từng sheet: vùng dữ liệu, giá trị/công thức từng ô, định dạng số, ô gộp, in đậm, màu nền,
bộ lọc, định dạng có điều kiện, kiểm tra dữ liệu, biểu đồ, thiết lập trang in.

Ví dụ:
  python scripts/dump_workbook.py "samples/_local/b09-du-lieu-dang-so/de.xlsx"
  python scripts/dump_workbook.py file.xlsx --sheet "3. Dap_An_Mau" --max-rows 40
  python scripts/dump_workbook.py file.xlsx --summary      # chỉ in tóm tắt mỗi sheet
"""

from __future__ import annotations

import argparse
import contextlib
import html
import re
import sys
import warnings
import zipfile
from pathlib import Path

import openpyxl
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def describe_cell(cell: Cell, cached: object) -> str:
    parts: list[str] = []
    value = cell.value
    if isinstance(value, str) and value.startswith("="):
        parts.append(f"{value}  →  {cached!r}")
    else:
        parts.append(repr(value))
    if cell.number_format and cell.number_format != "General":
        parts.append(f"fmt={cell.number_format}")
    font = cell.font
    if font is not None:
        if font.b:
            parts.append("đậm")
        if font.i:
            parts.append("nghiêng")
        if font.color is not None and font.color.type == "rgb" and font.color.rgb not in (None, "FF000000"):
            parts.append(f"chữ={font.color.rgb}")
    fill = cell.fill
    if fill is not None and fill.fill_type == "solid" and fill.fgColor is not None:
        color = fill.fgColor.rgb if fill.fgColor.type == "rgb" else f"theme{fill.fgColor.theme}"
        parts.append(f"nền={color}")
    align = cell.alignment
    if align is not None and align.horizontal:
        parts.append(f"canh={align.horizontal}")
    if align is not None and align.wrap_text:
        parts.append("xuống-dòng")
    border = cell.border
    if border is not None and any(getattr(border, side).style for side in ("left", "right", "top", "bottom")):
        parts.append("viền")
    return " · ".join(parts)


def summarize_sheet(ws: Worksheet) -> str:
    formulas = sum(
        1 for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")
    )
    values = sum(1 for row in ws.iter_rows() for c in row if c.value is not None)
    extras = []
    if ws.merged_cells.ranges:
        extras.append(f"{len(ws.merged_cells.ranges)} vùng gộp")
    if ws.auto_filter.ref:
        extras.append(f"lọc {ws.auto_filter.ref}")
    if ws.conditional_formatting:
        extras.append("định dạng có điều kiện")
    if ws.data_validations.dataValidation:
        extras.append("kiểm tra dữ liệu")
    charts = getattr(ws, "_charts", [])
    if charts:
        extras.append(f"{len(charts)} biểu đồ")
    return f"vùng {ws.dimensions} · {values} ô có dữ liệu · {formulas} công thức" + (
        " · " + ", ".join(extras) if extras else ""
    )


def dump_sheet(ws: Worksheet, ws_cached: Worksheet, max_rows: int) -> None:
    print(f"\n## Sheet: {ws.title}  ({summarize_sheet(ws)})")
    ps = ws.page_setup
    m = ws.page_margins
    print(
        f"Trang in: hướng={ps.orientation} khổ={ps.paperSize} tỉ-lệ={ps.scale} "
        f"vừa-trang={ws.sheet_properties.pageSetUpPr.fitToPage if ws.sheet_properties.pageSetUpPr else None} "
        f"lề(T/D/T/P)={m.top}/{m.bottom}/{m.left}/{m.right} "
        f"tiêu-đề-in={ws.print_title_rows} vùng-in={ws.print_area} "
        f"đầu/chân-trang={ws.oddHeader.center.text or ''}/{ws.oddFooter.center.text or ''}"
    )
    if ws.freeze_panes:
        print(f"Cố định: {ws.freeze_panes}")
    if ws.merged_cells.ranges:
        print("Gộp ô:", ", ".join(str(r) for r in ws.merged_cells.ranges))
    if ws.auto_filter.ref:
        print("AutoFilter:", ws.auto_filter.ref)
    for cf in ws.conditional_formatting:
        print("Định dạng có điều kiện:", cf.sqref, [r.type for r in cf.rules])
    for dv in ws.data_validations.dataValidation:
        print("Kiểm tra dữ liệu:", dv.sqref, dv.type, dv.formula1)
    for chart in getattr(ws, "_charts", []):
        title = None
        with contextlib.suppress(AttributeError):
            title = "".join(r.t for p in chart.title.tx.rich.p for r in (p.r or []))
        print(f"Biểu đồ: loại={chart.tagname} tiêu-đề={title!r}")
    widths = {k: round(v.width, 1) for k, v in ws.column_dimensions.items() if v.width}
    if widths:
        print("Độ rộng cột:", widths)
    shown = 0
    for row, row_cached in zip(ws.iter_rows(), ws_cached.iter_rows(), strict=False):
        cells = [(c, cc) for c, cc in zip(row, row_cached, strict=False) if c.value is not None]
        if not cells:
            continue
        shown += 1
        if shown > max_rows:
            print("… (còn nữa, dùng --max-rows để xem thêm)")
            break
        for c, cc in cells:
            print(f"  {c.coordinate}: {describe_cell(c, cc.value)}")


def textbox_texts(path: Path) -> list[tuple[str, str]]:
    """Đọc chữ trong text box (hình vẽ). openpyxl bỏ qua phần này, mà nhiều bài đặt đề bài trong text box."""
    sheet_by_drawing: dict[str, str] = {}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        workbook_xml = z.read("xl/workbook.xml").decode("utf-8")
        workbook_rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        rel_target = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', workbook_rels))
        for sheet_name, rel_id in re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', workbook_xml):
            sheet_file = "xl/" + rel_target.get(rel_id, "").lstrip("/").removeprefix("xl/")
            rels_file = sheet_file.replace("worksheets/", "worksheets/_rels/") + ".rels"
            if rels_file in names:
                for target in re.findall(
                    r'Target="([^"]*drawing\d+\.xml)"', z.read(rels_file).decode("utf-8")
                ):
                    sheet_by_drawing["xl/drawings/" + target.rsplit("/", 1)[-1]] = html.unescape(sheet_name)
        result = []
        for name in sorted(n for n in names if re.match(r"xl/drawings/drawing\d+\.xml$", n)):
            xml = z.read(name).decode("utf-8")
            for shape in re.findall(r"<xdr:sp[ >].*?</xdr:sp>", xml, re.S):
                text = " ".join(re.findall(r"<a:t>([^<]*)</a:t>", shape)).strip()
                if text:
                    result.append((sheet_by_drawing.get(name, "?"), html.unescape(text)))
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Xuất nội dung file Excel ra văn bản.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--sheet", help="Chỉ xuất sheet này")
    parser.add_argument("--max-rows", type=int, default=60, help="Số dòng có dữ liệu tối đa mỗi sheet")
    parser.add_argument("--summary", action="store_true", help="Chỉ in tóm tắt mỗi sheet")
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.path)
    wb_cached = openpyxl.load_workbook(args.path, data_only=True)
    print(f"# {args.path.name}")
    for ws in wb.worksheets:
        if args.sheet and ws.title != args.sheet:
            continue
        if args.summary:
            print(f"- {ws.title}: {summarize_sheet(ws)}")
        else:
            dump_sheet(ws, wb_cached[ws.title], args.max_rows)
    boxes = [(s, t) for s, t in textbox_texts(args.path) if not args.sheet or s == args.sheet]
    if boxes:
        print("\n## Text box (đề bài thường nằm ở đây)")
        for sheet, text in boxes:
            print(f"  [{sheet}] {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
