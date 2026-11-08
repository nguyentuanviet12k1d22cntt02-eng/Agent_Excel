import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import b22 from "@schemas/tutor-script/v1/examples/b22-ham-tinh-tong.json";
import type { Script, ScriptStatus, ScriptVersion, ScriptVersionSummary } from "@/api/types";
import { installFakeApi, problem, type FakeApi } from "@/test/fakeApi";
import { exercise, EXERCISE_ID, VERSION_ID, versionSummary } from "@/test/fixtures";
import { renderApp, signIn } from "@/test/renderApp";

import { changedSteps, diffScripts } from "./diffScripts";

const SCRIPT = b22 as unknown as Script;
const EDITED_ID = "99999999-9999-4999-8999-999999999999";

function editedScript(): Script {
  const script = structuredClone(SCRIPT);
  script.revision = 2;
  script.steps[0]!.title = "Tổng tiền ngày 1";
  script.steps[1]!.hints[0].text = "Câu định hướng mới.";
  return script;
}

/** Backend giả có vòng đời thật: nháp → chờ duyệt → đã duyệt → phát hành. */
function setupLifecycle(): { api: FakeApi; state: { status: ScriptStatus; note?: string } } {
  const api = installFakeApi();
  const state: { status: ScriptStatus; note?: string } = { status: "draft" };
  const summary = (): ScriptVersionSummary =>
    versionSummary({
      status: state.status,
      created_by_name: "Giảng Viên A",
      ...(state.status === "approved" || state.status === "published"
        ? { reviewed_by_name: "Giảng Viên A", reviewed_at: "2026-11-08T04:00:00Z" }
        : {}),
      ...(state.status === "published" ? { published_at: "2026-11-08T05:00:00Z" } : {}),
      ...(state.note ? { review_note: state.note } : {}),
    });
  const full = (): ScriptVersion => ({ ...summary(), content: SCRIPT, self_check_report: null as never });
  const step = (from: ScriptStatus, to: ScriptStatus) => () => {
    if (state.status !== from) return problem(409, "invalid_transition", "Sai trạng thái");
    state.status = to;
    return summary();
  };
  api.on("GET", "/scripts/:id", () => full());
  api.on("GET", "/exercises/:id", () =>
    exercise({
      latest_version: summary(),
      published_version: state.status === "published" ? summary() : undefined,
    }),
  );
  api.on("GET", "/exercises/:id/sheet-preview", {
    sheet: "Bài 01",
    sheet_names: ["Bài 01"],
    range: "A1:A1",
    rows: 1,
    cols: 1,
    truncated: false,
    cells: [],
    merged: [],
    col_widths: {},
    row_heights: {},
    hidden_rows: [],
    hidden_cols: [],
  });
  api.on("POST", "/scripts/:id/submit", step("draft", "pending_review"));
  api.on("POST", "/scripts/:id/approve", step("pending_review", "approved"));
  api.on("POST", "/scripts/:id/publish", step("approved", "published"));
  signIn();
  return { api, state };
}

test("gửi duyệt → duyệt → phát hành ngay trong trình sửa, rồi tải được file đề", async () => {
  const { api } = setupLifecycle();
  api.on(
    "GET",
    "/exercises/:id/starter-file",
    () =>
      new Response("xlsx", {
        headers: { "Content-Disposition": 'attachment; filename="b22-ham-tinh-tong.xlsx"' },
      }),
  );
  const createUrl = vi.fn(() => "blob:file-de");
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: createUrl, revokeObjectURL: vi.fn() }));
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Gửi duyệt" }, { timeout: 5000 }));
  await user.click(await screen.findByRole("button", { name: "Duyệt" }));
  await user.click(await screen.findByRole("button", { name: "Phát hành" }));
  const dialog = screen.getByRole("dialog", { name: "Phát hành bản 1" });
  expect(dialog).toHaveTextContent("nhúng mã bài b22-ham-tinh-tong");
  await user.click(within(dialog).getByRole("button", { name: "Phát hành" }));

  expect(await screen.findByText(/Học viên đang dùng bản này/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tải file đề cho học viên" }));
  expect(screen.queryByRole("alert")).toBeNull();
  await waitFor(() => expect(click).toHaveBeenCalledOnce());
  expect((click.mock.contexts[0] as HTMLAnchorElement).download).toBe("b22-ham-tinh-tong.xlsx");
  expect(api.callsTo("POST", `/scripts/${VERSION_ID}/publish`)).toHaveLength(1);
  click.mockRestore();
});

test("gửi duyệt bị chặn vì tự kiểm chưa đạt thì hiện từng lỗi", async () => {
  const { api } = setupLifecycle();
  api.on(
    "POST",
    "/scripts/:id/submit",
    problem(409, "self_check_failed", "Kịch bản chưa qua tự kiểm", [
      { path: "/self_check", message: "bước s1_first_total: mọi điều kiện đã đạt sẵn trên file đề" },
    ]),
  );
  renderApp(`/scripts/${VERSION_ID}`);

  await userEvent.click(await screen.findByRole("button", { name: "Gửi duyệt" }, { timeout: 5000 }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Chưa chuyển được trạng thái");
  expect(alert).toHaveTextContent("mọi điều kiện đã đạt sẵn trên file đề");
});

test("từ chối phải kèm góp ý, bản quay về nháp", async () => {
  const { api, state } = setupLifecycle();
  state.status = "pending_review";
  api.on("POST", "/scripts/:id/reject", (_req, _params, body) => {
    state.status = "draft";
    state.note = (body as { note: string }).note;
    return versionSummary({ status: "draft", review_note: state.note });
  });
  renderApp(`/scripts/${VERSION_ID}`);
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Từ chối" }, { timeout: 5000 }));
  const dialog = screen.getByRole("dialog", { name: "Từ chối kèm góp ý" });
  const submit = within(dialog).getByRole("button", { name: "Từ chối" });
  expect(submit).toBeDisabled();
  await user.type(within(dialog).getByLabelText("Góp ý cho người sửa"), "Gợi ý cấp 2 nên nhắc nút AutoSum.");
  await user.click(submit);

  expect(await screen.findByText(/góp ý khi duyệt: “Gợi ý cấp 2 nên nhắc nút AutoSum.”/)).toBeInTheDocument();
  expect(api.callsTo("POST", `/scripts/${VERSION_ID}/reject`)[0]?.body).toEqual({
    note: "Gợi ý cấp 2 nên nhắc nút AutoSum.",
  });
});

test("lịch sử bản trên trang bài: người tạo, người duyệt, so sánh bản AI với bản giảng viên sửa", async () => {
  const api = installFakeApi();
  const ai = versionSummary({
    status: "archived",
    created_by_name: "Giảng Viên A",
    reviewed_by_name: "Trưởng Bộ Môn",
    reviewed_at: "2026-11-08T04:00:00Z",
  });
  const edited = versionSummary({
    id: EDITED_ID,
    revision: 2,
    status: "published",
    origin: "ai_edited",
    parent_version_id: VERSION_ID,
    created_by_name: "Giảng Viên A",
    published_at: "2026-11-08T05:00:00Z",
  });
  api.on("GET", "/textbooks", []);
  api.on("GET", "/exercises/:id", exercise({ latest_version: edited, published_version: edited }));
  api.on("GET", "/exercises/:id/generation-jobs", []);
  api.on("GET", "/exercises/:id/scripts", [edited, ai]);
  api.on("GET", "/scripts/:id", (_req, params) =>
    params.id === EDITED_ID ? { ...edited, content: editedScript() } : { ...ai, content: SCRIPT },
  );
  signIn();
  renderApp(`/exercises/${EXERCISE_ID}`);
  const user = userEvent.setup();

  expect(await screen.findByText(/Học viên đang dùng bản 2/)).toBeInTheDocument();
  expect(await screen.findByText("Trưởng Bộ Môn")).toBeInTheDocument();
  expect(screen.getByText("AI sinh, giảng viên sửa")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "So với bản 1" }));

  const dialog = await screen.findByRole("dialog", { name: "So sánh bản 1 → bản 2" });
  expect(await within(dialog).findByText("2 chỗ khác, ở 2/3 bước.")).toBeInTheDocument();
  expect(within(dialog).getByText("Tổng tiền ngày 1")).toBeInTheDocument();
});

test("so sánh theo trường, bỏ qua số revision và nguồn gốc", () => {
  const changes = diffScripts(SCRIPT, editedScript());
  expect(changes.map((c) => [c.kind, c.where])).toEqual([
    ["changed", "Bước 1 “Tổng tiền ngày 1” › Tên"],
    ["changed", "Bước 2 “Sao chép công thức xuống các ngày còn lại” › Gợi ý cấp 1 › Lời gợi ý"],
  ]);
  expect(changedSteps(changes)).toBe(2);

  const removed = structuredClone(SCRIPT);
  removed.steps[2]!.feedback = undefined;
  const kinds = new Set(diffScripts(SCRIPT, removed).map((c) => c.kind));
  expect(kinds).toEqual(new Set(["removed"]));
});
