import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { GenerationJob } from "@/api/types";
import { installFakeApi, problem, type FakeApi } from "@/test/fakeApi";
import { exercise, EXERCISE_ID, VERSION_ID, versionSummary } from "@/test/fixtures";
import { renderApp, signIn } from "@/test/renderApp";

const JOB_ID = "66666666-6666-4666-8666-666666666666";

function job(overrides: Partial<GenerationJob> = {}): GenerationJob {
  return {
    id: JOB_ID,
    exercise_id: EXERCISE_ID,
    status: "succeeded",
    stage: "self_check",
    model: "mercury-3",
    attempts: 1,
    prompt_tokens: 5068,
    completion_tokens: 5156,
    duration_ms: 8600,
    result_version_id: VERSION_ID,
    created_at: "2026-11-08T03:00:00Z",
    started_at: "2026-11-08T03:00:01Z",
    finished_at: "2026-11-08T03:00:10Z",
    ...overrides,
  };
}

function setup(jobs: () => GenerationJob[]): FakeApi {
  const api = installFakeApi();
  api.on("GET", "/textbooks", []);
  api.on("GET", "/exercises/:id", exercise());
  api.on("GET", "/exercises/:id/generation-jobs", () => jobs());
  signIn();
  return api;
}

test("job đang chạy: hiện giai đoạn, hỏi lại tới khi xong rồi mở được bản nháp", async () => {
  let polls = 0;
  const api = setup(() => {
    polls += 1;
    return polls < 2
      ? [job({ status: "running", stage: "llm", attempts: 2, result_version_id: undefined })]
      : [job({ attempts: 2 })];
  });
  renderApp(`/exercises/${EXERCISE_ID}`);

  expect(await screen.findByText("Đang sinh kịch bản…")).toBeInTheDocument();
  expect(screen.getByText(/lần gọi thứ 2/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Sinh kịch bản" })).toBeDisabled();

  const open = await screen.findByRole("link", { name: "Mở bản nháp để xem và sửa" }, { timeout: 4000 });
  expect(open).toHaveAttribute("href", `/scripts/${VERSION_ID}`);
  expect(screen.getByText(/2 lần gọi AI · 8,6 giây/)).toBeInTheDocument();
  // Xong thì làm mới thông tin bài (có revision mới)
  await waitFor(() => expect(api.callsTo("GET", `/exercises/${EXERCISE_ID}`).length).toBeGreaterThan(1));
}, 10_000);

test("bấm sinh lại, gửi lưu ý cho AI và mô hình", async () => {
  let jobs: GenerationJob[] = [job()];
  const api = setup(() => jobs);
  api.on("GET", "/exercises/:id", exercise({ latest_version: versionSummary() }));
  api.on("POST", "/exercises/:id/generation-jobs", () => {
    const queued = job({ id: "77777777-7777-4777-8777-777777777777", status: "queued", stage: undefined });
    jobs = [queued, ...jobs];
    return queued;
  });
  renderApp(`/exercises/${EXERCISE_ID}`);
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Sinh lại (giữ các bản cũ)" }));
  const dialog = screen.getByRole("dialog", { name: "Sinh kịch bản bằng AI" });
  await user.type(within(dialog).getByLabelText("Lưu ý thêm cho AI (tùy chọn)"), "Tách bước sao chép.");
  await user.click(within(dialog).getByText("Tùy chọn nâng cao"));
  await user.type(within(dialog).getByLabelText("Mô hình AI"), "mercury-2");
  await user.click(within(dialog).getByRole("button", { name: "Bắt đầu sinh" }));

  expect(await screen.findByText("Đang chờ tới lượt…")).toBeInTheDocument();
  expect(api.callsTo("POST", `/exercises/${EXERCISE_ID}/generation-jobs`)[0]?.body).toEqual({
    instructions: "Tách bước sao chép.",
    model: "mercury-2",
  });
  expect(screen.getByText("Lịch sử sinh (2 lần)")).toBeInTheDocument();
});

test("lần sinh lỗi thì hiện lỗi; đang có job thì Backend báo 409", async () => {
  const api = setup(() => [
    job({ status: "failed", error: "File đáp án không khác file đề", result_version_id: undefined }),
  ]);
  api.on(
    "POST",
    "/exercises/:id/generation-jobs",
    problem(409, "generation_in_progress", "Bài này đang được sinh kịch bản, chờ xong rồi sinh lại"),
  );
  renderApp(`/exercises/${EXERCISE_ID}`);
  const user = userEvent.setup();

  expect(await screen.findByText("File đáp án không khác file đề")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Sinh kịch bản" }));
  await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Bắt đầu sinh" }));

  expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent(
    "Bài này đang được sinh kịch bản",
  );
});
