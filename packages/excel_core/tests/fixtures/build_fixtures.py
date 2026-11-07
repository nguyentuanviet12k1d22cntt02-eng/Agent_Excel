"""Dựng các file Excel dùng cho test của excel_core (bài do nhóm tự soạn, số liệu giả).

Bố cục theo 2 kịch bản viết tay đã công khai (docs/kich-ban-tay/), để chạy được kịch bản mẫu trong
schemas/tutor-script/v1/examples/ trên CI mà không cần bài của trung tâm (samples/_local/ không lên git).

    .venv\\Scripts\\python packages\\excel_core\\tests\\fixtures\\build_fixtures.py

File đáp án có công thức nên phải được **Excel** mở và lưu để có giá trị đã tính (snapshot.md mục 5). Script
mở một phiên Excel riêng (DispatchEx), không đụng tới Excel người dùng đang mở. `--no-excel` bỏ bước này.
"""

import argparse
import logging
import re
import zipfile
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
FIXTURE_AUTHOR = "excel_core tests"
COMMA_0 = '_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)'  # Comma Style rồi giảm còn 0 số lẻ
B09_SHEET = "2. Bang_Ke_Ban_Hang"
B22_SHEET = "Bài 01"
B09_HEADERS = ["STT", "Mã hàng", "Tên hàng", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền", "Tỉ lệ giảm giá"]
B09_ITEMS = [
    ("VPP01", "Bút bi", "Cây", 1250, 3.5, 0.05),
    ("VPP02", "Giấy in", "Ream", 320, 62, 0),
    ("VPP03", "Bìa hồ sơ", "Cái", 15000, 1.25, 0.125),
    ("VPP04", "Kẹp giấy", "Hộp", 845, 18.75, 0.1),
    ("VPP05", "Thước kẻ", "Cây", 4300, 7, 0.075),
]
B22_DAYS = 11
B22_AMOUNTS = [(25 + d * 3, 40 + (d * 7) % 15, 30 + (d * 5) % 12) for d in range(B22_DAYS)]  # nghìn đồng


def _b09_table(ws: Worksheet, header_row: int, with_numbers: bool) -> None:
    for i, title in enumerate(B09_HEADERS):
        ws.cell(header_row, 2 + i, title).font = Font(bold=True)
    for n, (code, name, unit, qty, price, rate) in enumerate(B09_ITEMS, start=1):
        row = header_row + n
        ws.cell(row, 2, n)
        ws.cell(row, 3, code)
        ws.cell(row, 4, name)
        ws.cell(row, 5, unit)
        if with_numbers:
            ws.cell(row, 6, qty)
            ws.cell(row, 7, price)
            ws.cell(row, 9, rate)


def _b09(solution: bool) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    guide = wb.active
    guide.title = "1. Thuc_Hanh_Tung_Buoc"
    guide["B2"] = "Bài tập do nhóm tự soạn để kiểm thử excel_core (số liệu giả)."
    guide["B5"] = "Dấu phân cách hàng nghìn: chọn cột, thẻ Home, nhóm Number, nút Comma Style."
    ws = wb.create_sheet(B09_SHEET)
    ws["B2"] = "BẢNG KÊ BÁN HÀNG"
    ws["B2"].font = Font(bold=True, size=14)
    ws.merge_cells("B2:I2")
    _b09_table(ws, 9, with_numbers=solution)
    ws["B16"] = "Số liệu thô"
    _b09_table(ws, 17, with_numbers=True)
    for row in range(10, 15):
        ws.cell(row, 8, f"=F{row}*G{row}")
    if solution:
        for row in range(10, 15):
            ws.cell(row, 6).number_format = COMMA_0
            ws.cell(row, 7).number_format = "#,##0.00"
            ws.cell(row, 8).number_format = "#,##0.00"
            ws.cell(row, 9).number_format = "0.000"
            for col in range(6, 10):
                ws.cell(row, col).alignment = Alignment(horizontal="right")
    wb.active = 1
    return wb


def _b22(solution: bool) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = B22_SHEET
    ws["B2"] = "BẢNG CHI TIÊU ĐI CHỢ (nghìn đồng, số liệu giả)"
    for i, title in enumerate(["Ngày", "Tiền Bún", "Tiền Thịt", "Tiền Cá", "Tổng tiền"]):
        ws.cell(8, 2 + i, title).font = Font(bold=True)
    start = date(2026, 11, 1)
    for d, (bun, thit, ca) in enumerate(B22_AMOUNTS):
        row = 9 + d
        ws.cell(row, 2, start + timedelta(days=d)).number_format = "dd/mm/yyyy"
        for col, amount in ((3, bun), (4, thit), (5, ca)):
            ws.cell(row, col, amount * 1000).number_format = "#,##0"
        ws.cell(row, 6).number_format = "#,##0"
    ws["B20"] = "TỔNG CỘNG"
    ws["B20"].font = Font(bold=True)
    for col in range(3, 7):
        ws.cell(20, col).number_format = "#,##0"
    ws["J9"] = "Hãy tính Tổng tiền bằng hàm SUM."
    ws["J10"] = "Hãy hoàn thành dòng TỔNG CỘNG bằng hàm SUM."
    ws["J11"] = "Hãy dùng phương pháp sao chép công thức để làm nhanh."
    if solution:
        for row in range(9, 9 + B22_DAYS):
            ws.cell(row, 6, f"=SUM(C{row}:E{row})")
        for col in "CDE":
            ws[f"{col}20"] = f"=SUM({col}9:{col}19)"
        ws["F20"] = "=SUM(F9:F19)"
    return wb


def scrub_author(path: Path) -> None:
    """Repo public: thay tên người dùng máy mà Excel ghi vào lastModifiedBy khi lưu.

    Không đổi Application.UserName vì đó là cài đặt Office của người dùng (lưu vào registry).
    """
    with zipfile.ZipFile(path) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        for info, data in entries:
            if info.filename == "docProps/core.xml":
                text = re.sub(
                    r"<cp:lastModifiedBy>[^<]*</cp:lastModifiedBy>",
                    f"<cp:lastModifiedBy>{FIXTURE_AUTHOR}</cp:lastModifiedBy>",
                    data.decode("utf-8"),
                )
                data = text.encode("utf-8")
            target.writestr(info, data)


B14_SHEET = "Bang_Diem"
B14_STUDENTS = [
    ("Nguyễn Văn An", 8, 7.5, 9),
    ("Trần Thị Bình", 6.5, 8, 7),
    ("Lê Minh Châu", 9, 9, 8.5),
    ("Phạm Quốc Dũng", 7, 6, 8),
    ("Hoàng Thu Hà", 8.5, 7, 9.5),
]
B16_SHEET = "Bai 01"
B16_STAFF = [
    ("NV01", "Nguyễn Văn An", "Kế toán", 8_500_000),
    ("NV02", "Trần Thị Bình", "Kinh doanh", 12_000_000),
    ("NV03", "Lê Minh Châu", "Kỹ thuật", 15_500_000),
    ("NV04", "Phạm Quốc Dũng", "Kinh doanh", 9_800_000),
    ("NV05", "Hoàng Thu Hà", "Kế toán", 11_200_000),
    ("NV06", "Võ Thanh Long", "Kỹ thuật", 13_700_000),
]


def _b14(solution: bool) -> openpyxl.Workbook:
    """Tạo bảng: gộp ô tiêu đề, in đậm, tô nền dòng tiêu đề cột, kẻ viền cả bảng."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = B14_SHEET
    ws["A1"] = "BẢNG ĐIỂM HỌC KỲ I (số liệu giả)"
    for i, title in enumerate(["STT", "Họ tên", "Toán", "Văn", "Anh"], start=1):
        ws.cell(3, i, title)
    for n, (name, *scores) in enumerate(B14_STUDENTS, start=1):
        ws.append([n, name, *scores])
    if solution:
        ws.merge_cells("A1:E1")
        ws["A1"].font = Font(bold=True, size=14)
        ws["A1"].alignment = Alignment(horizontal="center")
        thin = Side(style="thin")
        for row in ws.iter_rows(min_row=3, max_row=3 + len(B14_STUDENTS), min_col=1, max_col=5):
            for cell in row:
                cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        for cell in ws[3]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="FFD9E1F2")
            cell.alignment = Alignment(horizontal="center")
    return wb


def _b16(solution: bool) -> openpyxl.Workbook:
    """Sắp xếp danh sách nhân viên theo Lương giảm dần (giữ nguyên từng dòng)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = B16_SHEET
    ws["A1"] = "DANH SÁCH NHÂN VIÊN (số liệu giả)"
    for i, title in enumerate(["Mã NV", "Họ tên", "Phòng", "Lương"], start=1):
        ws.cell(3, i, title).font = Font(bold=True)
    rows = sorted(B16_STAFF, key=lambda r: r[3], reverse=True) if solution else B16_STAFF
    for offset, record in enumerate(rows):
        for col, value in enumerate(record, start=1):
            ws.cell(4 + offset, col, value)
        ws.cell(4 + offset, 4).number_format = "#,##0"
    ws["F3"] = "Yêu cầu: sắp xếp bảng theo Lương từ cao xuống thấp."
    return wb


BUILDERS: dict[str, Callable[[bool], openpyxl.Workbook]] = {
    "b09": _b09,
    "b22": _b22,
    "b14": _b14,
    "b16": _b16,
}


def recalculate_with_excel(paths: list[Path]) -> None:
    """Mở và lưu lại bằng một phiên Excel riêng để file có giá trị đã tính của công thức."""
    # Chỉ cần khi dựng lại file trên Windows có Excel, nên import trong hàm
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    try:
        excel.Visible = False
        excel.DisplayAlerts = False
        for path in paths:
            wb = excel.Workbooks.Open(str(path))
            excel.CalculateFull()
            wb.Save()
            wb.Close(False)
            logger.info("Excel đã tính và lưu %s", path.relative_to(HERE))
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Dựng file Excel cho test excel_core.")
    parser.add_argument("--no-excel", action="store_true", help="không mở Excel tính lại công thức")
    parser.add_argument("--only", nargs="+", choices=sorted(BUILDERS), help="chỉ dựng các bài này")
    args = parser.parse_args()
    written = []
    for name, build in BUILDERS.items():
        if args.only and name not in args.only:
            continue
        folder = HERE / name
        folder.mkdir(exist_ok=True)
        for filename, solution in (("de.xlsx", False), ("dap-an.xlsx", True)):
            path = folder / filename
            build(solution).save(path)
            written.append(path)
    if not args.no_excel:
        recalculate_with_excel(written)
    for path in written:
        scrub_author(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
