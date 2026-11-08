/** Dữ liệu mẫu cho test, đúng kiểu sinh từ openapi.yaml. */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { Exercise, ScriptVersionSummary, Textbook } from "@/api/types";

export const EXERCISE_ID = "11111111-1111-4111-8111-111111111111";
export const VERSION_ID = "22222222-2222-4222-8222-222222222222";

export function textbook(overrides: Partial<Textbook> = {}): Textbook {
  return {
    id: "33333333-3333-4333-8333-333333333333",
    title: "Giáo trình Excel cơ bản",
    file_type: "pdf",
    status: "ready",
    chunk_count: 42,
    ...overrides,
  };
}

export function versionSummary(overrides: Partial<ScriptVersionSummary> = {}): ScriptVersionSummary {
  return {
    id: VERSION_ID,
    exercise_id: EXERCISE_ID,
    revision: 1,
    status: "draft",
    origin: "ai",
    created_at: "2026-11-08T03:00:00Z",
    ...overrides,
  };
}

export function exercise(overrides: Partial<Exercise> = {}): Exercise {
  return {
    id: EXERCISE_ID,
    code: "b22-ham-tinh-tong",
    title: "Hàm tính tổng SUM",
    sheet_name: "Bài 01",
    prompt_text: "Tính tổng tiền mỗi ngày.",
    textbook_ids: [],
    warnings: [],
    ...overrides,
  };
}

// Vitest chạy tại apps/web; import.meta.url trong môi trường jsdom không phải file://
const FIXTURES = resolve(process.cwd(), "../../packages/excel_core/tests/fixtures");

/** File .xlsx tự soạn của excel_core (số liệu giả), dạng File như người dùng chọn trên trình duyệt. */
export function fixtureXlsx(folder: string, name: "de.xlsx" | "dap-an.xlsx"): File {
  const bytes = readFileSync(resolve(FIXTURES, folder, name));
  return new File([bytes], name, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}
