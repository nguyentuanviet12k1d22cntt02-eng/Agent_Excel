/**
 * Tên ngắn cho các kiểu sinh từ docs/thiet-ke/openapi.yaml (file schema.d.ts, chạy `npm run gen:api`).
 * Không tự gõ lại kiểu dữ liệu API: sửa đặc tả rồi sinh lại.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Role = Schemas["Role"];
export type User = Schemas["User"];
export type UserCreate = Schemas["UserCreate"];
export type TokenPair = Schemas["TokenPair"];
export type Problem = Schemas["Problem"];
export type ClassInfo = Schemas["Class"];
export type StudyGroup = Schemas["StudyGroup"];
export type Textbook = Schemas["Textbook"];
export type Passage = Schemas["Passage"];
export type Exercise = Schemas["Exercise"];
export type GenerationJob = Schemas["GenerationJob"];
export type ScriptVersionSummary = Schemas["ScriptVersionSummary"];
export type ScriptVersion = Schemas["ScriptVersion"];
export type ScriptStatus = ScriptVersionSummary["status"];
export type ScriptOrigin = ScriptVersionSummary["origin"];
export type SelfCheckReport = Schemas["SelfCheckReport"];

// Kịch bản (schemas/tutor-script/v1)
export type Script = Schemas["TutorScript"];
export type Step = Schemas["step"];
export type Check = Schemas["check"];
export type GlobalCheck = Schemas["global_check"];
export type CellTarget = Schemas["cell_target"];
export type UiTarget = Schemas["ui_target"];
export type Feedback = Schemas["feedback"];
export type Reference = Schemas["reference"];
export type StepSignals = Schemas["step_signals"];
export type Skill = NonNullable<Schemas["exercise"]["skills"]>[number];
