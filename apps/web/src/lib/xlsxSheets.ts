/**
 * Đọc tên các trang tính trong file .xlsx ngay trên trình duyệt, để giảng viên chọn sheet làm bài từ danh
 * sách thay vì gõ tay (gõ sai thì Backend báo sheet_not_found).
 *
 * File .xlsx là ZIP; chỉ cần giải nén một mục `xl/workbook.xml`, nên đọc thư mục trung tâm của ZIP và dùng
 * DecompressionStream có sẵn của trình duyệt, không thêm thư viện ZIP.
 */

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_SIGNATURE = 0x02014b50;
const LOCAL_SIGNATURE = 0x04034b50;
const EOCD_MIN_SIZE = 22;
const MAX_COMMENT = 0xffff;
const WORKBOOK_ENTRY = "xl/workbook.xml";

export class XlsxReadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "XlsxReadError";
  }
}

function findEndOfCentralDirectory(view: DataView): number {
  const lowest = Math.max(0, view.byteLength - EOCD_MIN_SIZE - MAX_COMMENT);
  for (let i = view.byteLength - EOCD_MIN_SIZE; i >= lowest; i--) {
    if (view.getUint32(i, true) === EOCD_SIGNATURE) return i;
  }
  throw new XlsxReadError("Không phải file .xlsx hợp lệ");
}

interface ZipEntry {
  method: number;
  compressedSize: number;
  localOffset: number;
}

function findEntry(view: DataView, bytes: Uint8Array, name: string): ZipEntry {
  const eocd = findEndOfCentralDirectory(view);
  const count = view.getUint16(eocd + 10, true);
  let offset = view.getUint32(eocd + 16, true);
  const decoder = new TextDecoder();
  for (let i = 0; i < count; i++) {
    if (view.getUint32(offset, true) !== CENTRAL_SIGNATURE) break;
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const entryName = decoder.decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
    if (entryName === name) {
      return {
        method: view.getUint16(offset + 10, true),
        compressedSize: view.getUint32(offset + 20, true),
        localOffset: view.getUint32(offset + 42, true),
      };
    }
    offset += 46 + nameLength + extraLength + commentLength;
  }
  throw new XlsxReadError("Không phải file .xlsx hợp lệ (thiếu xl/workbook.xml)");
}

async function inflate(data: Uint8Array<ArrayBuffer>): Promise<string> {
  const body = new Response(data).body;
  if (!body) throw new XlsxReadError("File .xlsx bị hỏng");
  return new Response(body.pipeThrough(new DecompressionStream("deflate-raw"))).text();
}

async function readEntry(buffer: ArrayBuffer, name: string): Promise<string> {
  const view = new DataView(buffer);
  const bytes = new Uint8Array(buffer);
  const entry = findEntry(view, bytes, name);
  if (view.getUint32(entry.localOffset, true) !== LOCAL_SIGNATURE) {
    throw new XlsxReadError("File .xlsx bị hỏng");
  }
  const start =
    entry.localOffset +
    30 +
    view.getUint16(entry.localOffset + 26, true) +
    view.getUint16(entry.localOffset + 28, true);
  const data = bytes.slice(start, start + entry.compressedSize);
  if (entry.method === 0) return new TextDecoder().decode(data);
  if (entry.method === 8) return inflate(data);
  throw new XlsxReadError("File .xlsx nén theo kiểu không hỗ trợ");
}

/** Tên các sheet theo thứ tự trong file. */
export function sheetNamesFromWorkbookXml(xml: string): string[] {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  return Array.from(doc.getElementsByTagNameNS("*", "sheet"))
    .map((sheet) => sheet.getAttribute("name"))
    .filter((name): name is string => !!name);
}

export async function readSheetNames(file: Blob): Promise<string[]> {
  return sheetNamesFromWorkbookXml(await readEntry(await file.arrayBuffer(), WORKBOOK_ENTRY));
}
