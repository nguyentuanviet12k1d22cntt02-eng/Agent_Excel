import b09 from "@schemas/tutor-script/v1/examples/b09-du-lieu-dang-so.json";
import b22 from "@schemas/tutor-script/v1/examples/b22-ham-tinh-tong.json";
import type { Script } from "@/api/types";
import { colIndex, colLetter, parseRange } from "@/lib/a1";

import { checkRange, describeCheck } from "./checkText";
import { codesForCheckType, describePath, stepCodes, validateScript } from "./scriptSchema";
import { overlayRects, type SheetPreview } from "./sheetLayout";
import { move, withoutStep } from "./useScriptDraft";

const clone = <T>(value: T): T => structuredClone(value);

test("kịch bản mẫu viết tay hợp lệ theo lược đồ v1 (cùng file Backend dùng)", () => {
  expect(validateScript(b09)).toEqual([]);
  expect(validateScript(b22)).toEqual([]);
});

test("lỗi trong điều kiện chỉ báo theo đúng loại điều kiện, câu tiếng Việt, vị trí dễ đọc", () => {
  const script = clone(b09) as unknown as Script;
  const check = script.steps[1]?.checks[0] as unknown as Record<string, unknown>;
  check.range = "F10:F14,G1";
  (script.global_checks?.[0] as unknown as Record<string, unknown>).type = "font";
  script.steps[2]!.hints[3].actions = [];

  const messages = validateScript(script).map((i) => `${i.where}: ${i.message}`);

  expect(messages).toEqual([
    "Điều kiện toàn bài 1 › Loại: Giá trị không nằm trong danh sách cho phép.",
    "Bước 2 “Định dạng Số lượng” › Điều kiện 1 › Vùng: Địa chỉ vùng không hợp lệ (ví dụ F10:F14 hoặc H10, không ghi tên sheet, không ghép nhiều vùng).",
    "Bước 3 “Nhập và định dạng Đơn giá” › Gợi ý cấp 4 › Các thao tác: Cần ít nhất một mục.",
  ]);
});

test("thiếu trường bắt buộc, sai mã bước trong tiêu chí", () => {
  const script = clone(b22) as unknown as Record<string, unknown> & Script;
  delete (script.steps[0] as Partial<Script["steps"][number]>).task;
  script.completion!.criteria![0]!.step_ids = ["Bước 1"];

  const issues = validateScript(script);

  expect(issues.map((i) => i.message)).toEqual([
    "Mã chỉ gồm chữ thường không dấu, số, gạch dưới và bắt đầu bằng chữ (ví dụ nhap_so_luong).",
    "Thiếu mục bắt buộc “task”.",
  ]);
  expect(describePath("/steps/0/hints/3/actions/1", b22)).toBe(
    "Bước 1 “Tổng tiền ngày đầu tiên” › Gợi ý cấp 4 › Thao tác 2",
  );
});

test("mã lỗi lấy từ lược đồ: danh sách đóng cho phản hồi theo lỗi", () => {
  expect(codesForCheckType("value_equals")).toEqual(["stored_as_text", "wrong_value", "empty"]);
  expect(codesForCheckType("khong_co")).toEqual([]);
  expect(stepCodes((b22 as unknown as Script).steps[0]!)).toContain("used_operator_instead");
});

test("câu mô tả điều kiện cho giảng viên đọc khi duyệt", () => {
  expect(describeCheck({ type: "formula_uses_function", range: "F9", functions: ["SUM"] })).toBe(
    "Công thức ở F9 dùng hàm SUM (không cộng từng ô lẻ)",
  );
  expect(
    describeCheck({
      type: "number_format",
      range: "G10:G14",
      categories: ["number"],
      decimals: 2,
      thousands_separator: true,
    }),
  ).toBe("Định dạng số ở G10:G14: Number, 2 số lẻ, có phân cách nghìn");
  expect(describeCheck({ type: "value_equals", range: "H10", expected: { from: "solution" } })).toBe(
    "Giá trị ở H10 bằng file đáp án",
  );
  expect(describeCheck({ type: "sorted_by", range: "A3:F20", key_column: "Lương", order: "desc" })).toBe(
    "A3:F20 sắp xếp theo “Lương” giảm dần",
  );
  expect(checkRange({ type: "chart", data_range: "A1:B5" })).toEqual({ range: "A1:B5", sheet: undefined });
  expect(checkRange({ type: "printed_to_pdf" })).toBeNull();
});

test("địa chỉ ô A1", () => {
  expect(parseRange("$F$10:F14")).toEqual({ c1: 6, r1: 10, c2: 6, r2: 14 });
  expect(parseRange("H10")).toEqual({ c1: 8, r1: 10, c2: 8, r2: 10 });
  expect(parseRange("5:7")).toBeNull();
  expect(parseRange("F10:F14,G1")).toBeNull();
  expect([colIndex("AA"), colLetter(27), colLetter(702), colLetter(703)]).toEqual([27, "AA", "ZZ", "AAA"]);
});

test("khung tô tính từ độ rộng cột, chiều cao dòng; vùng vượt lưới thì cắt", () => {
  const preview: SheetPreview = {
    sheet: "S",
    sheet_names: ["S"],
    range: "A1:C3",
    rows: 3,
    cols: 3,
    truncated: false,
    cells: [],
    merged: [],
    col_widths: { B: 20 },
    row_heights: { "2": 30 },
    hidden_rows: [],
    hidden_cols: [],
  };
  const [rect] = overlayRects(preview, [{ box: { c1: 2, r1: 2, c2: 5, r2: 9 }, kind: "target" }]);
  // A rộng mặc định 8,43 ký tự = 64 px; B 20 ký tự = 145 px; dòng 1 = 20 px; dòng 2 = 40 px
  expect(rect).toMatchObject({ left: 36 + 64, top: 22 + 20, width: 145 + 64, height: 40 + 20 });
  expect(overlayRects(preview, [{ box: { c1: 9, r1: 1, c2: 9, r2: 1 }, kind: "focus" }])).toEqual([]);
});

test("xóa bước thì gỡ bước đó khỏi tiêu chí hoàn thành; đổi thứ tự", () => {
  const script = clone(b22) as unknown as Script;
  const after = withoutStep(script, 2);
  expect(after.steps.map((s) => s.id)).toEqual(["s1_first_total", "s2_copy_down"]);
  expect(after.completion?.criteria?.map((c) => c.step_ids)).toEqual([
    ["s1_first_total", "s2_copy_down"],
    ["s2_copy_down"],
  ]);
  expect(move(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
  expect(move(["a", "b"], 1, 1)).toEqual(["a", "b"]);
});
