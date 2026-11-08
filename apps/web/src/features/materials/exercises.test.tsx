import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { installFakeApi, problem } from "@/test/fakeApi";
import { exercise, EXERCISE_ID, fixtureXlsx, textbook, versionSummary } from "@/test/fixtures";
import { renderApp, signIn } from "@/test/renderApp";

test("danh sách bài tập hiện trạng thái kịch bản và tìm theo tên", async () => {
  const api = installFakeApi();
  api.on("GET", "/exercises", (request) =>
    new URL(request.url).searchParams.get("q") === "zzz"
      ? []
      : [
          exercise({
            latest_version: versionSummary({ revision: 2, status: "pending_review" }),
            published_version: versionSummary({ revision: 1, status: "published" }),
            warnings: ["Bố cục lệch ở dòng 12"],
          }),
        ],
  );
  signIn();
  renderApp("/exercises");

  expect(await screen.findByRole("link", { name: "Hàm tính tổng SUM" })).toHaveAttribute(
    "href",
    `/exercises/${EXERCISE_ID}`,
  );
  expect(screen.getByText("Chờ duyệt")).toBeInTheDocument();
  expect(screen.getByText("Bản 1")).toBeInTheDocument();
  expect(screen.getByText("1 cảnh báo")).toBeInTheDocument();

  await userEvent.type(screen.getByLabelText("Tìm bài tập"), "zzz");
  expect(await screen.findByText("Không có bài nào khớp.")).toBeInTheDocument();
});

test("tạo bài: chọn sheet từ file đề, gợi ý mã bài, gửi đủ trường rồi mở trang bài", async () => {
  const api = installFakeApi();
  api.on("GET", "/textbooks", [textbook()]);
  api.on("POST", "/exercises", exercise());
  api.on("GET", "/exercises/:id", exercise());
  signIn();
  const { router } = renderApp("/exercises/new");
  const user = userEvent.setup();

  await user.type(await screen.findByLabelText("Tên bài"), "Hàm tính tổng SUM");
  expect(screen.getByLabelText("Mã bài")).toHaveValue("ham-tinh-tong-sum");
  await user.upload(screen.getByLabelText("File đề (.xlsx)"), fixtureXlsx("b22", "de.xlsx"));
  await user.upload(screen.getByLabelText("File đáp án (.xlsx)"), fixtureXlsx("b22", "dap-an.xlsx"));
  const sheet = await screen.findByRole("combobox", { name: "Sheet làm bài" });
  await user.selectOptions(sheet, "Bài 01");
  await user.type(screen.getByLabelText("Đề bài dạng chữ (tùy chọn)"), "Tính tổng tiền.");
  await user.click(await screen.findByRole("checkbox", { name: "Giáo trình Excel cơ bản" }));
  await user.click(screen.getByRole("button", { name: "Tạo bài tập" }));

  await waitFor(() => expect(router.state.location.pathname).toBe(`/exercises/${EXERCISE_ID}`));
  const form = api.callsTo("POST", "/exercises")[0]?.body as FormData;
  expect(form.get("code")).toBe("ham-tinh-tong-sum");
  expect(form.get("sheet_name")).toBe("Bài 01");
  expect(form.get("prompt_text")).toBe("Tính tổng tiền.");
  expect(form.getAll("textbook_ids")).toEqual([textbook().id]);
  // File của jsdom đi qua Request của Node thì mất tên (trình duyệt thật giữ tên): so theo kích thước
  expect((form.get("solution_file") as Blob).size).toBe(fixtureXlsx("b22", "dap-an.xlsx").size);
  expect((form.get("starter_file") as Blob).size).toBe(fixtureXlsx("b22", "de.xlsx").size);
});

test("Backend báo file đáp án chưa tính thì hiện ngay dưới ô file", async () => {
  const api = installFakeApi();
  api.on("GET", "/textbooks", []);
  api.on(
    "POST",
    "/exercises",
    problem(422, "solution_not_calculated", "File đáp án chưa có giá trị đã tính", [
      { path: "/solution_file", message: "Mở bằng Excel rồi lưu lại" },
    ]),
  );
  signIn();
  renderApp("/exercises/new");
  const user = userEvent.setup();

  await user.type(await screen.findByLabelText("Tên bài"), "Bài thử");
  await user.upload(screen.getByLabelText("File đề (.xlsx)"), fixtureXlsx("b22", "de.xlsx"));
  await user.upload(screen.getByLabelText("File đáp án (.xlsx)"), fixtureXlsx("b22", "dap-an.xlsx"));
  await user.selectOptions(await screen.findByRole("combobox", { name: "Sheet làm bài" }), "Bài 01");
  await user.click(screen.getByRole("button", { name: "Tạo bài tập" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("File đáp án chưa có giá trị đã tính");
  expect(screen.getByLabelText("File đáp án (.xlsx)")).toHaveAttribute("aria-invalid", "true");
});

test("sửa thông tin và xóa bài", async () => {
  const api = installFakeApi();
  api.on("GET", "/textbooks", [textbook()]);
  let current = exercise({ warnings: ["Ô H5 có ở đáp án nhưng không có ở đề"] });
  api.on("GET", "/exercises/:id", () => current);
  api.on("PATCH", "/exercises/:id", (_req, _params, body) => {
    current = { ...current, ...(body as object) };
    return current;
  });
  api.on("DELETE", "/exercises/:id", null);
  api.on("GET", "/exercises", []);
  signIn();
  const { router } = renderApp(`/exercises/${EXERCISE_ID}`);
  const user = userEvent.setup();

  expect(await screen.findByText("Ô H5 có ở đáp án nhưng không có ở đề")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Sửa thông tin" }));
  const dialog = screen.getByRole("dialog", { name: "Sửa thông tin bài" });
  await user.clear(within(dialog).getByLabelText("Tên bài"));
  await user.type(within(dialog).getByLabelText("Tên bài"), "Hàm SUM (sửa)");
  await user.click(within(dialog).getByRole("button", { name: "Lưu" }));
  expect(await screen.findByRole("heading", { name: "Hàm SUM (sửa)" })).toBeInTheDocument();
  expect(api.callsTo("PATCH", `/exercises/${EXERCISE_ID}`)[0]?.body).toMatchObject({
    title: "Hàm SUM (sửa)",
  });

  await user.click(screen.getByRole("button", { name: "Xóa bài" }));
  await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Xóa bài" }));
  await waitFor(() => expect(router.state.location.pathname).toBe("/exercises"));
});
