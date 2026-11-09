/** Kích thước lưới mô phỏng và vị trí khung tô (tách khỏi SheetGrid để test và dùng lại). */
import type { components } from "@/api/schema";
import { colLetter, type Box } from "@/lib/a1";

export type SheetPreview = components["schemas"]["SheetPreview"];
export type PreviewCell = SheetPreview["cells"][number];

export type HighlightKind = "target" | "source" | "focus";

export interface Highlight {
  box: Box;
  kind: HighlightKind;
  label?: string;
}

const CHAR_PX = 7; // độ rộng một ký tự của phông mặc định Excel (Calibri 11) ở 100%
const DEFAULT_COL_CHARS = 8.43;
const DEFAULT_ROW_PT = 15;
const HIDDEN_PX = 4;
const MIN_COL_PX = 24;
export const ROW_HEADER_PX = 36;
const COL_HEADER_PX = 22; // khớp .sheet__table thead th trong editor.css

export function colPx(preview: SheetPreview, col: string): number {
  if (preview.hidden_cols.includes(col)) return HIDDEN_PX;
  return Math.max(MIN_COL_PX, Math.round((preview.col_widths[col] ?? DEFAULT_COL_CHARS) * CHAR_PX + 5));
}

export function rowPx(preview: SheetPreview, row: number): number {
  if (preview.hidden_rows.includes(row)) return HIDDEN_PX;
  return Math.round(((preview.row_heights[String(row)] ?? DEFAULT_ROW_PT) * 4) / 3);
}

interface OverlayRect extends Highlight {
  top: number;
  left: number;
  width: number;
  height: number;
}

function sumRange(sizes: number[], from: number, to: number): number {
  let total = 0;
  for (let i = from; i <= to; i++) total += sizes[i - 1] ?? 0;
  return total;
}

/**
 * Bề ngang cả bảng. Phải đặt đúng con số này: bảng table-layout: fixed mà để trình duyệt tự tính bề ngang thì
 * cột giãn theo chữ dài, khung tô (tính theo độ rộng cột) bị lệch sang cột khác.
 */
/** Chiều cao (px) của `count` dòng bắt đầu từ dòng `row`, trừ đường kẻ. */
export function spanHeight(preview: SheetPreview, row: number, count: number): number {
  let total = 0;
  for (let r = row; r < row + count; r++) total += rowPx(preview, r);
  return Math.max(0, total - 1);
}

export function tableWidth(preview: SheetPreview): number {
  let total = ROW_HEADER_PX;
  for (let c = 1; c <= preview.cols; c++) total += colPx(preview, colLetter(c));
  return total;
}

/** Vị trí khung trên lưới, tính từ độ rộng cột và chiều cao dòng (bảng dùng table-layout: fixed). */
export function overlayRects(preview: SheetPreview, highlights: Highlight[]): OverlayRect[] {
  const colSizes = Array.from({ length: preview.cols }, (_, i) => colPx(preview, colLetter(i + 1)));
  const rowSizes = Array.from({ length: preview.rows }, (_, i) => rowPx(preview, i + 1));
  return highlights
    .filter((h) => h.box.c1 <= preview.cols && h.box.r1 <= preview.rows)
    .map((h) => {
      const c2 = Math.min(h.box.c2, preview.cols);
      const r2 = Math.min(h.box.r2, preview.rows);
      return {
        ...h,
        left: ROW_HEADER_PX + sumRange(colSizes, 1, h.box.c1 - 1),
        top: COL_HEADER_PX + sumRange(rowSizes, 1, h.box.r1 - 1),
        width: sumRange(colSizes, h.box.c1, c2),
        height: sumRange(rowSizes, h.box.r1, r2),
      };
    });
}
