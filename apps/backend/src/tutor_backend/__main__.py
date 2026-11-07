r"""Lệnh quản trị Backend.

.venv\Scripts\python -m tutor_backend migrate          nâng CSDL lên migration mới nhất
.venv\Scripts\python -m tutor_backend serve [--reload]  chạy máy chủ (http://127.0.0.1:8000/docs)
"""

import argparse
import logging
import sys

from tutor_backend.core.config import get_settings
from tutor_backend.db.migrate import upgrade_database


def _migrate(_: argparse.Namespace) -> int:
    upgrade_database(get_settings().database_url)
    print("Đã nâng CSDL lên migration mới nhất.")
    return 0


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "tutor_backend.main:create_app", factory=True, host=args.host, port=args.port, reload=args.reload
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tutor_backend", description="Lệnh quản trị Backend.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="nâng CSDL lên migration mới nhất").set_defaults(handler=_migrate)
    serve = commands.add_parser("serve", help="chạy máy chủ API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="tự khởi động lại khi sửa code")
    serve.set_defaults(handler=_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
