r"""Lệnh quản trị Backend.

    .venv\Scripts\python -m tutor_backend migrate          nâng CSDL lên migration mới nhất
    .venv\Scripts\python -m tutor_backend create-admin --email <email> --full-name "<họ tên>"
    .venv\Scripts\python -m tutor_backend serve [--reload]  chạy máy chủ (http://127.0.0.1:8000/docs)

`create-admin` hỏi mật khẩu (không hiện khi gõ); `--password-stdin` đọc mật khẩu từ stdin cho script.
Không nhận mật khẩu qua tham số dòng lệnh vì sẽ lộ trong lịch sử lệnh.
"""

import argparse
import getpass
import logging
import sys

from pydantic import ValidationError

from tutor_backend.core.config import Settings, get_settings
from tutor_backend.core.errors import AppError
from tutor_backend.db.migrate import upgrade_database
from tutor_backend.db.session import create_db_engine, create_session_factory
from tutor_backend.models.enums import Role
from tutor_backend.schemas.user import UserCreate
from tutor_backend.services import account_service


def _migrate(_: argparse.Namespace, settings: Settings) -> int:
    upgrade_database(settings.database_url)
    print("Đã nâng CSDL lên migration mới nhất.")
    return 0


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Mật khẩu (ít nhất 8 ký tự): ")
    if getpass.getpass("Nhập lại mật khẩu: ") != first:
        raise SystemExit("Hai lần nhập mật khẩu không khớp.")
    return first


def _create_admin(args: argparse.Namespace, settings: Settings) -> int:
    try:
        data = UserCreate(
            email=args.email,
            full_name=args.full_name,
            role=Role.ADMIN,
            password=_read_password(args.password_stdin),
        )
    except ValidationError as exc:
        print(f"Dữ liệu không hợp lệ: {exc.errors()[0]['loc'][0]} — {exc.errors()[0]['msg']}")
        return 2
    engine = create_db_engine(settings)
    try:
        with create_session_factory(engine)() as db:
            user = account_service.create_user(db, data)
    except AppError as exc:
        print(exc.message)
        return 1
    finally:
        engine.dispose()
    print(f"Đã tạo tài khoản quản trị {user.email}.")
    return 0


def _serve(args: argparse.Namespace, _: Settings) -> int:
    import uvicorn

    uvicorn.run(
        "tutor_backend.main:create_app", factory=True, host=args.host, port=args.port, reload=args.reload
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tutor_backend", description="Lệnh quản trị Backend.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="nâng CSDL lên migration mới nhất").set_defaults(handler=_migrate)
    admin = commands.add_parser("create-admin", help="tạo tài khoản quản trị đầu tiên")
    admin.add_argument("--email", required=True)
    admin.add_argument("--full-name", required=True)
    admin.add_argument("--password-stdin", action="store_true", help="đọc mật khẩu từ stdin")
    admin.set_defaults(handler=_create_admin)
    serve = commands.add_parser("serve", help="chạy máy chủ API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="tự khởi động lại khi sửa code")
    serve.set_defaults(handler=_serve)
    return parser


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    return args.handler(args, settings or get_settings())


if __name__ == "__main__":
    raise SystemExit(main())
