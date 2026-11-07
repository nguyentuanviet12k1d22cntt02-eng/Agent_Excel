"""T2.1 — Đọc dữ liệu qua Excel COM: đo tốc độ và đối chiếu với openpyxl.

Chạy:  .venv\\Scripts\\python spikes\\t2-1-com-doc-du-lieu\\read_benchmark.py [đường-dẫn-file-đáp-án]

Phần 1 (đo tốc độ): tạo workbook tạm 100 dòng × 10 cột = 1.000 ô trong một phiên Excel riêng, đo:
  từng ô (.Value, .Formula, NumberFormat qua LCID 1033, Font.Bold) so với đọc cả vùng một lần.
Phần 2 (đối chiếu): đọc cùng một file bằng COM và openpyxl, so giá trị, công thức, mã định dạng số.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import openpyxl
import pythoncom
import win32com.client

LCID_EN_US = 1033
ROWS, COLS = 100, 10


def get_invariant(obj: object, name: str) -> object:
    """Đọc thuộc tính COM với LCID 1033 để Excel không dịch theo cài đặt vùng (xem quy-tac-code.md 2.3)."""
    dispid = obj._oleobj_.GetIDsOfNames(name)
    return obj._oleobj_.Invoke(dispid, LCID_EN_US, pythoncom.DISPATCH_PROPERTYGET, 1)


def timed(label: str, fn: object, cells: int) -> float:
    start = time.perf_counter()
    fn()
    ms = (time.perf_counter() - start) * 1000
    print(f"  {label:<48} {ms:8.1f} ms   ({ms / cells * 1000:7.1f} µs/ô)")
    return ms


def benchmark(excel: object) -> dict[str, float]:
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)
    data = [[r * COLS + c + 0.5 for c in range(COLS)] for r in range(ROWS)]
    rng = ws.Range(ws.Cells(1, 1), ws.Cells(ROWS, COLS))
    rng.Value = data
    ws.Range(ws.Cells(1, COLS + 1), ws.Cells(ROWS, COLS + 1)).Formula = "=SUM(RC1:RC10)"
    n = ROWS * COLS
    cells = [ws.Cells(r, c) for r in range(1, ROWS + 1) for c in range(1, COLS + 1)]
    print(f"Đo trên {n} ô:")
    result = {
        "value_per_cell": timed("Từng ô: .Value", lambda: [c.Value for c in cells], n),
        "formula_per_cell": timed("Từng ô: .Formula", lambda: [c.Formula for c in cells], n),
        "numfmt_per_cell": timed(
            "Từng ô: NumberFormat (LCID 1033)", lambda: [get_invariant(c, "NumberFormat") for c in cells], n
        ),
        "bold_per_cell": timed("Từng ô: Font.Bold", lambda: [c.Font.Bold for c in cells], n),
        "value_bulk": timed("Cả vùng 1 lần: .Value", lambda: rng.Value, n),
        "formula_bulk": timed("Cả vùng 1 lần: .Formula", lambda: rng.Formula, n),
        "numfmt_bulk": timed(
            "Cả vùng 1 lần: NumberFormat (None nếu lẫn lộn)", lambda: get_invariant(rng, "NumberFormat"), n
        ),
    }
    wb.Close(SaveChanges=False)
    return result


def compare(excel: object, path: Path) -> None:
    print(f"\nĐối chiếu COM ↔ openpyxl trên {path.name}:")
    wb_formula = openpyxl.load_workbook(path)
    wb_value = openpyxl.load_workbook(path, data_only=True)
    wb = excel.Workbooks.Open(str(path), ReadOnly=True)
    try:
        for ws_px in wb_formula.worksheets:
            ws_com = wb.Worksheets(ws_px.title)
            mismatches = []
            checked = 0
            for row in ws_px.iter_rows():
                for cell in row:
                    if cell.value is None:
                        continue
                    checked += 1
                    com_cell = ws_com.Range(cell.coordinate)
                    px_formula = (
                        cell.value if isinstance(cell.value, str) and cell.value.startswith("=") else None
                    )
                    com_formula = com_cell.Formula if com_cell.HasFormula else None
                    px_value = wb_value[ws_px.title][cell.coordinate].value
                    com_value = com_cell.Value
                    if hasattr(com_value, "year"):  # pywintypes.datetime có múi giờ → đưa về datetime thường
                        com_value = datetime(*com_value.timetuple()[:6])
                    same_value = px_value == com_value or (
                        isinstance(px_value, int | float)
                        and isinstance(com_value, int | float)
                        and abs(px_value - com_value) < 1e-9
                    )
                    px_fmt = cell.number_format
                    com_fmt = get_invariant(com_cell, "NumberFormat")
                    if px_formula != com_formula or not same_value or px_fmt != com_fmt:
                        mismatches.append(
                            (cell.coordinate, px_formula, com_formula, px_value, com_value, px_fmt, com_fmt)
                        )
            print(f"  [{ws_px.title}] {checked} ô có dữ liệu, {len(mismatches)} ô lệch")
            for m in mismatches[:5]:
                print("     lệch:", m)
    finally:
        wb.Close(SaveChanges=False)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")  # phiên Excel riêng
    try:
        excel.Visible = False
        excel.DisplayAlerts = False
        print(f"Excel {excel.Version} build {excel.Build}")
        benchmark(excel)
        if len(sys.argv) > 1:
            compare(excel, Path(sys.argv[1]).resolve())
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
