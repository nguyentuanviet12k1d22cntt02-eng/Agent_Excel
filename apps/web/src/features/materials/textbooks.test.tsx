import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { installFakeApi, problem } from "@/test/fakeApi";
import { textbook } from "@/test/fixtures";
import { renderApp, signIn } from "@/test/renderApp";

test("tải giáo trình lên, tự hỏi lại trạng thái tới khi lập chỉ mục xong", async () => {
  const api = installFakeApi();
  let list = [textbook()];
  let polls = 0;
  api.on("GET", "/textbooks", () => {
    polls += 1;
    // Lần hỏi thứ 2 sau khi tải lên: đã lập chỉ mục xong
    if (list.some((t) => t.status === "indexing") && polls > 2) {
      list = list.map((t) =>
        t.status === "indexing" ? { ...t, status: "ready" as const, chunk_count: 7 } : t,
      );
    }
    return list;
  });
  api.on("POST", "/textbooks", (_req, _params, body) => {
    const form = body as FormData;
    const created = textbook({
      id: "44444444-4444-4444-8444-444444444444",
      title: form.get("title") as string,
      status: "indexing",
      chunk_count: 0,
    });
    list = [...list, created];
    return created;
  });
  signIn();
  renderApp("/textbooks");
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Tải giáo trình lên" }));
  const dialog = screen.getByRole("dialog", { name: "Tải giáo trình lên" });
  await user.upload(
    within(dialog).getByLabelText("File giáo trình (PDF hoặc DOCX)"),
    new File(["%PDF"], "chuong_3-ham.pdf", { type: "application/pdf" }),
  );
  expect(within(dialog).getByLabelText("Tên giáo trình")).toHaveValue("chuong 3 ham");
  await user.click(within(dialog).getByRole("button", { name: "Tải lên" }));

  expect(await screen.findByText("Đang lập chỉ mục")).toBeInTheDocument();
  const form = api.callsTo("POST", "/textbooks")[0]?.body as FormData;
  expect(form.get("title")).toBe("chuong 3 ham");
  expect(await (form.get("file") as Blob).text()).toBe("%PDF");
  // Hỏi lại sau 2 giây (thời gian thật): chờ tối đa 5 giây
  expect(await screen.findByText("Sẵn sàng · 7 đoạn", {}, { timeout: 5000 })).toBeInTheDocument();
}, 10_000);

test("xóa giáo trình đang gắn với bài thì hiện lỗi của Backend", async () => {
  const api = installFakeApi();
  api.on("GET", "/textbooks", [textbook()]);
  api.on("DELETE", "/textbooks/:id", problem(409, "textbook_in_use", "Giáo trình đang gắn với 2 bài tập"));
  signIn();
  renderApp("/textbooks");
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Xóa" }));
  await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Xóa" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Giáo trình đang gắn với 2 bài tập");
});

test("thử tìm đoạn giáo trình", async () => {
  const api = installFakeApi();
  api.on("GET", "/textbooks", [textbook()]);
  api.on("GET", "/textbooks/search", [
    {
      chunk_id: "55555555-5555-4555-8555-555555555555",
      textbook_id: textbook().id,
      textbook_title: "Giáo trình Excel cơ bản",
      heading: "Chương 3 > Hàm VLOOKUP",
      page: 41,
      content: "Hàm VLOOKUP tìm giá trị theo cột đầu tiên.",
      score: 7.25,
    },
  ]);
  signIn();
  renderApp("/textbooks");
  const user = userEvent.setup();

  await user.type(await screen.findByLabelText("Từ khóa"), "ham vlookup");
  await user.click(screen.getByRole("button", { name: "Tìm" }));

  expect(await screen.findByText("Chương 3 > Hàm VLOOKUP")).toBeInTheDocument();
  expect(screen.getByText(/trang 41/)).toBeInTheDocument();
  await waitFor(() =>
    expect(api.callsTo("GET", "/textbooks/search")[0]?.search).toContain("q=ham%20vlookup"),
  );
});
