import { createContext, useContext } from "react";

import type { Script, SelfCheckReport, Step } from "@/api/types";

import type { ScriptIssue } from "./scriptSchema";

/** Vùng đang xem trên lưới (ví dụ vùng của điều kiện vừa bấm). */
export interface FocusRange {
  range: string;
  sheet?: string;
  label?: string;
}

export interface EditorContextValue {
  draft: Script;
  saved: Script; // nội dung revision đang mở (để biết báo cáo tự kiểm còn đúng với phần nào)
  report: SelfCheckReport | null;
  issues: ScriptIssue[];
  readOnly: boolean;
  update: (change: (script: Script) => Script) => void;
  updateStep: (index: number, change: (step: Step) => Step) => void;
  focus: FocusRange | null;
  setFocus: (focus: FocusRange | null) => void;
}

export const EditorContext = createContext<EditorContextValue | null>(null);

export function useEditor(): EditorContextValue {
  const value = useContext(EditorContext);
  if (!value) throw new Error("useEditor phải dùng trong trình sửa kịch bản");
  return value;
}

/** Lỗi lược đồ ở đúng một trường (để tô đỏ ô nhập). */
export function issueAt(issues: ScriptIssue[], path: string): string | undefined {
  return issues.find((i) => i.path === path)?.message;
}

type ReportCheck = NonNullable<SelfCheckReport["checks"]>[number];

/**
 * Kết quả tự kiểm của một điều kiện. Báo cáo chạy trên bản đã lưu: điều kiện của bước đã bị sửa thì không
 * dùng (chỉ số có thể lệch), cần lưu để chạy lại.
 */
export function reportForCheck(
  report: SelfCheckReport | null,
  stepId: string | null,
  index: number,
): ReportCheck | undefined {
  return report?.checks?.find((c) => (c.step_id ?? null) === stepId && c.check_index === index);
}

export function stepChecksUnchanged(saved: Script, step: Step): boolean {
  const before = saved.steps.find((s) => s.id === step.id);
  return !!before && JSON.stringify(before.checks) === JSON.stringify(step.checks);
}
