r"""Lệnh quản trị Backend.

    .venv\Scripts\python -m tutor_backend migrate          nâng CSDL lên migration mới nhất
    .venv\Scripts\python -m tutor_backend create-admin --email <email> --full-name "<họ tên>"
    .venv\Scripts\python -m tutor_backend serve [--reload]  chạy máy chủ (http://127.0.0.1:8000/docs)
    .venv\Scripts\python -m tutor_backend generate --starter de.xlsx --solution dap-an.xlsx ^
        --sheet "Bài 01" --code b22-ham-tinh-tong --title "Hàm SUM" [--out kich-ban.json]
                                                           sinh thử kịch bản bằng AI, không cần Web

`create-admin` hỏi mật khẩu (không hiện khi gõ); `--password-stdin` đọc mật khẩu từ stdin cho script.
Không nhận mật khẩu qua tham số dòng lệnh vì sẽ lộ trong lịch sử lệnh.
"""

import argparse
import getpass
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from tutor_backend.ai.exercise_analysis import analyze_exercise
from tutor_backend.ai.llm_client import LLMError
from tutor_backend.ai.script_agent import generate_script
from tutor_backend.ai.script_builder import ExerciseInfo
from tutor_backend.core.config import Settings, get_settings
from tutor_backend.core.errors import AppError
from tutor_backend.db.migrate import upgrade_database
from tutor_backend.db.session import create_db_engine, create_session_factory
from tutor_backend.models.enums import Role
from tutor_backend.schemas.user import UserCreate
from tutor_backend.services import account_service
from tutor_backend.services.generation_service import default_llm_factory


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


def _generate(args: argparse.Namespace, settings: Settings) -> int:
    analysis = analyze_exercise(args.starter, args.solution, args.sheet)
    print(f"Phân tích: {len(analysis.changes)} thay đổi, {len(analysis.global_checks)} điều kiện toàn bài")
    info = ExerciseInfo(args.code, args.title, args.sheet, args.prompt_text, args.instructions)
    try:
        llm = default_llm_factory(settings, args.model or settings.llm_model)
        outcome = generate_script(
            analysis, info, [], llm, (args.starter, args.solution), settings.generation_max_attempts
        )
    except LLMError as exc:
        print(f"Lỗi AI: {exc}")
        return 1
    print(
        f"{llm.model}: {outcome.attempts} lần gọi, {outcome.llm_ms / 1000:.1f} s, "
        f"token vào/ra {outcome.prompt_tokens}/{outcome.completion_tokens}"
    )
    for step in (outcome.script or {}).get("steps", []):
        print(f"  [{step['id']}] {step['title']} — {len(step['checks'])} điều kiện")
    for issue in outcome.remaining_issues:
        print(f"  [còn lỗi] {issue}")
    if args.out and outcome.script is not None:
        payload = {"script": outcome.script, "report": outcome.report}
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Đã lưu {args.out}")
    return 0 if outcome.ok else 1


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
    gen = commands.add_parser("generate", help="sinh thử kịch bản bằng AI cho một cặp file đề/đáp án")
    gen.add_argument("--starter", type=Path, required=True)
    gen.add_argument("--solution", type=Path, required=True)
    gen.add_argument("--sheet", required=True)
    gen.add_argument("--code", required=True)
    gen.add_argument("--title", required=True)
    gen.add_argument("--prompt-text", default=None)
    gen.add_argument("--instructions", default=None)
    gen.add_argument("--model", default=None)
    gen.add_argument("--out", type=Path, default=None, help="lưu kịch bản + báo cáo tự kiểm (JSON)")
    gen.set_defaults(handler=_generate)
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
