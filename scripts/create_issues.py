"""T0.6 — Tạo issue GitHub cho từng task trong docs/quan-ly/ke-hoach-trien-khai.md.

Mặc định chỉ IN RA những gì sẽ tạo (chạy thử). Thêm --apply để tạo thật bằng GitHub CLI (`gh`).

Ví dụ:
  python scripts/create_issues.py                       # chạy thử, mọi giai đoạn
  python scripts/create_issues.py --only GĐ0,GĐ1        # chạy thử, chỉ GĐ0 và GĐ1
  python scripts/create_issues.py --only GĐ0 --apply    # tạo thật

Yêu cầu khi --apply:
  - Đã cài GitHub CLI và đăng nhập: `gh auth login`
  - Chạy trong thư mục repo đã có remote GitHub
  - (Tùy chọn) file scripts/thanh_vien.json ánh xạ tên → tài khoản GitHub để gán người:
      {"Việt": "tuanvietdev", "Hoài": "...", "Linh": "...", "Hòa": "..."}
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "docs" / "quan-ly" / "ke-hoach-trien-khai.md"
MEMBERS_FILE = ROOT / "scripts" / "thanh_vien.json"
MEMBER_NAMES = ["Việt", "Hoài", "Linh", "Hòa"]

PHASE_RE = re.compile(r"^###\s+(GĐ\d+)\s+—\s+(.+?)\s*$")
ROW_RE = re.compile(r"^\|\s*(T\d+\.\d+)\s*\|")


@dataclass
class Task:
    task_id: str
    phase: str
    phase_title: str
    text: str
    done_when: str
    depends_on: str
    owners_raw: str
    owners: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        plain = re.sub(r"[*`]", "", self.text)
        short = re.split(r"[:;]", plain, maxsplit=1)[0].strip()
        if len(short) > 80:
            short = short[:77].rstrip() + "…"
        return f"[{self.task_id}] {short}"

    @property
    def body(self) -> str:
        return (
            f"**Giai đoạn:** {self.phase} — {self.phase_title}\n\n"
            f"**Việc cần làm:** {self.text}\n\n"
            f"**Hoàn thành khi:** {self.done_when}\n\n"
            f"**Cần trước:** {self.depends_on}\n\n"
            f"**Phụ trách:** {self.owners_raw}\n\n"
            f"---\nNguồn: `docs/quan-ly/ke-hoach-trien-khai.md`. "
            f"Nhánh gợi ý: `feature/{self.task_id}-<mo-ta>`. "
            f"Xong thì đổi cột TT của {self.task_id} sang ✅ trong cùng Pull Request."
        )


def parse_plan(path: Path) -> list[Task]:
    tasks: list[Task] = []
    phase, phase_title = "", ""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PHASE_RE.match(line)
        if m:
            phase, phase_title = m.group(1), m.group(2)
            continue
        if not ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            print(f"Bỏ qua dòng không đúng định dạng: {line[:60]}…", file=sys.stderr)
            continue
        task_id, text, done_when, depends_on, owners_raw = cells[:5]
        if "cả nhóm" in owners_raw.lower():
            owners = list(MEMBER_NAMES)
        else:
            owners = [n for n in MEMBER_NAMES if n in owners_raw]
        tasks.append(Task(task_id, phase, phase_title, text, done_when, depends_on, owners_raw, owners))
    return tasks


def run_gh(args: list[str]) -> None:
    subprocess.run(["gh", *args], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tạo issue GitHub từ kế hoạch triển khai.")
    parser.add_argument("--only", help="Danh sách giai đoạn, cách nhau bởi dấu phẩy. Ví dụ: GĐ0,GĐ1")
    parser.add_argument("--apply", action="store_true", help="Tạo issue thật (mặc định chỉ chạy thử)")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    tasks = parse_plan(PLAN)
    if args.only:
        wanted = {p.strip() for p in args.only.split(",")}
        tasks = [t for t in tasks if t.phase in wanted]
    if not tasks:
        print("Không có task nào phù hợp.")
        return 1

    members: dict[str, str] = {}
    if MEMBERS_FILE.exists():
        members = json.loads(MEMBERS_FILE.read_text(encoding="utf-8"))

    if args.apply and not shutil.which("gh"):
        print("Chưa cài GitHub CLI (gh). Cài tại https://cli.github.com rồi chạy `gh auth login`.")
        return 1

    if args.apply:
        for phase in sorted({t.phase for t in tasks}):
            run_gh(["label", "create", phase, "--color", "0E8A16", "--force"])

    for t in tasks:
        assignees = [members[o] for o in t.owners if members.get(o)]
        print(f"{t.title}  ·  label={t.phase}  ·  gán={','.join(assignees) or '(chưa có thanh_vien.json)'}")
        if args.apply:
            cmd = ["issue", "create", "--title", t.title, "--body", t.body, "--label", t.phase]
            for a in assignees:
                cmd += ["--assignee", a]
            run_gh(cmd)

    print(f"\nTổng: {len(tasks)} task." + ("" if args.apply else " (chạy thử — thêm --apply để tạo thật)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
