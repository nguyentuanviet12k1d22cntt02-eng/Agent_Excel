/**
 * So sánh hai revision kịch bản theo từng trường (FR-W09): bản AI sinh với bản giảng viên sửa. Dữ liệu cho
 * "tỷ lệ bước phải sửa" của đánh giá kỹ thuật (T5.8) cũng từ đây mà ra.
 */
import { describePath } from "@/features/script-editor/scriptPaths";

export interface ScriptChange {
  path: string;
  where: string;
  kind: "added" | "removed" | "changed";
  before?: string;
  after?: string;
}

// Số revision và nguồn gốc luôn khác giữa hai bản, không phải nội dung giảng viên sửa
const IGNORED = ["/revision", "/meta"];

function flatten(value: unknown, path: string, out: Map<string, string>): void {
  if (Array.isArray(value)) {
    if (value.length === 0) out.set(path, "[]");
    value.forEach((item, i) => {
      flatten(item, `${path}/${String(i)}`, out);
    });
  } else if (typeof value === "object" && value !== null) {
    const entries = Object.entries(value);
    if (entries.length === 0) out.set(path, "{}");
    for (const [key, item] of entries) flatten(item, `${path}/${key}`, out);
  } else {
    out.set(path, typeof value === "string" ? value : JSON.stringify(value));
  }
}

function leaves(script: unknown): Map<string, string> {
  const out = new Map<string, string>();
  flatten(script, "", out);
  for (const path of out.keys()) {
    if (IGNORED.some((p) => path === p || path.startsWith(`${p}/`))) out.delete(path);
  }
  return out;
}

export function diffScripts(before: unknown, after: unknown): ScriptChange[] {
  const a = leaves(before);
  const b = leaves(after);
  const paths = [...new Set([...a.keys(), ...b.keys()])].sort((x, y) =>
    x.localeCompare(y, "en", { numeric: true }),
  );
  return paths.flatMap((path): ScriptChange[] => {
    const old = a.get(path);
    const now = b.get(path);
    if (old === now) return [];
    const kind = old === undefined ? "added" : now === undefined ? "removed" : "changed";
    return [
      { path, where: describePath(path, now === undefined ? before : after), kind, before: old, after: now },
    ];
  });
}

/** Số bước có thay đổi (so theo vị trí bước), để nhìn nhanh mức độ sửa. */
export function changedSteps(changes: ScriptChange[]): number {
  return new Set(changes.map((c) => /^\/steps\/(\d+)/.exec(c.path)?.[1]).filter(Boolean)).size;
}
