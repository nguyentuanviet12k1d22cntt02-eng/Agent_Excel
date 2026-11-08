/** Địa chỉ ô kiểu A1 (bản rút gọn của excel_core/address.py, chỉ để vẽ lên lưới mô phỏng). */

export interface Box {
  c1: number;
  r1: number;
  c2: number;
  r2: number;
}

export function colIndex(letters: string): number {
  let index = 0;
  for (const ch of letters.toUpperCase()) index = index * 26 + (ch.charCodeAt(0) - 64);
  return index;
}

export function colLetter(index: number): string {
  let letters = "";
  for (let n = index; n > 0; n = Math.floor((n - 1) / 26)) {
    letters = String.fromCharCode(65 + ((n - 1) % 26)) + letters;
  }
  return letters;
}

const CELL = /^\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6})$/;

function parseCell(text: string): [number, number] | null {
  const match = CELL.exec(text.trim().toUpperCase());
  if (!match?.[1] || !match[2]) return null;
  return [colIndex(match[1]), Number(match[2])];
}

/** "F10:F14", "H10", "$A$1:B2" → vùng; sai dạng (hoặc dải dòng/cột kiểu "5:7", "C:D") → null. */
export function parseRange(text: string): Box | null {
  const [first, second, extra] = text.split(":");
  if (first === undefined || extra !== undefined) return null;
  const a = parseCell(first);
  const b = second === undefined ? a : parseCell(second);
  if (!a || !b) return null;
  return {
    c1: Math.min(a[0], b[0]),
    r1: Math.min(a[1], b[1]),
    c2: Math.max(a[0], b[0]),
    r2: Math.max(a[1], b[1]),
  };
}

export function cellAddress(col: number, row: number): string {
  return `${colLetter(col)}${row}`;
}
