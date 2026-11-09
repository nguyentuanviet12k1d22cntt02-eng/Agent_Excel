r"""Điểm khởi động Desktop gia sư.

    .venv\Scripts\python -m tutor_desktop                    chế độ chạy thử cho giảng viên
    .venv\Scripts\python -m tutor_desktop --version <id>     chạy thử thẳng một bản kịch bản (id trên Web)

Chạy thử: đăng nhập bằng tài khoản giảng viên, chọn bản kịch bản (kể cả nháp), app tải một bản sao file đề
gốc, mở trong Excel đang chạy và hiện cửa sổ gia sư bên cạnh. Chế độ học viên (tự nhận bài, gợi ý theo tín
hiệu, gửi tiến độ) làm tiếp ở GĐ7.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSettings, QStandardPaths
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from excel_core.address import CellRange, parse_range
from excel_core.readers import full_request, read_workbook
from excel_core.script.self_check import is_procedure
from excel_core.snapshot import PropertyGroup, RangeRequest, ReadRequest, WorkbookSnapshot
from tutor_desktop.agent.preview_session import PreviewSession
from tutor_desktop.api_client.client import ApiClient, ApiError
from tutor_desktop.monitor.watcher import ExcelWatcher
from tutor_desktop.ui.dialogs import LoginDialog, PickerDialog
from tutor_desktop.ui.overlay import OverlayManager
from tutor_desktop.ui.preview_window import PreviewWindow

APP_NAME = "Gia sư Excel"


def _preview_copy(client: ApiClient, bundle: dict) -> Path:
    """Bản sao mới của file đề gốc cho mỗi lần chạy thử (lần trước sửa gì cũng không ảnh hưởng lần sau)."""
    folder = (
        Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        / "chay-thu"
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = folder / f"{bundle['exercise_code']}-ban-{bundle['revision']}-{stamp}.xlsx"
    return client.download_original_starter(str(bundle["exercise_id"]), target)


def layout_starter(path: Path, script: dict) -> WorkbookSnapshot | None:
    """File đề đọc từ A1 tới hết vùng đang dùng (giá trị + cấu trúc): dựng trạng thái mong đợi sau từng bước
    của kịch bản theo quy trình (báo bấm nhầm lệnh, quay lui khi hoàn tác). Đọc trước khi Excel mở file."""
    sheet = script["exercise"]["sheet"]
    if not is_procedure(script):
        return None
    used = next((parse_range(r.range) for r in full_request(path).ranges if r.sheet == sheet), None)
    if used is None:
        return None
    box = CellRange(1, 1, used.max_col, used.max_row)
    groups = frozenset({PropertyGroup.VALUES, PropertyGroup.STRUCTURE})
    return read_workbook(path, ReadRequest((RangeRequest(sheet, str(box), groups),)))


def run_preview(app: QApplication, version_id: str | None) -> int:
    settings = QSettings("TDMU", "GiaSuExcel")
    login = LoginDialog(settings)
    if login.exec() != QDialog.DialogCode.Accepted or login.client is None:
        return 0
    client = login.client
    if version_id is None:
        picker = PickerDialog(client)
        if picker.exec() != QDialog.DialogCode.Accepted or picker.version is None:
            return 0
        version_id = str(picker.version["id"])
    try:
        bundle = client.preview_bundle(version_id)
        path = _preview_copy(client, bundle)
    except ApiError as exc:
        QMessageBox.critical(None, APP_NAME, f"Không tải được kịch bản: {exc}")
        return 1
    session = PreviewSession(bundle["content"], bundle["references"], layout_starter(path, bundle["content"]))
    watcher = ExcelWatcher(path)
    watcher.set_request(session.read_request())
    window = PreviewWindow(session, bundle, watcher, OverlayManager(app))
    window.show()
    watcher.start()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    # Console Windows mặc định dùng cp1252, in tiếng Việt sẽ lỗi (quy-tac-code.md mục 2.2)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="python -m tutor_desktop", description="Gia sư Excel trên Windows.")
    parser.add_argument("--version", dest="version_id", help="id bản kịch bản cần chạy thử (xem trên Web)")
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    return run_preview(app, args.version_id)


if __name__ == "__main__":
    sys.exit(main())
