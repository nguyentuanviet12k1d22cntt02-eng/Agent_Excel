/** Đường dẫn JSON trong kịch bản → vị trí dễ đọc (không phụ thuộc Ajv, dùng được ở mọi trang). */

const SEGMENT_NAMES: Record<string, string> = {
  title: "Tên",
  task: "Thẻ yêu cầu",
  targets: "Vùng liên quan",
  text: "Lời gợi ý",
  alternative: "Cách làm khác",
  message: "Lời nhắn",
  signals: "Tín hiệu",
  idle_seconds: "Thời gian chờ",
  max_auto_level: "Cấp gợi ý tự đưa",
  immediate_codes: "Mã lỗi phản hồi ngay",
  completion: "Màn hình hoàn thành",
  exercise: "Thông tin bài",
  summary: "Mô tả",
  skills: "Kỹ năng",
  range: "Vùng",
  label: "Tên gọi",
  role: "Vai trò",
  severity: "Mức",
  code: "Mã lỗi",
  step_ids: "Các bước",
  meta: "Nguồn gốc",
  type: "Loại",
  steps: "Các bước",
  cells: "Vùng",
  hints: "Gợi ý",
  actions: "Các thao tác",
  highlight: "Chỉ vị trí",
  checks: "Điều kiện kiểm chứng",
  feedback: "Phản hồi",
  criteria: "Tiêu chí",
  references: "Nguồn trích",
  global_checks: "Điều kiện toàn bài",
};

const INDEXED_NAMES: Record<string, (n: number) => string> = {
  steps: (n) => `Bước ${n}`,
  cells: (n) => `Vùng ${n}`,
  ui: (n) => `Nút ${n}`,
  hints: (n) => `Gợi ý cấp ${n}`,
  actions: (n) => `Thao tác ${n}`,
  highlight: (n) => `Chỉ vị trí ${n}`,
  checks: (n) => `Điều kiện ${n}`,
  feedback: (n) => `Phản hồi ${n}`,
  global_checks: (n) => `Điều kiện toàn bài ${n}`,
  criteria: (n) => `Tiêu chí ${n}`,
  references: (n) => `Nguồn trích ${n}`,
};

/** "/steps/1/hints/3/actions/0" → "Bước 2 “Tên bước” › Gợi ý cấp 4 › Thao tác 1". */
export function describePath(path: string, script: unknown): string {
  const parts = path.split("/").filter(Boolean);
  const labels: string[] = [];
  let node: unknown = script;
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i] ?? "";
    const next = parts[i + 1];
    node = typeof node === "object" && node !== null ? (node as Record<string, unknown>)[part] : undefined;
    const indexed = INDEXED_NAMES[part];
    if (indexed && next !== undefined && /^\d+$/.test(next)) {
      node = Array.isArray(node) ? (node[Number(next)] as unknown) : undefined;
      const title = part === "steps" ? (node as { title?: unknown } | undefined)?.title : undefined;
      labels.push(indexed(Number(next) + 1) + (typeof title === "string" && title ? ` “${title}”` : ""));
      i++;
    } else {
      labels.push(SEGMENT_NAMES[part] ?? part);
    }
  }
  return labels.join(" › ") || "Kịch bản";
}
