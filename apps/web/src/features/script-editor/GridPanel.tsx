import { useMemo, useState } from "react";

import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { parseRange } from "@/lib/a1";

import { useSheetPreview, type PreviewFile } from "./scriptApi";
import { SheetGrid } from "./SheetGrid";
import type { Highlight, HighlightKind } from "./sheetLayout";

export interface RangeMark {
  range: string;
  sheet?: string;
  kind: HighlightKind;
  label?: string;
}

/** Lưới mô phỏng trang tính bên phải trình sửa: chọn file đề / đáp án, khoanh vùng liên quan. */
export function GridPanel({
  exerciseId,
  defaultSheet,
  marks,
}: {
  exerciseId: string;
  defaultSheet: string;
  marks: RangeMark[];
}) {
  const [file, setFile] = useState<PreviewFile>("starter");
  const focusSheet = marks.find((m) => m.kind === "focus")?.sheet;
  const [chosenSheet, setChosenSheet] = useState<string | null>(null);
  const sheet = focusSheet ?? chosenSheet ?? defaultSheet;
  const preview = useSheetPreview(exerciseId, file, sheet);

  const highlights = useMemo<Highlight[]>(
    () =>
      marks.flatMap((m) => {
        const box = (m.sheet ?? defaultSheet) === sheet ? parseRange(m.range) : null;
        return box ? [{ box, kind: m.kind, label: m.label ?? m.range }] : [];
      }),
    [marks, sheet, defaultSheet],
  );

  return (
    <section className="grid-panel" aria-label="Lưới mô phỏng trang tính">
      <div className="grid-panel__toolbar">
        <div className="segmented" role="group" aria-label="File">
          <button type="button" aria-pressed={file === "starter"} onClick={() => setFile("starter")}>
            File đề
          </button>
          <button type="button" aria-pressed={file === "solution"} onClick={() => setFile("solution")}>
            File đáp án
          </button>
        </div>
        {preview.data && preview.data.sheet_names.length > 1 && (
          <select
            aria-label="Trang tính"
            value={sheet}
            onChange={(e) => setChosenSheet(e.target.value)}
            disabled={!!focusSheet}
          >
            {preview.data.sheet_names.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="grid-panel__legend small">
        <span className="legend legend--target">Học viên làm</span>
        <span className="legend legend--source">Dữ liệu nguồn</span>
        <span className="legend legend--focus">Đang xem</span>
      </div>
      {preview.isPending && <Loading label="Đang đọc trang tính…" />}
      <ErrorAlert error={preview.error} />
      {preview.data && (
        <>
          <SheetGrid preview={preview.data} highlights={highlights} />
          {preview.data.truncated && (
            <p className="muted small">Trang tính lớn: chỉ hiện {preview.data.range}.</p>
          )}
        </>
      )}
    </section>
  );
}
