/** Bỏ dấu tiếng Việt (cả đ/Đ, NFD không tách được hai chữ này). */
export function stripAccents(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").replace(/đ/g, "d").replace(/Đ/g, "D");
}

/** Gợi ý mã bài từ tên bài: chữ thường không dấu, số, gạch nối (khớp mẫu ExerciseCode của API). */
export function slugify(text: string, maxLength = 64): string {
  return stripAccents(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, maxLength)
    .replace(/-+$/, "");
}

export const EXERCISE_CODE_PATTERN = /^[a-z0-9][a-z0-9-]{2,63}$/;
