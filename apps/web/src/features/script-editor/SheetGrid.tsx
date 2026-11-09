import { useEffect, useMemo, useRef, type CSSProperties } from "react";

import { cellAddress, colLetter, parseRange } from "@/lib/a1";

import {
  colPx,
  overlayRects,
  ROW_HEADER_PX,
  rowPx,
  spanHeight,
  tableWidth,
  type Highlight,
  type PreviewCell,
  type SheetPreview,
} from "./sheetLayout";

interface Merge {
  rowSpan: number;
  colSpan: number;
}

function mergeMap(preview: SheetPreview): { starts: Map<string, Merge>; covered: Set<string> } {
  const starts = new Map<string, Merge>();
  const covered = new Set<string>();
  for (const range of preview.merged) {
    const box = parseRange(range);
    if (!box) continue;
    starts.set(cellAddress(box.c1, box.r1), { rowSpan: box.r2 - box.r1 + 1, colSpan: box.c2 - box.c1 + 1 });
    for (let r = box.r1; r <= box.r2; r++) {
      for (let c = box.c1; c <= box.c2; c++) {
        if (r !== box.r1 || c !== box.c1) covered.add(cellAddress(c, r));
      }
    }
  }
  return { starts, covered };
}

function cellStyle(cell: PreviewCell | undefined): CSSProperties | undefined {
  if (!cell) return undefined;
  const align = cell.align === "center_across" ? "center" : cell.align;
  return {
    fontWeight: cell.bold ? 700 : undefined,
    fontStyle: cell.italic ? "italic" : undefined,
    color: cell.color ?? undefined,
    background: cell.fill ?? undefined,
    textAlign: (align as CSSProperties["textAlign"]) ?? (cell.number ? "right" : undefined),
    whiteSpace: cell.wrap ? "normal" : undefined,
  };
}

/**
 * Lưới mô phỏng trang tính (T6.4): vẽ ô, ô gộp, độ rộng cột như Excel; vùng mục tiêu, vùng nguồn, vùng của
 * điều kiện đang chọn được khoanh bằng khung đè lên lưới.
 */
export function SheetGrid({ preview, highlights }: { preview: SheetPreview; highlights: Highlight[] }) {
  const container = useRef<HTMLDivElement>(null);
  const cells = useMemo(() => new Map(preview.cells.map((c) => [c.address, c])), [preview.cells]);
  const merges = useMemo(() => mergeMap(preview), [preview]);
  const rects = useMemo(() => overlayRects(preview, highlights), [preview, highlights]);
  const rows = Array.from({ length: preview.rows }, (_, i) => i + 1);
  const cols = Array.from({ length: preview.cols }, (_, i) => i + 1);

  // Cuộn tới vùng đang xem (điều kiện được chọn, hoặc vùng mục tiêu của bước)
  useEffect(() => {
    const focus = rects.find((r) => r.kind === "focus") ?? rects[0];
    const root = container.current;
    if (focus && root && typeof root.scrollTo === "function") {
      root.scrollTo({
        top: Math.max(0, focus.top - 60),
        left: Math.max(0, focus.left - 80),
        behavior: "smooth",
      });
    }
  }, [rects]);

  return (
    <div className="sheet" ref={container}>
      <table className="sheet__table" style={{ width: tableWidth(preview) }}>
        <colgroup>
          <col style={{ width: ROW_HEADER_PX }} />
          {cols.map((c) => (
            <col key={c} style={{ width: colPx(preview, colLetter(c)) }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th className="sheet__corner" />
            {cols.map((c) => (
              <th key={c} scope="col">
                {colLetter(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r} style={{ height: rowPx(preview, r) }}>
              <th scope="row">{r}</th>
              {cols.map((c) => {
                const address = cellAddress(c, r);
                if (merges.covered.has(address)) return null;
                const cell = cells.get(address);
                const merge = merges.starts.get(address);
                return (
                  <td
                    key={address}
                    data-address={address}
                    rowSpan={merge?.rowSpan}
                    colSpan={merge?.colSpan}
                    style={cellStyle(cell)}
                    title={cell?.formula ? `${address}: ${cell.formula}` : undefined}
                  >
                    {/* Chữ không được làm dòng cao lên: khung tô tính theo chiều cao dòng như Excel */}
                    <div
                      className="sheet__cell"
                      style={{ maxHeight: spanHeight(preview, r, merge?.rowSpan ?? 1) }}
                    >
                      {cell?.text}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {rects.map((r, i) => (
        <div
          key={`${r.kind}-${String(i)}`}
          className={`sheet__mark sheet__mark--${r.kind}`}
          style={{ top: r.top, left: r.left, width: r.width, height: r.height }}
          title={r.label}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
