import type { ScriptOrigin, ScriptStatus } from "@/api/types";

export const SCRIPT_STATUS_LABELS: Record<ScriptStatus, string> = {
  draft: "Nháp",
  pending_review: "Chờ duyệt",
  approved: "Đã duyệt",
  published: "Đang phát hành",
  archived: "Lưu trữ",
};

export const SCRIPT_ORIGIN_LABELS: Record<ScriptOrigin, string> = {
  ai: "AI sinh",
  teacher: "Giảng viên viết",
  ai_edited: "AI sinh, giảng viên sửa",
};
