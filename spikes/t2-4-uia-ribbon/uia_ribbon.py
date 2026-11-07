"""T2.4 — UI Automation / MSAA: Ribbon, nút lệnh, hộp thoại, vị trí ô.

Chạy:  .venv\\Scripts\\python spikes\\t2-4-uia-ribbon\\uia_ribbon.py
(Một cửa sổ Excel riêng sẽ hiện lên ~20 giây. Không giả lập bàn phím/chuột.)

Kiểm tra:
  1. Tìm các tab Ribbon, biết tab nào đang chọn.
  2. Tìm nút theo tên và theo AutomationId, lấy tọa độ màn hình (để overlay chỉ vào).
  3. Đọc trạng thái nút bật/tắt (Bold) qua UIA TogglePattern và MSAA (LegacyIAccessible).
  4. Phát hiện hộp thoại Format Cells, tab đang chọn bên trong, mục đang chọn trong danh sách Category.
  5. Đo thời gian mỗi lần tìm.
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time

import pythoncom
import uiautomation as auto
import win32com.client
import win32con
import win32gui
import win32process

BUTTONS = [
    "Comma Style",
    "Decrease Decimal",
    "Increase Decimal",
    "Align Right",
    "Bold",
    "AutoSum",
    "Sort & Filter",
]
XL_DIALOG_FORMAT_NUMBER = 42
MSAA_STATE_PRESSED = 0x8


def timed(fn: object) -> tuple[object, float]:
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000


def find_by_name(
    root: auto.Control, name: str, control_type: str | None = None, depth: int = 30
) -> auto.Control | None:
    def match(c: auto.Control, _depth: int) -> bool:
        return c.Name == name and (control_type is None or c.ControlTypeName == control_type)

    found = root.Control(searchDepth=depth, Compare=match)
    return found if found.Exists(0, 0) else None


def ribbon_tabs(window: auto.Control) -> None:
    print("1) Tab Ribbon:")
    all_tabs, t = timed(
        lambda: [c for c, _ in auto.WalkControl(window, maxDepth=12) if c.ControlTypeName == "TabItemControl"]
    )
    tabs = [c for c in all_tabs if c.GetParentControl().Name == "Ribbon Tabs"]
    others = [c.Name for c in all_tabs if c not in tabs]
    print(f"   {len(tabs)} tab Ribbon ({t:.0f} ms): {[c.Name for c in tabs]}")
    print(f"   TabItem khác (không phải Ribbon, ví dụ tab sheet): {others}")
    selected = [c.Name for c in tabs if c.GetSelectionItemPattern().IsSelected]
    print(f"   Tab Ribbon đang chọn khi mới mở: {selected or 'không có (Ribbon chưa chọn tab nào)'}")
    home = next((c for c in tabs if c.Name == "Home"), None)
    if home:
        home.GetSelectionItemPattern().Select()
        time.sleep(0.8)
        print(
            f"   Sau khi chọn Home qua UIA: đang chọn {[c.Name for c in tabs if c.GetSelectionItemPattern().IsSelected]}"
        )


def ribbon_buttons(window: auto.Control) -> dict[str, auto.Control]:
    print("2) Nút lệnh trên tab Home:")
    found: dict[str, auto.Control] = {}
    for name in BUTTONS:
        ctrl, t = timed(lambda name=name: find_by_name(window, name))
        if not ctrl:
            print(f"   {name:<18} KHÔNG thấy ({t:.0f} ms)")
            continue
        r = ctrl.BoundingRectangle
        print(
            f"   {name:<18} loại={ctrl.ControlTypeName:<22} AutomationId={ctrl.AutomationId!r:<22} "
            f"tọa độ=({r.left},{r.top},{r.right},{r.bottom}) ({t:.0f} ms)"
        )
        found[name] = ctrl
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
            f"(pressed={bool(state & MSAA_STATE_PRESSED)}), COM CommandBars.GetPressedMso('Bold')={pressed_mso}"
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


def close_dialogs(excel: object) -> None:
    """Dọn dẹp: đóng mọi hộp thoại còn mở của phiên Excel riêng trước khi Quit."""
    pid = win32process.GetWindowThreadProcessId(excel.Hwnd)[1]
    while hwnd := find_dialog_hwnd(pid):
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(0.3)


def dialog(excel: object) -> None:
    print("4) Hộp thoại Format Cells:")
    stream = pythoncom.CoMarshalInterThreadInterfaceInStream(pythoncom.IID_IDispatch, excel._oleobj_)

    def show() -> None:
        pythoncom.CoInitialize()
        app = win32com.client.Dispatch(
            pythoncom.CoGetInterfaceAndReleaseStream(stream, pythoncom.IID_IDispatch)
        )
        try:
            app.Dialogs(XL_DIALOG_FORMAT_NUMBER).Show()
        finally:
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=show, daemon=True)
    thread.start()
    pid = win32process.GetWindowThreadProcessId(excel.Hwnd)[1]
    dlg = None
    start = time.perf_counter()
    while time.perf_counter() - start < 5 and dlg is None:
        hwnd = find_dialog_hwnd(pid)
        dlg = auto.ControlFromHandle(hwnd) if hwnd else None
        time.sleep(0.1)
    if not dlg:
        print("   Không thấy hộp thoại")
        return
    print(
        f"   Hộp thoại: Name={dlg.Name!r}, ClassName={dlg.ClassName!r} ({(time.perf_counter() - start) * 1000:.0f} ms)"
    )
    tabs = [c for c, _ in auto.WalkControl(dlg, maxDepth=6) if c.ControlTypeName == "TabItemControl"]
    sel_tab = [t.Name for t in tabs if t.GetSelectionItemPattern().IsSelected]
    print(f"   Các tab: {[t.Name for t in tabs]} — đang chọn: {sel_tab}")
    lists = [c for c, _ in auto.WalkControl(dlg, maxDepth=8) if c.ControlTypeName == "ListControl"]
    for lst in lists[:2]:
        items = [i for i in lst.GetChildren() if i.ControlTypeName == "ListItemControl"]
        chosen = [i.Name for i in items if i.GetSelectionItemPattern().IsSelected]
        print(f"   Danh sách {lst.Name!r}: {len(items)} mục, đang chọn {chosen}")
    win32gui.PostMessage(dlg.NativeWindowHandle, win32con.WM_CLOSE, 0, 0)
    thread.join(timeout=5)
    print(f"   Đóng hộp thoại: {'được' if not thread.is_alive() else 'KHÔNG'}")


def cell_rect(excel: object, window: auto.Control) -> None:
    print("5) Vị trí ô trên màn hình — so sánh UIA với công thức COM PointsToScreenPixels:")
    ws = excel.ActiveSheet
    pane = excel.ActiveWindow.ActivePane
    for address in ("A1", "C5", "F12"):
        rng = ws.Range(address)
        x1 = pane.PointsToScreenPixelsX(rng.Left)
        y1 = pane.PointsToScreenPixelsY(rng.Top)
        x2 = pane.PointsToScreenPixelsX(rng.Left + rng.Width)
        y2 = pane.PointsToScreenPixelsY(rng.Top + rng.Height)
        item, t = timed(lambda address=address: find_by_name(window, address, "DataItemControl"))
        if item:
            r = item.BoundingRectangle
            uia = (r.left, r.top, r.right, r.bottom)
            diff = max(abs(a - b) for a, b in zip((x1, y1, x2, y2), uia, strict=True))
            print(
                f"   {address}: COM=({x1},{y1},{x2},{y2})  UIA={uia}  lệch tối đa {diff} px  (tìm UIA {t:.0f} ms)"
            )
        else:
            print(f"   {address}: COM=({x1},{y1},{x2},{y2})  UIA không thấy ô ({t:.0f} ms)")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    try:
        excel.Visible = True
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Add()
        wb.Worksheets(1).Range("A1").Value = 1234.5
        excel.WindowState = -4143  # xlNormal
        time.sleep(1.5)
        window = auto.ControlFromHandle(excel.Hwnd)
        print(
            f"Cửa sổ Excel: {window.Name!r} | ngôn ngữ giao diện Office: {excel.LanguageSettings.LanguageID(2)} | "
            f"DPI cửa sổ: {ctypes.windll.user32.GetDpiForWindow(excel.Hwnd)} (96 = 100%)"
        )
        ribbon_tabs(window)
        buttons = ribbon_buttons(window)
        toggle_state(excel, buttons)
        dialog(excel)
        cell_rect(excel, window)
        wb.Close(SaveChanges=False)
    finally:
        close_dialogs(excel)
        excel.Quit()
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
