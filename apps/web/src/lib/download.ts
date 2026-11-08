/** Lưu một file về máy người dùng (file đề đã nhúng mã bài, danh sách mật khẩu, file mẫu). */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** CSV UTF-8 có BOM để Excel mở đúng tiếng Việt. */
export function saveCsv(text: string, filename: string): void {
  saveBlob(new Blob(["\uFEFF", text], { type: "text/csv;charset=utf-8" }), filename);
}

export function csvCell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}
