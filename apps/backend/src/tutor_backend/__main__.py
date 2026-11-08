r"""Lệnh quản trị Backend.

    .venv\Scripts\python -m tutor_backend migrate          nâng CSDL lên migration mới nhất
    .venv\Scripts\python -m tutor_backend create-admin --email <email> --full-name "<họ tên>"
    .venv\Scripts\python -m tutor_backend serve [--reload]  chạy máy chủ (http://127.0.0.1:8000/docs)
    .venv\Scripts\python -m tutor_backend generate --starter de.xlsx --solution dap-an.xlsx ^
        --sheet "Bài 01" --code b22-ham-tinh-tong --title "Hàm SUM" [--out kich-ban.json]
                                                           sinh thử kịch bản bằng AI, không cần Web

    .venv\Scripts\python -m tutor_backend evaluate --runs 3 [--samples-dir samples\_local] [--out ket-qua.md]
                                                           đánh giá AI sinh so với kịch bản viết tay (T5.8)

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

from tutor_backend.ai.evaluation import (
    SUMMARY_HEADER,
    EvaluationCase,
    RunResult,
    markdown_table,
    results_json,
    run_evaluation,
    summary_rows,
)
from tutor_backend.ai.exercise_analysis import analyze_exercise
from tutor_backend.ai.llm_client import LLMError
from tutor_backend.ai.script_agent import generate_script
from tutor_backend.ai.script_builder import ExerciseInfo
from tutor_backend.core.config import BACKEND_DIR, Settings, get_settings
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


REPO = BACKEND_DIR.parents[1]
FIXTURES = REPO / "packages" / "excel_core" / "tests" / "fixtures"
EXAMPLES = REPO / "schemas" / "tutor-script" / "v1" / "examples"
# (thư mục file test, sheet làm bài, mã bài, tên bài, có kịch bản viết tay để so không)
EVALUATION_CASES = [
    ("b09", "2. Bang_Ke_Ban_Hang", "b09-du-lieu-dang-so", "Định dạng dữ liệu số", True),
    ("b22", "Bài 01", "b22-ham-tinh-tong", "Hàm tính tổng SUM", True),
    ("b14", "Bang_Diem", "b14-tao-bang-tinh", "Tạo bảng tính", False),
    ("b16", "Bai 01", "b16-sap-xep-du-lieu", "Sắp xếp dữ liệu", False),
]


def _evaluation_cases(samples_dir: Path | None) -> list[EvaluationCase]:
    cases = []
    for folder, sheet, code, title, has_reference in EVALUATION_CASES:
        base = FIXTURES / folder
        source = "tự soạn"
        if samples_dir is not None and (samples_dir / code / "dap-an.xlsx").is_file():
            base, source = samples_dir / code, "bài trung tâm"
        reference = None
        if has_reference:
            reference = json.loads((EXAMPLES / f"{code}.json").read_text(encoding="utf-8"))
        cases.append(
            EvaluationCase(
                f"{code} ({source})",
                base / "de.xlsx",
                base / "dap-an.xlsx",
                ExerciseInfo(code, title, sheet),
                reference,
            )
        )
    return cases


def _evaluate(args: argparse.Namespace, settings: Settings) -> int:
    cases = _evaluation_cases(args.samples_dir)
    model = args.model or settings.llm_model
    try:
        default_llm_factory(settings, model)  # báo sớm nếu thiếu API key
    except LLMError as exc:
        print(f"Lỗi AI: {exc}")
        return 1

    def report(result: RunResult) -> None:
        status = "đạt" if result.ok else f"CHƯA ĐẠT ({result.error})"
        seconds = result.llm_ms / 1000
        print(f"  {result.case} lần {result.run}: {status}, {result.attempts} lần gọi, {seconds:.1f} s")

    results = run_evaluation(
        cases,
        lambda: default_llm_factory(settings, model),
        args.runs,
        settings.generation_max_attempts,
        on_result=report,
    )
    table = markdown_table(SUMMARY_HEADER, summary_rows(results, cases))
    print(table)
    if args.out:
        args.out.write_text(f"Mô hình: {model}, {args.runs} lần mỗi bài\n\n{table}\n", encoding="utf-8")
        args.out.with_suffix(".json").write_text(results_json(results), encoding="utf-8")
        print(f"Đã lưu {args.out} và {args.out.with_suffix('.json')}")
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
    evaluate = commands.add_parser("evaluate", help="đánh giá kịch bản AI so với kịch bản viết tay (T5.8)")
    evaluate.add_argument("--runs", type=int, default=3, help="số lần sinh mỗi bài")
    evaluate.add_argument(
        "--samples-dir", type=Path, default=None, help="dùng bài thật, ví dụ samples/_local"
    )
    evaluate.add_argument("--model", default=None)
    evaluate.add_argument(
        "--out", type=Path, default=None, help="lưu bảng kết quả (.md) và số liệu thô (.json)"
    )
    evaluate.set_defaults(handler=_evaluate)
    serve = commands.add_parser("serve", help="chạy máy chủ API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="tự khởi động lại khi sửa code")
    serve.set_defaults(handler=_serve)
    return parser


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    # Log ghi ra stderr: cũng chuyển sang UTF-8, nếu không tiếng Việt trong log bị in thành \uXXXX
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    return args.handler(args, settings or get_settings())


if __name__ == "__main__":
    raise SystemExit(main())
