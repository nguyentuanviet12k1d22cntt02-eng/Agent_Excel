/**
 * Kiểm kịch bản theo lược đồ v1 ngay trên trình duyệt (cùng file schemas/tutor-script/v1 với Backend và
 * Desktop), đổi lỗi của Ajv thành câu tiếng Việt kèm vị trí dễ đọc (luoc-do-kich-ban.md, mục "Điểm chưa
 * chắc chắn" 2). Backend vẫn kiểm lại khi lưu: Web kiểm trước để giảng viên sửa ngay khi gõ.
 */
import type { ErrorObject } from "ajv";
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import schema from "@schemas/tutor-script/v1/tutor-script.schema.json";
import type { Step } from "@/api/types";

import { describePath } from "./scriptPaths";

export interface ScriptIssue {
  path: string; // JSON pointer, ví dụ "/steps/0/hints/3/actions/1"
  where: string; // "Bước 1 “Nhập số lượng” › Gợi ý cấp 4 › Thao tác 2"
  message: string;
}

const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
const validate = ajv.compile(schema);

type Defs = Record<string, { description?: string } | undefined>;
const DEFS = schema.$defs as Defs;

/** Mã lỗi của từng loại điều kiện, lấy từ câu "Mã lỗi: …" trong mô tả của lược đồ (danh sách đóng). */
export function codesForCheckType(type: string): string[] {
  const match = /Mã lỗi: ([^.]+)\./.exec(DEFS[`check_${type}`]?.description ?? "");
  return match?.[1] ? match[1].split(",").map((code) => code.trim()) : [];
}

/** Mã lỗi các điều kiện của bước có thể trả về (để chọn mã cho phản hồi, mã phản hồi ngay). */
export function stepCodes(step: Step): string[] {
  return [...new Set(step.checks.flatMap((c) => codesForCheckType(c.type)))];
}

const PATTERN_MESSAGES: Record<string, string> = {
  range: "Địa chỉ vùng không hợp lệ (ví dụ F10:F14 hoặc H10, không ghi tên sheet, không ghép nhiều vùng).",
  print_area: "Địa chỉ vùng không hợp lệ (ví dụ A1:H20).",
  data_range: "Địa chỉ vùng không hợp lệ (ví dụ A1:H20).",
  id: "Mã chỉ gồm chữ thường không dấu, số, gạch dưới và bắt đầu bằng chữ (ví dụ nhap_so_luong).",
  code: "Mã lỗi chỉ gồm chữ thường không dấu, số, gạch dưới.",
  color: "Màu viết dạng #RRGGBB, ví dụ #FFFF00.",
  rows: "Dải dòng viết dạng 5:7.",
  cols: "Dải cột viết dạng C:D.",
  control: "Mã nút Ribbon không hợp lệ (ví dụ CommaStyle).",
  tab: "Mã thẻ Ribbon không hợp lệ (ví dụ TabHome).",
  r1c1: "Công thức mẫu phải bắt đầu bằng dấu =.",
};

function lastNamedSegment(path: string): string {
  const parts = path.split("/").filter((p) => p && !/^\d+$/.test(p));
  return parts.at(-1) ?? "";
}

function limit(error: ErrorObject): number {
  return (error.params as { limit?: number }).limit ?? 0;
}

function messageFor(error: ErrorObject): string {
  const params = error.params as Record<string, unknown>;
  switch (error.keyword) {
    case "required":
      return `Thiếu mục bắt buộc “${String(params.missingProperty)}”.`;
    case "minLength":
      return limit(error) <= 1 ? "Không được để trống." : `Cần ít nhất ${limit(error)} ký tự.`;
    case "maxLength":
      return `Dài quá: tối đa ${limit(error)} ký tự.`;
    case "pattern": {
      const key = lastNamedSegment(error.instancePath);
      const parent = error.instancePath.split("/").at(-2) ?? "";
      if (key === "step_ids" || key === "reference_ids") return PATTERN_MESSAGES.id ?? "";
      if (key === "immediate_codes") return PATTERN_MESSAGES.code ?? "";
      if (key === "functions") return "Tên hàm viết hoa, không dấu, ví dụ SUM.";
      return PATTERN_MESSAGES[key] ?? PATTERN_MESSAGES[parent] ?? "Sai định dạng.";
    }
    case "minimum":
      return `Phải từ ${limit(error)} trở lên.`;
    case "exclusiveMinimum":
      return `Phải lớn hơn ${limit(error)}.`;
    case "maximum":
      return `Tối đa ${limit(error)}.`;
    case "minItems":
      return limit(error) <= 1 ? "Cần ít nhất một mục." : `Cần ít nhất ${limit(error)} mục.`;
    case "maxItems":
      return `Tối đa ${limit(error)} mục.`;
    case "uniqueItems":
      return "Có mục bị trùng.";
    case "enum":
    case "const":
      return "Giá trị không nằm trong danh sách cho phép.";
    case "type":
      return "Sai kiểu dữ liệu.";
    case "additionalProperties":
      return `Có mục không thuộc lược đồ: “${String(params.additionalProperty)}”.`;
    case "unevaluatedProperties":
      return `Có mục không thuộc lược đồ: “${String(params.unevaluatedProperty)}”.`;
    case "minProperties":
      return "Cần ghi thêm ít nhất một thuộc tính để kiểm.";
    case "format":
      return "Sai định dạng ngày giờ.";
    default:
      return "Không khớp lược đồ kịch bản.";
  }
}

const CHECK_PATH = /^(\/steps\/\d+\/checks\/\d+|\/global_checks\/\d+)/;
const COMBINATORS = new Set(["oneOf", "anyOf", "allOf", "if"]);
const GLOBAL_CHECK_TYPES = new Set(["data_unchanged", "is_formula"]);

function nodeAt(script: unknown, pointer: string): unknown {
  let node: unknown = script;
  for (const part of pointer.split("/").filter(Boolean)) {
    node = typeof node === "object" && node !== null ? (node as Record<string, unknown>)[part] : undefined;
  }
  return node;
}

function subschemaErrors(def: string, value: unknown, prefix: string): ErrorObject[] {
  const check = ajv.getSchema(`${schema.$id}#/$defs/${def}`);
  if (!check || check(value)) return [];
  return (check.errors ?? []).map((e) => ({ ...e, instancePath: prefix + e.instancePath }));
}

/**
 * Một điều kiện sai thì Ajv báo lỗi của cả 25 nhánh oneOf, và lỗi đi qua $ref mất dấu nhánh. Nên bỏ hết lỗi
 * nằm trong điều kiện rồi kiểm lại điều kiện đó theo đúng định nghĩa của loại (`type`) của nó.
 */
function checkErrors(script: unknown, checkPath: string): ErrorObject[] {
  const check = nodeAt(script, checkPath);
  const type = (check as { type?: unknown } | undefined)?.type;
  const isGlobal = checkPath.startsWith("/global_checks/");
  if (typeof type !== "string" || !DEFS[`check_${type}`] || (isGlobal && !GLOBAL_CHECK_TYPES.has(type))) {
    return [
      { instancePath: `${checkPath}/type`, keyword: "enum", params: {}, schemaPath: "" } as ErrorObject,
    ];
  }
  return [
    ...subschemaErrors("check_common", check, checkPath),
    ...subschemaErrors(`check_${type}`, check, checkPath),
  ];
}

/** Trường lẻ có oneOf (ví dụ màu nền: #RRGGBB hoặc "any") báo lỗi của mọi nhánh: chỉ giữ một câu. */
function collapseCombinators(errors: ErrorObject[]): ErrorObject[] {
  const combinedAt = new Set(errors.filter((e) => COMBINATORS.has(e.keyword)).map((e) => e.instancePath));
  const seen = new Set<string>();
  return errors.filter((e) => {
    if (COMBINATORS.has(e.keyword)) return false;
    const key = combinedAt.has(e.instancePath) ? e.instancePath : `${e.instancePath}|${messageFor(e)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function relevantErrors(errors: ErrorObject[], script: unknown): ErrorObject[] {
  const checkPaths = new Set<string>();
  const others: ErrorObject[] = [];
  for (const error of errors) {
    const checkPath = CHECK_PATH.exec(error.instancePath)?.[1];
    if (checkPath) checkPaths.add(checkPath);
    else others.push(error);
  }
  const fromChecks = [...checkPaths].flatMap((path) => checkErrors(script, path));
  return collapseCombinators([...others, ...fromChecks]);
}

export { describePath };

export function validateScript(script: unknown): ScriptIssue[] {
  if (validate(script)) return [];
  return relevantErrors(validate.errors ?? [], script)
    .map((error) => ({
      path: error.instancePath,
      where: describePath(error.instancePath, script),
      message: messageFor(error),
    }))
    .sort((a, b) => a.path.localeCompare(b.path, "en", { numeric: true }));
}

/** Lỗi ở đúng vị trí hoặc bên trong vị trí đó. */
export function issuesUnder(issues: ScriptIssue[], pointer: string): ScriptIssue[] {
  return issues.filter((i) => i.path === pointer || i.path.startsWith(`${pointer}/`));
}
