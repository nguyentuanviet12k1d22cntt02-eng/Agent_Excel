/** Diễn đạt điều kiện kiểm chứng thành câu tiếng Việt cho giảng viên đọc khi duyệt (danh-muc-dieu-kien.md). */

type Params = Record<string, unknown>;

export const CHECK_TYPE_LABELS: Record<string, string> = {
  value_equals: "Giá trị đúng",
  value_type: "Kiểu dữ liệu",
  data_unchanged: "Giữ nguyên dữ liệu",
  is_formula: "Là công thức",
  formula_uses_function: "Dùng hàm",
  formula_consistent: "Sao chép công thức",
  formula_matches_r1c1: "Công thức đúng mẫu",
  number_format: "Định dạng số",
  alignment: "Căn lề",
  font: "Phông chữ",
  fill: "Màu nền",
  border: "Viền",
  merged: "Gộp ô",
  row_col_hidden: "Ẩn/hiện dòng, cột",
  row_col_size: "Kích thước dòng, cột",
  layout_matches: "Bố cục bảng",
  sheet_exists: "Có trang tính",
  autofilter: "Bộ lọc",
  visible_rows: "Dòng đang hiện",
  sorted_by: "Sắp xếp",
  page_setup: "Trang in",
  header_footer: "Đầu/cuối trang",
  chart: "Biểu đồ",
  printed_to_pdf: "In ra PDF",
  observation_only: "Học viên tự xác nhận",
};

const KINDS: Record<string, string> = { number: "số", date: "ngày", text: "chữ", logical: "đúng/sai" };
const CATEGORIES: Record<string, string> = {
  general: "General",
  number: "Number",
  currency: "Currency",
  accounting: "Accounting",
  percent: "Percentage",
  date: "Date",
  time: "Time",
  text: "Text",
  scientific: "Scientific",
  fraction: "Fraction",
};
const HORIZONTAL: Record<string, string> = {
  general: "General",
  left: "trái",
  center: "giữa",
  right: "phải",
  justify: "đều hai bên",
  center_across: "giữa vùng chọn",
};
const VERTICAL: Record<string, string> = { top: "trên", center: "giữa", bottom: "dưới", justify: "đều" };
const SIDES: Record<string, string> = {
  outline: "khung ngoài",
  inside: "đường trong",
  top: "trên",
  bottom: "dưới",
  left: "trái",
  right: "phải",
  inside_horizontal: "ngang bên trong",
  inside_vertical: "dọc bên trong",
};
const POSITIONS: Record<string, string> = {
  header_left: "Đầu trang bên trái",
  header_center: "Đầu trang ở giữa",
  header_right: "Đầu trang bên phải",
  footer_left: "Cuối trang bên trái",
  footer_center: "Cuối trang ở giữa",
  footer_right: "Cuối trang bên phải",
};

function str(p: Params, key: string): string {
  const value = p[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function list(p: Params, key: string, names: Record<string, string> = {}): string {
  const value = p[key];
  return Array.isArray(value) ? value.map((v) => names[String(v)] ?? String(v)).join(", ") : "";
}

function yesNo(p: Params, key: string, yes: string, no: string): string | null {
  return typeof p[key] === "boolean" ? (p[key] ? yes : no) : null;
}

function expected(p: Params): string {
  const exp = p.expected as Params | undefined;
  if (!exp || exp.from === "solution") return "bằng file đáp án";
  if (exp.from === "range") return `bằng vùng ${str(exp, "range")}`;
  return `bằng ${JSON.stringify(exp.value)}`;
}

function joinParts(parts: (string | null | false | undefined)[]): string {
  return parts.filter(Boolean).join(", ");
}

type Describe = (p: Params, where: string) => string;

const DESCRIBE: Record<string, Describe> = {
  value_equals: (p, w) =>
    `Giá trị ở ${w} ${expected(p)}${p.tolerance ? ` (sai số ${str(p, "tolerance")})` : ""}`,
  value_type: (p, w) => `Mọi ô ở ${w} là ${KINDS[str(p, "kind")] ?? str(p, "kind")}`,
  data_unchanged: (_p, w) => `Dữ liệu và công thức ở ${w} giữ nguyên như file đề`,
  is_formula: (_p, w) => `Mọi ô ở ${w} là công thức`,
  formula_uses_function: (p, w) =>
    `Công thức ở ${w} dùng hàm ${list(p, "functions")}${p.forbid_operator_only === false ? "" : " (không cộng từng ô lẻ)"}`,
  formula_consistent: (_p, w) => `Công thức ở ${w} được sao chép nhất quán`,
  formula_matches_r1c1: (p, w) => `Công thức ở ${w} đúng mẫu ${str(p, "r1c1")}`,
  number_format: (p, w) =>
    `Định dạng số ở ${w}: ${joinParts([
      list(p, "categories", CATEGORIES),
      p.decimals !== undefined && `${str(p, "decimals")} số lẻ`,
      yesNo(p, "thousands_separator", "có phân cách nghìn", "không phân cách nghìn"),
      p.date_pattern !== undefined && `mẫu ngày ${str(p, "date_pattern")}`,
    ])}`,
  alignment: (p, w) =>
    `Căn lề ở ${w}: ${joinParts([
      p.horizontal !== undefined && `ngang ${list(p, "horizontal", HORIZONTAL)}`,
      p.vertical !== undefined && `dọc ${list(p, "vertical", VERTICAL)}`,
      yesNo(p, "wrap_text", "xuống dòng trong ô", "không xuống dòng"),
    ])}`,
  font: (p, w) =>
    `Phông chữ ở ${w}: ${joinParts([
      yesNo(p, "bold", "đậm", "không đậm"),
      yesNo(p, "italic", "nghiêng", "không nghiêng"),
      yesNo(p, "underline", "gạch chân", "không gạch chân"),
      p.size !== undefined && `cỡ ${str(p, "size")}`,
      p.name !== undefined && str(p, "name"),
      p.color !== undefined && `màu ${str(p, "color")}`,
    ])}`,
  fill: (p, w) => `Tô nền ${w} ${p.color === "any" ? "màu bất kỳ" : `màu ${str(p, "color")}`}`,
  border: (p, w) =>
    `Viền ${w}: ${list(p, "sides", SIDES)}${p.style && p.style !== "any" ? `, nét ${str(p, "style")}` : ""}`,
  merged: (_p, w) => `Gộp ${w} thành một ô`,
  row_col_hidden: (p) =>
    `${p.rows ? `Dòng ${str(p, "rows")}` : `Cột ${str(p, "cols")}`} ${p.hidden ? "được ẩn" : "đang hiện"}`,
  row_col_size: (p) => {
    const target = p.rows ? `Chiều cao dòng ${str(p, "rows")}` : `Độ rộng cột ${str(p, "cols")}`;
    if (p.autofit) return `${target} vừa khít nội dung`;
    if (p.same_as) return `${target} bằng ${p.rows ? "dòng" : "cột"} ${str(p, "same_as")}`;
    return `${target} bằng ${str(p, "equals")}`;
  },
  layout_matches: (p, w) => `Bố cục bảng ${w} khớp đáp án (cột khóa “${str(p, "key_column")}”)`,
  sheet_exists: (p) => `Có trang tính tên khớp “${str(p, "name_pattern")}”`,
  autofilter: (p, w) =>
    `Bật bộ lọc ở ${w}${p.column ? `, lọc cột “${str(p, "column")}”` : ""}${
      Array.isArray(p.criteria) ? ` theo ${list(p, "criteria")}` : ""
    }`,
  visible_rows: (p, w) => `Các dòng đang hiện trong ${w} ${expected(p)}`,
  sorted_by: (p, w) =>
    `${w} sắp xếp theo “${str(p, "key_column")}” ${p.order === "desc" ? "giảm dần" : "tăng dần"}`,
  page_setup: (p) =>
    `Trang in: ${joinParts([
      p.orientation !== undefined && (p.orientation === "landscape" ? "khổ ngang" : "khổ dọc"),
      p.paper_size !== undefined && `giấy ${str(p, "paper_size")}`,
      p.margins_cm !== undefined && "lề theo yêu cầu",
      p.fit_to_pages_wide !== undefined && `vừa ${str(p, "fit_to_pages_wide")} trang ngang`,
      p.fit_to_pages_tall !== undefined && `vừa ${str(p, "fit_to_pages_tall")} trang dọc`,
      yesNo(p, "center_horizontally", "căn giữa ngang", "không căn giữa"),
      p.print_area !== undefined && `vùng in ${str(p, "print_area")}`,
    ])}`,
  header_footer: (p) => `${POSITIONS[str(p, "position")] ?? str(p, "position")} có “${str(p, "contains")}”`,
  chart: (p) =>
    `Có biểu đồ${p.chart_types ? ` loại ${list(p, "chart_types")}` : ""}${
      p.data_range ? `, dữ liệu ${str(p, "data_range")}` : ""
    }${p.has_title ? ", có tiêu đề" : ""}`,
  printed_to_pdf: () => "Học viên đã in ra PDF",
  observation_only: (p) => `Học viên tự bấm “Đã xong”: ${str(p, "confirm_text")}`,
};

/** Câu mô tả điều kiện, ví dụ "Công thức ở H10:H14 dùng hàm SUM (không cộng từng ô lẻ)". */
export function describeCheck(check: object): string {
  const p = check as Params;
  const type = str(p, "type");
  const sheet = str(p, "sheet");
  const where = `${sheet ? `${sheet}!` : ""}${str(p, "range") || "—"}`;
  const describe = DESCRIBE[type];
  return describe ? describe(p, where) : `Điều kiện ${type}`;
}

export function checkTypeLabel(type: string): string {
  return CHECK_TYPE_LABELS[type] ?? type;
}

/** Vùng của điều kiện để khoanh trên lưới (điều kiện không theo vùng thì không có). */
export function checkRange(check: object): { range: string; sheet?: string } | null {
  const p = check as Params;
  const range = str(p, "range") || str(p, "data_range") || str(p, "print_area");
  return range ? { range, sheet: str(p, "sheet") || undefined } : null;
}
