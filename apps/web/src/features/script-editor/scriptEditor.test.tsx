import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import b22 from "@schemas/tutor-script/v1/examples/b22-ham-tinh-tong.json";
import type { Script, ScriptVersion, SelfCheckReport } from "@/api/types";
import { installFakeApi, problem, type FakeApi } from "@/test/fakeApi";
import { exercise, EXERCISE_ID, VERSION_ID } from "@/test/fixtures";
import { renderApp, signIn } from "@/test/renderApp";

const NEW_VERSION_ID = "88888888-8888-4888-8888-888888888888";
const SCRIPT = b22 as unknown as Script;

const REPORT: SelfCheckReport = {
  schema_ok: true,
  cross_reference_errors: [],
  checks: [
    {
      step_id: "s1_first_total",
      check_index: 0,
      type: "is_formula",
      passes_on_solution: true,
      fails_on_starter: true,
      code_on_starter: "empty",
    },
    {
      step_id: "s1_first_total",
      check_index: 1,
      type: "formula_uses_function",
      passes_on_solution: false,
      fails_on_starter: true,
      code_on_starter: "empty",
    },
  ],
  diff_coverage: 1,
  uncovered_ranges: [],
  hint_text_issues: [
    { step_id: "s2_copy_down", text: "F10", issue: "có địa chỉ ô trong chữ (đã có overlay chỉ)" },
  ],
  errors: [
    "bước s1_first_total, điều kiện 1 (formula_uses_function): không đạt trên đáp án (missing_function: …)",
  ],
  warnings: [],
};

function version(overrides: Partial<ScriptVersion> = {}): ScriptVersion {
  return {
    id: VERSION_ID,
    exercise_id: EXERCISE_ID,
    revision: 1,
    status: "draft",
    origin: "ai",
    created_at: "2026-11-08T03:00:00Z",
    content: SCRIPT,
    self_check_report: REPORT,
    ...overrides,
  };
}

const PREVIEW = {
  sheet: "Bài 01",
  sheet_names: ["Bài 01"],
  range: "A1:F20",
  rows: 20,
  cols: 6,
  truncated: false,
  cells: [
    { address: "C8", text: "Tiền Bún", bold: true, italic: false, number: false, wrap: false },
    { address: "C9", text: "120.000", bold: false, italic: false, number: true, wrap: false },
  ],
  merged: ["A1:F1"],
  col_widths: {},
  row_heights: {},
  hidden_rows: [],
  hidden_cols: [],
};

function setup(): FakeApi {
  const api = installFakeApi();
  api.on("GET", "/scripts/:id", (_req, params) =>
    params.id === NEW_VERSION_ID
      ? version({ id: NEW_VERSION_ID, revision: 2, origin: "ai_edited" })
      : version(),
  );
  api.on("GET", "/exercises/:id", exercise());
  api.on("GET", "/exercises/:id/sheet-preview", PREVIEW);
  api.on("GET", "/textbooks", []);
  signIn();
  return api;
}

async function openStep(user: ReturnType<typeof userEvent.setup>, name: RegExp) {
  await user.click(await screen.findByRole("button", { name }));
}

test("tổng quan: kiểm lược đồ, lỗi tự kiểm chặn gửi duyệt, mục lục đánh dấu bước có vấn đề", async () => {
  setup();
  renderApp(`/scripts/${VERSION_ID}`);

  // Lần đầu mở: tải riêng trang trình sửa (lazy) và dựng bộ kiểm lược đồ
  expect(
    await screen.findByRole("heading", { name: /Kịch bản bản 1/ }, { timeout: 5000 }),
  ).toBeInTheDocument();
  expect(screen.getByText("Bản đang sửa khớp lược đồ kịch bản v1.")).toBeInTheDocument();
  expect(screen.getByText("Lỗi chặn gửi duyệt")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /1\. Tổng tiền ngày đầu tiên/ })).toHaveTextContent("1");
  expect(screen.getByRole("button", { name: "Lưu thành bản mới" })).toBeDisabled();
  // Lưới mô phỏng hiện file đề
  expect(await screen.findByText("Tiền Bún")).toBeInTheDocument();
});

test("sửa bước: lỗi lược đồ hiện ngay và chặn lưu; lưu thành bản mới rồi mở bản đó", async () => {
  const api = setup();
  api.on("POST", "/exercises/:id/scripts", (_req, _params, body) => {
    const { content } = body as { content: Script };
    return version({ id: NEW_VERSION_ID, revision: 2, origin: "ai_edited", content });
  });
  const { router } = renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await openStep(user, /1\. Tổng tiền ngày đầu tiên/);
  const title = screen.getByLabelText("Tên bước");
  await user.clear(title);
  expect(await screen.findByText("Không được để trống.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Lưu thành bản mới" })).toBeDisabled();

  await user.type(title, "Tính tổng tiền ngày 1");
  await user.click(screen.getByRole("button", { name: "Thêm thao tác" }));
  await user.type(screen.getByLabelText("Thao tác 3"), "Bấm Enter.");
  await user.click(screen.getByRole("button", { name: "Lưu thành bản mới" }));

  await waitFor(() => expect(router.state.location.pathname).toBe(`/scripts/${NEW_VERSION_ID}`));
  const call = api.callsTo("POST", `/exercises/${EXERCISE_ID}/scripts`)[0];
  const sent = call?.body as { parent_version_id: string; content: Script };
  expect(sent.parent_version_id).toBe(VERSION_ID);
  expect(sent.content.steps[0]?.title).toBe("Tính tổng tiền ngày 1");
  expect(sent.content.steps[0]?.hints[3].actions.at(-1)).toBe("Bấm Enter.");
  expect(await screen.findByText(/Đã lưu thành bản 2/)).toBeInTheDocument();
});

test("Backend từ chối khi lưu thì hiện lỗi theo vị trí dễ đọc", async () => {
  const api = setup();
  api.on(
    "POST",
    "/exercises/:id/scripts",
    problem(422, "script_invalid", "Kịch bản không hợp lệ", [
      { path: "/completion/criteria/0/step_ids/0", message: "bước không tồn tại" },
    ]),
  );
  renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await openStep(user, /Màn hình hoàn thành/);
  await user.type(screen.getByLabelText("Lời chúc khi xong bài"), " Giỏi lắm!");
  await user.click(screen.getByRole("button", { name: "Lưu thành bản mới" }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Kịch bản không hợp lệ");
  expect(alert).toHaveTextContent("Màn hình hoàn thành › Tiêu chí 1 › Các bước");
});

test("bấm Xem ở một điều kiện thì khoanh vùng đó trên lưới; tự kiểm hiện theo từng điều kiện", async () => {
  setup();
  const { container } = renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await openStep(user, /1\. Tổng tiền ngày đầu tiên/);
  const checks = screen.getByRole("heading", { name: "Điều kiện kiểm chứng" }).closest("section");
  expect(checks).not.toBeNull();
  const rows = within(checks as HTMLElement).getAllByRole("row");
  expect(rows[2]).toHaveTextContent("Công thức ở F9 dùng hàm SUM");
  expect(rows[2]).toHaveTextContent("✗ đáp án");
  await user.click(within(rows[2] as HTMLElement).getByRole("button", { name: "Xem" }));

  await waitFor(() => expect(container.querySelector(".sheet__mark--focus")).not.toBeNull());
  // Vùng học viên làm (F9) và vùng nguồn (C9:E9) của bước cũng được khoanh
  expect(container.querySelectorAll(".sheet__mark--target")).toHaveLength(1);
  expect(container.querySelectorAll(".sheet__mark--source")).toHaveLength(1);
});

test("gợi ý có địa chỉ ô thì cảnh báo ở đúng bước; rời trang khi chưa lưu thì hỏi lại", async () => {
  setup();
  const { router } = renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await openStep(user, /2\. Sao chép công thức/);
  expect(screen.getByText(/“F10”: có địa chỉ ô trong chữ/)).toBeInTheDocument();
  await user.type(screen.getByLabelText("Cấp 1 — Định hướng"), " Thêm.");
  await user.click(screen.getByRole("link", { name: /Hàm tính tổng SUM/ }));

  const dialog = await screen.findByRole("dialog", { name: "Rời trang khi chưa lưu?" });
  await user.click(within(dialog).getByRole("button", { name: "Hủy" }));
  expect(router.state.location.pathname).toBe(`/scripts/${VERSION_ID}`);
});

test("chấm thử bằng file Excel: hiện bước học viên đang làm, điều kiện chưa đạt và lời gia sư", async () => {
  const api = setup();
  api.on("POST", "/scripts/:id/try-out", {
    current_step_id: "s1_first_total",
    global_checks: [{ index: 0, type: "data_unchanged", status: "passed", cells: [], detail: "" }],
    steps: [
      {
        step_id: "s1_first_total",
        title: "Tổng tiền ngày đầu tiên",
        status: "failed",
        checks: [
          { index: 0, type: "is_formula", status: "passed", cells: [], detail: "" },
          {
            index: 1,
            type: "formula_uses_function",
            status: "failed",
            code: "used_operator_instead",
            cells: ["F9"],
            detail: "",
          },
        ],
        feedback: [{ code: "used_operator_instead", message: "Bài yêu cầu dùng hàm SUM." }],
      },
      { step_id: "s2_copy_down", title: "Sao chép", status: "failed", checks: [], feedback: [] },
    ],
  });
  renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await user.click(
    await screen.findByRole("button", { name: "Chấm thử bằng file Excel" }, { timeout: 5000 }),
  );
  const dialog = screen.getByRole("dialog", { name: "Chấm thử bằng file Excel" });
  await user.upload(within(dialog).getByLabelText("File bài làm (.xlsx)"), new File(["PK"], "bai-lam.xlsx"));
  await user.click(within(dialog).getByRole("button", { name: "Chấm" }));

  expect(
    await within(dialog).findByText("Học viên đang ở bước 1: Tổng tiền ngày đầu tiên"),
  ).toBeInTheDocument();
  expect(within(dialog).getByText(/Công thức ở F9 dùng hàm SUM/)).toHaveTextContent(
    "used_operator_instead ở F9",
  );
  expect(within(dialog).getByText("Gia sư nói: “Bài yêu cầu dùng hàm SUM.”")).toBeInTheDocument();
  expect(api.callsTo("POST", `/scripts/${VERSION_ID}/try-out`)).toHaveLength(1);
});

test("chạy thử trên Excel: hiện lệnh mở ứng dụng gia sư đúng bản kịch bản", async () => {
  setup();
  renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Chạy thử trên Excel" }, { timeout: 5000 }));

  const dialog = screen.getByRole("dialog", { name: "Chạy thử trên Excel" });
  expect(
    within(dialog).getByText(new RegExp(`-m tutor_desktop --version ${VERSION_ID}$`)),
  ).toBeInTheDocument();
});
