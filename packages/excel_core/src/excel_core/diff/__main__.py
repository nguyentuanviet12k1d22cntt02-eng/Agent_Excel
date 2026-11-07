r"""In diff giữa file đề và file đáp án.

.venv\Scripts\python -m excel_core.diff de.xlsx dap-an.xlsx
"""

import argparse
import sys
from pathlib import Path

from excel_core.diff import diff_files


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="python -m excel_core.diff", description="So sánh file đề với file đáp án."
    )
    parser.add_argument("starter", type=Path, help="file đề (.xlsx)")
    parser.add_argument("solution", type=Path, help="file đáp án (.xlsx)")
    args = parser.parse_args()
    diff = diff_files(args.starter, args.solution)
    print(diff.to_text() or "(không có thay đổi)")
    print(f"--- {len(diff)} thay đổi, {len(diff.cell_changes())} trên vùng ô")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
