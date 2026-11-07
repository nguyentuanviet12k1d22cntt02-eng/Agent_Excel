"""Kho file trên máy chủ (kien-truc.md mục 2: thư mục STORAGE_DIR, tên file theo id).

CSDL chỉ lưu đường dẫn **tương đối** so với gốc kho, nên chuyển máy chủ hay đổi STORAGE_DIR
không phải sửa dữ liệu.
"""

import logging
import shutil
from pathlib import Path, PurePosixPath

logger = logging.getLogger(__name__)


class StorageError(ValueError):
    """Đường dẫn ra ngoài kho file."""


class FileStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, relative: str) -> Path:
        """Đường dẫn thật của một file trong kho; chặn `..` để không đọc/ghi ra ngoài kho."""
        candidate = (self.root / PurePosixPath(relative)).resolve()
        if not candidate.is_relative_to(self.root):
            raise StorageError(f"Đường dẫn ra ngoài kho file: {relative!r}")
        return candidate

    def save(self, relative: str, data: bytes) -> str:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return PurePosixPath(relative).as_posix()

    def delete(self, relative: str | None) -> None:
        if relative:
            self.path(relative).unlink(missing_ok=True)

    def delete_dir(self, relative: str) -> None:
        target = self.path(relative)
        if target.is_dir():
            shutil.rmtree(target)

    def discard_dir(self, relative: str) -> None:
        """Dọn thư mục khi thao tác hỏng; lỗi khi dọn chỉ ghi log, không che lỗi gốc."""
        try:
            self.delete_dir(relative)
        except OSError as exc:
            logger.warning("Không dọn được %s: %s", relative, exc)
