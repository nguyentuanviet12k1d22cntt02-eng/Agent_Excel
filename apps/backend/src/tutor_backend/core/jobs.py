"""Tiến trình nền trong cùng tiến trình Backend (kien-truc.md A6): sinh kịch bản, lập chỉ mục giáo trình.

Quy mô lớp học nên dùng thread pool, không cần Celery/Redis. Trạng thái công việc lưu trong CSDL
(`generation_jobs`, `textbooks.status`), nên Web hỏi định kỳ là đủ.
"""

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class JobRunner(Protocol):
    def submit(self, fn: Callable[..., Any], *args: Any) -> None: ...

    def shutdown(self) -> None: ...


class ThreadJobRunner:
    def __init__(self, workers: int) -> None:
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tutor-job")

    def submit(self, fn: Callable[..., Any], *args: Any) -> None:
        future = self._executor.submit(fn, *args)
        future.add_done_callback(_log_failure)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class InlineJobRunner:
    """Chạy ngay trong luồng gọi: dùng cho test để kết quả có ngay khi API trả về."""

    def submit(self, fn: Callable[..., Any], *args: Any) -> None:
        fn(*args)

    def shutdown(self) -> None:
        return None


def _log_failure(future: Future[Any]) -> None:
    error = future.exception()
    if error is not None:
        # Công việc phải tự ghi lỗi vào CSDL; tới đây là lỗi lọt lưới
        logger.error("Tiến trình nền dừng vì lỗi không bắt: %r", error, exc_info=error)
