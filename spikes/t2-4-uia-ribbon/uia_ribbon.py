"""T2.4 — UI Automation / MSAA: Ribbon, nút lệnh, hộp thoại, vị trí ô, sự kiện in.

Chạy:
  .venv\\Scripts\\python spikes\\t2-4-uia-ribbon\\uia_ribbon.py             # kiểm tra (~30 giây)
  .venv\\Scripts\\python spikes\\t2-4-uia-ribbon\\uia_ribbon.py --catalog   # xuất danh mục AutomationId của Ribbon
(Một cửa sổ Excel riêng sẽ hiện lên. Không giả lập bàn phím/chuột.)

Kiểm tra:
  1. Tìm các tab Ribbon, biết tab nào đang chọn.
  2. Tìm nút theo AutomationId (= idMso), lấy tọa độ màn hình (để overlay chỉ vào). Có cả nút tách đôi.
  3. Đọc trạng thái nút bật/tắt (Bold) qua UIA TogglePattern, MSAA (LegacyIAccessible) và COM.
  4. Mở hộp thoại Format Cells bằng nút trên Ribbon (UIA Invoke, như người dùng bấm); đọc tab đang chọn và
     mục đang chọn trong danh sách Category.
  5. Vị trí ô trên màn hình: COM so với UIA.
  6. Sự kiện in: WorkbookBeforePrint khi in ra PDF và khi xuất PDF.
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import tempfile
import threading
import time
from pathlib import Path

import pythoncom
import uiautomation as auto
import win32com.client
import win32con
import win32gui
import win32process

# (tên hiển thị trên Office tiếng Anh, AutomationId = idMso). Tên hiển thị đổi theo ngôn ngữ; idMso thì không.
BUTTONS = [
    ("Comma Style", "CommaStyle"),
    ("Decrease Decimal", "DecimalsDecrease"),
    ("Increase Decimal", "DecimalsIncrease"),
    ("Align Right", "AlignRight"),
    ("Bold", "Bold"),
    ("AutoSum (tên hiển thị là 'Sum')", "AutoSum"),
    ("Sort & Filter", "SortFilterMenu"),
]
CATALOG_TABS = ["TabHome", "TabInsert", "TabPageLayoutExcel", "TabFormulas", "TabData", "TabView"]
CATALOG_KINDS = {
    "ButtonControl",
    "SplitButtonControl",
    "MenuItemControl",
    "CheckBoxControl",
    "ComboBoxControl",
}
CATALOG_FILE = Path(__file__).resolve().parent / "danh-muc-idmso.md"
LCID_EN_US = 1033
MSAA_STATE_CHECKED = 0x10
PRINT_EVENTS: list[str] = []


class AppEvents:
    def OnWorkbookBeforePrint(self, wb: object, _cancel: object) -> None:  # noqa: N802 — tên do COM quy định
        PRINT_EVENTS.append(wb.Name)


def timed(fn: object) -> tuple[object, float]:
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000


def find_by_id(root: auto.Control, automation_id: str, depth: int = 30) -> auto.Control | None:
    found = root.Control(searchDepth=depth, AutomationId=automation_id)
    return found if found.Exists(0, 0) else None


def select_tab(window: auto.Control, tab_id: str) -> auto.Control | None:
    tab = window.TabItemControl(searchDepth=12, AutomationId=tab_id)
    if not tab.Exists(2):
        return None
    tab.GetSelectionItemPattern().Select()
    time.sleep(0.8)
    return tab


def set_number_format(rng: object, fmt: str) -> None:
    """Gán NumberFormat theo mã en-US (LCID 1033) — xem quy-tac-code.md mục 2.3."""
    dispid = rng._oleobj_.GetIDsOfNames("NumberFormat")
    rng._oleobj_.Invoke(dispid, LCID_EN_US, pythoncom.DISPATCH_PROPERTYPUT, 0, fmt)


def ribbon_tabs(window: auto.Control) -> None:
    print("1) Tab Ribbon:")
    all_tabs, t = timed(
        lambda: [c for c, _ in auto.WalkControl(window, maxDepth=12) if c.ControlTypeName == "TabItemControl"]
    )
    tabs = [c for c in all_tabs if c.GetParentControl().Name == "Ribbon Tabs"]
    others = [c.Name for c in all_tabs if c not in tabs]
    print(f"   {len(tabs)} tab Ribbon ({t:.0f} ms): {[(c.Name, c.AutomationId) for c in tabs]}")
    print(f"   TabItem khác (không phải Ribbon, ví dụ tab sheet): {others}")
    selected = [c.Name for c in tabs if c.GetSelectionItemPattern().IsSelected]
    print(f"   Tab Ribbon đang chọn khi mới mở: {selected or 'không có'}")
    select_tab(window, "TabHome")
    print(
        f"   Sau khi chọn TabHome qua UIA: đang chọn {[c.Name for c in tabs if c.GetSelectionItemPattern().IsSelected]}"
    )


def ribbon_buttons(window: auto.Control) -> dict[str, auto.Control]:
    print("2) Nút lệnh trên tab Home (tìm theo AutomationId):")
    found: dict[str, auto.Control] = {}
    for label, automation_id in BUTTONS:
        ctrl, t = timed(lambda automation_id=automation_id: find_by_id(window, automation_id))
        if not ctrl:
            print(f"   {label:<32} {automation_id:<18} KHÔNG thấy ({t:.0f} ms)")
            continue
        r = ctrl.BoundingRectangle
        print(
            f"   {label:<32} {automation_id:<18} Name={ctrl.Name!r:<18} loại={ctrl.ControlTypeName:<18} "
            f"tọa độ=({r.left},{r.top},{r.right},{r.bottom}) ({t:.0f} ms)"
        )
        found[automation_id] = ctrl
    return found


def toggle_state(excel: object, buttons: dict[str, auto.Control]) -> None:
    print("3) Trạng thái nút Bold khi ô đang chọn in đậm / không in đậm:")
    bold = buttons.get("Bold")
    if not bold:
        print("   Không có nút Bold để thử")
        return
    ws = excel.ActiveSheet
    for value in (True, False):
        ws.Range("A1").Font.Bold = value
        ws.Range("A1").Select()
        time.sleep(0.4)  # chờ Ribbon cập nhật
        try:
            toggle = bold.GetTogglePattern().ToggleState
        except Exception as exc:
            toggle = f"không có TogglePattern ({exc.__class__.__name__})"
        state = bold.GetLegacyIAccessiblePattern().State
        pressed_mso = excel.CommandBars.GetPressedMso("Bold")
        print(
            f"   A1 in đậm={value}: UIA ToggleState={toggle}, MSAA state=0x{state:X} "
            f"(checked={bool(state & MSAA_STATE_CHECKED)}), COM GetPressedMso('Bold')={pressed_mso}"
        )


def find_dialog_hwnd(pid: int) -> int | None:
    found: list[int] = []

    def visit(hwnd: int, _: object) -> bool:
        if (
            win32gui.GetClassName(hwnd) == "bosa_sdm_XL9"
            and win32process.GetWindowThreadProcessId(hwnd)[1] == pid
        ):
            found.append(hwnd)
        return True

    win32gui.EnumWindows(visit, None)
    return found[0] if found else None


def close_dialogs(pid: int) -> None:
    """Dọn dẹp: đóng mọi hộp thoại còn mở của phiên Excel riêng trước khi Quit."""
    for _ in range(10):
        hwnd = find_dialog_hwnd(pid)
        if not hwnd:
            return
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(0.3)


def dialog(excel: object, window: auto.Control) -> None:
    print("4) Hộp thoại Format Cells (mở bằng nút mở rộng nhóm Number, như người dùng bấm):")
    ws = excel.ActiveSheet
    set_number_format(ws.Range("A1"), "0.00%")
    ws.Range("A1").Select()
    select_tab(window, "TabHome")
    hwnd_main = excel.Hwnd
    pid = win32process.GetWindowThreadProcessId(hwnd_main)[1]

    def invoke() -> None:
        with auto.UIAutomationInitializerInThread():
            button = auto.ControlFromHandle(hwnd_main).ButtonControl(
                AutomationId="FormatCellsNumberDialog", searchDepth=20
            )
            button.GetInvokePattern().Invoke()

    threading.Thread(target=invoke, daemon=True).start()
    start = time.perf_counter()
    hwnd = None
    while time.perf_counter() - start < 5 and hwnd is None:
        hwnd = find_dialog_hwnd(pid)
        time.sleep(0.1)
    if not hwnd:
        print("   Không thấy hộp thoại")
        return
    dlg = auto.ControlFromHandle(hwnd)
    time.sleep(0.4)
    print(
        f"   Hộp thoại: Name={dlg.Name!r}, ClassName={dlg.ClassName!r} ({(time.perf_counter() - start) * 1000:.0f} ms)"
    )
    tabs = [c for c, _ in auto.WalkControl(dlg, maxDepth=6) if c.ControlTypeName == "TabItemControl"]
    sel_tab = [t.Name for t in tabs if t.GetSelectionItemPattern().IsSelected]
    print(f"   Các tab: {[t.Name for t in tabs]} — đang chọn: {sel_tab}")
    lists = [c for c, _ in auto.WalkControl(dlg, maxDepth=8) if c.ControlTypeName == "ListControl"]
    for lst in lists[:1]:
        items = [i for i in lst.GetChildren() if i.ControlTypeName == "ListItemControl"]
        by_item = [i.Name for i in items if i.GetSelectionItemPattern().IsSelected]
        by_list = [s.Name for s in lst.GetSelectionPattern().GetSelection()]
        by_msaa = lst.GetLegacyIAccessiblePattern().Value
        print(f"   Danh sách {lst.Name!r} ({len(items)} mục), ô A1 đang là 0.00%:")
        print(f"     ListItem.IsSelected → {by_item}   (cách cũ, không dùng được)")
        print(f"     List.SelectionPattern.GetSelection() → {by_list}")
        print(f"     List.LegacyIAccessible.Value → {by_msaa!r}")
    close_dialogs(pid)
    print(f"   Đóng hộp thoại bằng WM_CLOSE: {'được' if not find_dialog_hwnd(pid) else 'KHÔNG'}")


def cell_rect(excel: object, window: auto.Control) -> None:
    print("5) Vị trí ô trên màn hình — so sánh UIA với COM PointsToScreenPixels:")
    ws = excel.ActiveSheet
    pane = excel.ActiveWindow.ActivePane
    for address in ("A1", "C5", "F12"):
        rng = ws.Range(address)
        x1 = pane.PointsToScreenPixelsX(rng.Left)
        y1 = pane.PointsToScreenPixelsY(rng.Top)
        x2 = pane.PointsToScreenPixelsX(rng.Left + rng.Width)
        y2 = pane.PointsToScreenPixelsY(rng.Top + rng.Height)
        item, t = timed(lambda address=address: window.DataItemControl(searchDepth=30, Name=address))
        if item.Exists(0, 0):
            r = item.BoundingRectangle
            uia = (r.left, r.top, r.right, r.bottom)
            diff = max(abs(a - b) for a, b in zip((x1, y1, x2, y2), uia, strict=True))
            print(
                f"   {address}: COM=({x1},{y1},{x2},{y2})  UIA={uia}  lệch tối đa {diff} px  (tìm UIA {t:.0f} ms)"
            )
        else:
            print(f"   {address}: COM=({x1},{y1},{x2},{y2})  UIA không thấy ô ({t:.0f} ms)")


def print_events(excel: object) -> None:
    print("6) Sự kiện in (tín hiệu cho điều kiện printed_to_pdf):")
    ws = excel.ActiveSheet
    with tempfile.TemporaryDirectory() as tmp:
        for label, act in [
            (
                "In bằng máy in 'Microsoft Print to PDF'",
                lambda: ws.PrintOut(
                    ActivePrinter="Microsoft Print to PDF",
                    PrintToFile=True,
                    PrToFileName=str(Path(tmp) / "in.pdf"),
                ),
            ),
            (
                "Xuất PDF (ExportAsFixedFormat)",
                lambda: ws.ExportAsFixedFormat(0, str(Path(tmp) / "xuat.pdf")),
            ),
        ]:
            PRINT_EVENTS.clear()
            try:
                act()
            except pythoncom.com_error as exc:
                print(f"   {label}: lỗi {exc}")
                continue
            for _ in range(20):
                pythoncom.PumpWaitingMessages()
                time.sleep(0.05)
            print(f"   {label}: WorkbookBeforePrint {'CÓ' if PRINT_EVENTS else 'KHÔNG'} báo {PRINT_EVENTS}")


def catalog(window: auto.Control) -> None:
    """Xuất danh mục AutomationId (= idMso) của các nút trên các tab hay dùng."""
    lines = [
        "# Danh mục AutomationId (idMso) trên Ribbon Excel",
        "",
        "Sinh tự động bằng `uia_ribbon.py --catalog` (Microsoft 365, giao diện tiếng Anh). Dùng cho trường",
        "`ui_target` của kịch bản (T3.2). Cột **Tên hiển thị** đổi theo ngôn ngữ Office; cột **AutomationId** thì không.",
        "",
    ]
    for tab_id in CATALOG_TABS:
        tab = select_tab(window, tab_id)
        if tab is None:
            continue
        lower = window.Control(searchDepth=12, Name="Lower Ribbon")
        base = lower if lower.Exists(0, 0) else window
        seen: set[str] = set()
        rows = []
        for ctrl, _ in auto.WalkControl(base, maxDepth=20):
            aid = ctrl.AutomationId or ""
            if ctrl.ControlTypeName in CATALOG_KINDS and aid and not aid.isdigit() and aid not in seen:
                seen.add(aid)
                kind = ctrl.ControlTypeName.removesuffix("Control")
                rows.append(f"| `{aid}` | {ctrl.Name.replace('|', '/')} | {kind} |")
        lines += [
            f"## {tab.Name} (`{tab_id}`)",
            "",
            "| AutomationId | Tên hiển thị | Loại |",
            "|---|---|---|",
            *rows,
            "",
        ]
        print(f"   {tab_id}: {len(rows)} nút")
    CATALOG_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {CATALOG_FILE.name}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog", action="store_true", help="Xuất danh mục AutomationId ra danh-muc-idmso.md"
    )
    args = parser.parse_args()
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    win32com.client.WithEvents(excel, AppEvents)
    pid = win32process.GetWindowThreadProcessId(excel.Hwnd)[1]
    try:
        excel.Visible = True
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Add()
        wb.Worksheets(1).Range("A1").Value = 1234.5
        excel.WindowState = -4143  # xlNormal
        # Đủ rộng để Ribbon không gộp nhóm (nhóm bị gộp thì nút bên trong không có trong cây UIA)
        win32gui.SetWindowPos(excel.Hwnd, 0, 40, 40, 1500, 900, win32con.SWP_NOACTIVATE)
        time.sleep(1.5)
        window = auto.ControlFromHandle(excel.Hwnd)
        print(
            f"Cửa sổ Excel: {window.Name!r} | ngôn ngữ giao diện Office: {excel.LanguageSettings.LanguageID(2)} | "
            f"DPI cửa sổ: {ctypes.windll.user32.GetDpiForWindow(excel.Hwnd)} (96 = 100%)"
        )
        if args.catalog:
            excel.WindowState = -4137  # xlMaximized: Ribbon rộng nhất, không nhóm nào bị gộp
            time.sleep(1.0)
            catalog(window)
        else:
            ribbon_tabs(window)
            buttons = ribbon_buttons(window)
            toggle_state(excel, buttons)
            dialog(excel, window)
            cell_rect(excel, window)
            print_events(excel)
        wb.Close(SaveChanges=False)
    finally:
        close_dialogs(pid)
        excel.Quit()
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
