/** Các phần của trình sửa kịch bản (mục lục bên trái). */
export type Section =
  | { kind: "overview" }
  | { kind: "step"; index: number }
  | { kind: "global" }
  | { kind: "completion" }
  | { kind: "references" };

export function sectionKey(section: Section): string {
  return section.kind === "step" ? `step-${String(section.index)}` : section.kind;
}
