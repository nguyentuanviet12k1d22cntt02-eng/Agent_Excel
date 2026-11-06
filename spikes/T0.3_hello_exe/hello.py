"""T0.3 — App "hello" kiểm tra môi trường đóng gói Desktop.

Kiểm tra 3 điều sau khi đóng gói bằng PyInstaller:
  1. PyQt6 hiển thị được cửa sổ.
  2. pywin32 (win32com) import được.
  3. Kết nối COM tới Excel: đọc phiên bản Excel.

Chạy:
  python hello.py                      # mở cửa sổ
  python hello.py --selftest out.json  # không mở cửa sổ, ghi kết quả ra file JSON
"""

from __future__ import annotations

import json
import platform
import sys
import traceback


def check_excel_com() -> dict:
    """Mở một phiên Excel RIÊNG (không đụng vào Excel người dùng đang mở), đọc phiên bản rồi đóng."""
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        excel = win32com.client.DispatchEx("Excel.Application")
        try:
            excel.Visible = False
            excel.DisplayAlerts = False
            return {
                "ok": True,
                "excel_version": str(excel.Version),
                "excel_build": str(excel.Build),
                "language_id": int(excel.LanguageSettings.LanguageID(2)),  # 2 = giao diện người dùng
            }
        finally:
            excel.Quit()
            pythoncom.CoUninitialize()
    except Exception as exc:  # noqa: BLE001 — spike: muốn thấy mọi lỗi
        return {"ok": False, "error": repr(exc), "trace": traceback.format_exc()}


def collect_report() -> dict:
    from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR

    try:
        import win32api  # noqa: F401 — chỉ kiểm tra import

        pywin32 = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        pywin32 = {"ok": False, "error": repr(exc)}

    return {
        "frozen": bool(getattr(sys, "frozen", False)),
        "python": platform.python_version(),
        "pyqt": PYQT_VERSION_STR,
        "qt": QT_VERSION_STR,
        "windows": platform.platform(),
        "pywin32": pywin32,
        "excel_com": check_excel_com(),
    }


def run_gui() -> int:
    from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    app = QApplication(sys.argv)
    report = collect_report()
    excel = report["excel_com"]
    lines = [
        "<h2>Gia sư Excel — kiểm tra môi trường</h2>",
        f"Python {report['python']} · PyQt {report['pyqt']} · Qt {report['qt']}",
        f"Đóng gói (.exe): {'có' if report['frozen'] else 'không'}",
        f"pywin32: {'OK' if report['pywin32']['ok'] else 'LỖI'}",
        (
            f"Excel COM: OK — phiên bản {excel['excel_version']} (build {excel['excel_build']}),"
            f" ngôn ngữ giao diện {excel['language_id']}"
            if excel["ok"]
            else f"Excel COM: LỖI — {excel['error']}"
        ),
    ]
    win = QWidget()
    win.setWindowTitle("Hello — Gia sư Excel")
    layout = QVBoxLayout(win)
    label = QLabel("<br>".join(lines))
    label.setWordWrap(True)
    layout.addWidget(label)
    win.resize(520, 220)
    win.show()
    return app.exec()


def run_selftest(out_path: str) -> int:
    from PyQt6.QtWidgets import QApplication, QWidget

    app = QApplication(sys.argv)
    QWidget()  # tạo widget để chắc chắn Qt khởi tạo được, không hiển thị
    report = collect_report()
    app.quit()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if report["pywin32"]["ok"] and report["excel_com"]["ok"] else 1


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        sys.exit(run_selftest(sys.argv[2]))
    sys.exit(run_gui())
