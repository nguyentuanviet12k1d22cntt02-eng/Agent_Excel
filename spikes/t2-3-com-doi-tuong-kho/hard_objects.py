"""T2.3 — Đối tượng khó: bộ lọc, sắp xếp, trang in, biểu đồ, thuộc tính tài liệu tùy chỉnh.

Chạy:  .venv\\Scripts\\python spikes\\t2-3-com-doi-tuong-kho\\hard_objects.py

Làm trên BẢN SAO của bài b15 (lọc) trong thư mục tạm, không sửa file mẫu. Với mỗi loại đối tượng:
thao tác bằng COM (như học viên làm) → đọc lại bằng COM → lưu → đọc bằng openpyxl → so sánh.
Đo thời gian đọc từng loại, đặc biệt PageSetup (nghi là chậm vì gọi driver máy in).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

import openpyxl
import pythoncom
import win32com.client

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "samples" / "_local" / "b15-loc-du-lieu" / "de.xlsx"
SHEET = "Bai 01"
TABLE = "B9:I28"  # vùng dữ liệu có tiêu đề ở dòng 9
EXERCISE_ID_PROP = "tutor_exercise_id"

XL_LANDSCAPE, XL_PAPER_A5 = 2, 11
XL_COLUMN_CLUSTERED = 51
XL_ASCENDING, XL_DESCENDING, XL_YES = 1, 2, 1
XL_CELL_TYPE_VISIBLE = 12
XL_TOP_TO_BOTTOM = 1
MSO_PROPERTY_TYPE_STRING = 4


def ms(start: float) -> str:
    return f"{(time.perf_counter() - start) * 1000:.1f} ms"


def autofilter(ws: object) -> None:
    print("1) Bộ lọc — lọc cột 'Mã SP' (cột thứ 3 của bảng) = MH003")
    ws.Range(TABLE).AutoFilter(Field=3, Criteria1="MH003")
    t = time.perf_counter()
    af = ws.AutoFilter
    flt = af.Filters(3)
    visible = ws.Range(TABLE).Columns(1).SpecialCells(XL_CELL_TYPE_VISIBLE).Count - 1  # trừ dòng tiêu đề
    print(
        f"   COM: vùng {af.Range.Address}, cột 3 đang lọc={flt.On}, tiêu chí={flt.Criteria1!r}, "
        f"số dòng dữ liệu đang hiện={visible} ({ms(t)})"
    )


def read_autofilter_openpyxl(path: Path) -> None:
    ws = openpyxl.load_workbook(path)[SHEET]
    af = ws.auto_filter
    cols = [(fc.colId, list(fc.filters.filter) if fc.filters else None) for fc in af.filterColumn]
    hidden = [r for r, d in ws.row_dimensions.items() if d.hidden and 10 <= r <= 28]
    print(
        f"   openpyxl: vùng {af.ref}, cột lọc (colId từ 0) và giá trị={cols}, số dòng bị ẩn trong bảng={len(hidden)}"
    )


def sort_state(excel: object, wb: object) -> None:
    print("2) Sắp xếp — sắp bảng ở sheet 'Bai 02' theo Số lượng giảm dần (như học viên dùng Data > Sort)")
    ws = wb.Worksheets("Bai 02")
    if ws.AutoFilterMode:
        ws.AutoFilterMode = False
    headers = list(ws.Range("B9:I9").Value[0])
    col = headers.index("Số lượng")  # tìm cột theo tiêu đề: mỗi sheet xếp cột khác nhau
    key = ws.Cells(10, 2 + col)  # ô đầu của cột Số lượng
    data = ws.Range("B10:I28")
    # Orientation=1 BẮT BUỘC: không truyền thì Excel có thể sắp theo chiều ngang (xáo cột) — đã kiểm chứng
    data.Sort(Key1=key, Order1=XL_DESCENDING, Header=2, Orientation=XL_TOP_TO_BOTTOM)
    t = time.perf_counter()
    values = [row[col] for row in data.Value if isinstance(row[col], int | float)]
    print(f"   Cột 'Số lượng' là cột {col + 1} của bảng; giá trị sau khi sắp: {values[:6]}…")
    is_desc = all(a >= b for a, b in zip(values, values[1:], strict=False))
    fields = ws.Sort.SortFields.Count
    print(
        f"   COM: Số lượng giảm dần theo dữ liệu thật={is_desc}; Sort.SortFields lưu lại={fields} ({ms(t)})"
    )
    print("   → Range.Sort không để lại 'trạng thái sắp xếp' tin cậy; kiểm chứng phải đọc THỨ TỰ DỮ LIỆU")


def page_setup(ws: object) -> None:
    print("3) Trang in — đặt khổ A5, ngang, số trang ở giữa đầu trang")
    t = time.perf_counter()
    ps = ws.PageSetup
    ps.Orientation = XL_LANDSCAPE
    ps.PaperSize = XL_PAPER_A5
    ps.CenterHeader = "&P"
    print(f"   Ghi 3 thuộc tính: {ms(t)}")
    timings = []
    for _ in range(3):
        t = time.perf_counter()
        _ = (ps.Orientation, ps.PaperSize, ps.CenterHeader)
        timings.append((time.perf_counter() - t) * 1000)
    print(
        f"   COM đọc 3 thuộc tính: lần 1 {timings[0]:.1f} ms, lần 2 {timings[1]:.1f} ms, lần 3 {timings[2]:.1f} ms; "
        f"giá trị: hướng={ps.Orientation}, khổ={ps.PaperSize}, đầu trang giữa={ps.CenterHeader!r}"
    )
    excel = ws.Application
    t = time.perf_counter()
    excel.PrintCommunication = False
    _ = (ps.Orientation, ps.PaperSize, ps.CenterHeader)
    excel.PrintCommunication = True
    print(f"   COM đọc khi tắt PrintCommunication: {ms(t)}")


def read_page_setup_openpyxl(path: Path) -> None:
    ws = openpyxl.load_workbook(path)[SHEET]
    print(
        f"   openpyxl: hướng={ws.page_setup.orientation}, khổ={ws.page_setup.paperSize}, "
        f"đầu trang giữa={ws.oddHeader.center.text!r}"
    )


def chart(ws: object) -> None:
    print("4) Biểu đồ — tạo biểu đồ cột từ cột Số lượng")
    obj = ws.ChartObjects().Add(Left=600, Top=50, Width=360, Height=220)
    c = obj.Chart
    c.SetSourceData(ws.Range("G9:G14"))
    c.ChartType = XL_COLUMN_CLUSTERED
    c.HasTitle = True
    c.ChartTitle.Text = "Số lượng bán"
    t = time.perf_counter()
    series = c.SeriesCollection(1)
    print(
        f"   COM: số biểu đồ={ws.ChartObjects().Count}, loại={c.ChartType}, tiêu đề={c.ChartTitle.Text!r}, "
        f"chuỗi={series.Formula!r} ({ms(t)})"
    )


def read_chart_openpyxl(path: Path) -> None:
    ws = openpyxl.load_workbook(path)[SHEET]
    charts = ws._charts
    if not charts:
        print("   openpyxl: KHÔNG đọc được biểu đồ")
        return
    c = charts[0]
    title = "".join(r.t for p in c.title.tx.rich.p for r in (p.r or [])) if c.title else None
    refs = [s.val.numRef.f for s in c.series]
    print(
        f"   openpyxl: số biểu đồ={len(charts)}, loại={c.tagname}, kiểu cột={getattr(c, 'type', None)}, "
        f"tiêu đề={title!r}, chuỗi={refs}"
    )


def custom_property(wb: object) -> None:
    print("5) Thuộc tính tài liệu tùy chỉnh — ghi mã bài (Backend sẽ làm khi phát hành)")
    props = wb.CustomDocumentProperties
    props.Add(EXERCISE_ID_PROP, False, MSO_PROPERTY_TYPE_STRING, "b15@v1")  # pywin32: phải truyền theo vị trí
    t = time.perf_counter()
    print(f"   COM đọc lại: {props(EXERCISE_ID_PROP).Value!r} ({ms(t)})")


def read_custom_property_openpyxl(path: Path) -> None:
    wb = openpyxl.load_workbook(path)
    value = next((p.value for p in wb.custom_doc_props.props if p.name == EXERCISE_ID_PROP), None)
    print(f"   openpyxl đọc: {value!r}")
    wb.custom_doc_props.append(
        openpyxl.packaging.custom.StringProperty(name="tutor_written_by", value="openpyxl")
    )
    out = path.with_name("openpyxl-written.xlsx")
    wb.save(out)
    print(f"   openpyxl ghi thuộc tính khác rồi lưu → {out.name} (COM đọc lại ở bước cuối)")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="t2-3-"))
    work = tmp / "b15-copy.xlsx"
    shutil.copy2(SOURCE, work)
    saved = tmp / "b15-saved.xlsx"
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    try:
        excel.Visible = False
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Open(str(work))
        ws = wb.Worksheets(SHEET)
        autofilter(ws)
        sort_state(excel, wb)
        page_setup(ws)
        chart(ws)
        custom_property(wb)
        wb.SaveAs(str(saved), FileFormat=51)
        wb.Close(SaveChanges=False)

        print("\n--- Đọc lại file đã lưu bằng openpyxl ---")
        print("1) Bộ lọc")
        read_autofilter_openpyxl(saved)
        print("3) Trang in")
        read_page_setup_openpyxl(saved)
        print("4) Biểu đồ")
        read_chart_openpyxl(saved)
        print("5) Thuộc tính tùy chỉnh")
        read_custom_property_openpyxl(saved)

        wb = excel.Workbooks.Open(str(saved.with_name("openpyxl-written.xlsx")), ReadOnly=True)
        props = {p.Name: p.Value for p in wb.CustomDocumentProperties}
        print(f"   COM đọc file do openpyxl ghi: {props}")
        print(f"   Biểu đồ còn sau khi openpyxl lưu lại: {wb.Worksheets(SHEET).ChartObjects().Count}")
        wb.Close(SaveChanges=False)
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
