import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { User } from "@/api/types";
import { ADMIN, installFakeApi, TEACHER } from "@/test/fakeApi";
import { exercise, EXERCISE_ID } from "@/test/fixtures";
import { renderApp, signIn } from "@/test/renderApp";
import { randomPassword } from "@/lib/password";

const CLASS_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const STUDENT: User = {
  id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  email: "hv01@tdmu.edu.vn",
  full_name: "Trần Thị B",
  role: "student",
  is_active: true,
};

test("quản trị: danh sách tài khoản lọc theo vai trò, thêm tài khoản và xem mật khẩu một lần", async () => {
  const api = installFakeApi(ADMIN);
  api.on("GET", "/users", (request) => {
    const role = new URL(request.url).searchParams.get("role");
    const items = [TEACHER, STUDENT].filter((u) => !role || u.role === role);
    return { items, total: items.length };
  });
  api.on("POST", "/users", (_req, _params, body) => ({ ...STUDENT, ...(body as object), id: "new" }));
  signIn();
  renderApp("/users");
  const user = userEvent.setup();

  expect(await screen.findByText("Trần Thị B")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Giảng viên" }));
  await waitFor(() => expect(screen.queryByText("Trần Thị B")).toBeNull());
  expect(api.calls.at(-1)?.search).toContain("role=teacher");

  await user.click(screen.getByRole("button", { name: "Thêm tài khoản" }));
  const dialog = screen.getByRole("dialog", { name: "Thêm tài khoản" });
  await user.type(within(dialog).getByLabelText("Họ tên"), "Lê Văn C");
  await user.type(within(dialog).getByLabelText("Email đăng nhập"), "gv2@tdmu.edu.vn");
  const password = within(dialog).getByLabelText<HTMLInputElement>("Mật khẩu").value;
  await user.click(within(dialog).getByRole("button", { name: "Tạo tài khoản" }));

  const done = await screen.findByRole("dialog", { name: "Đã tạo tài khoản" });
  expect(done).toHaveTextContent(password);
  expect(api.callsTo("POST", "/users")[0]?.body).toEqual({
    email: "gv2@tdmu.edu.vn",
    full_name: "Lê Văn C",
    role: "teacher",
    password,
  });
});

test("nhập CSV: hiện số tạo, dòng bỏ qua, mật khẩu tự tạo và cho tải về", async () => {
  const api = installFakeApi(ADMIN);
  api.on("GET", "/users", { items: [], total: 0 });
  api.on("POST", "/users/import", {
    created: 2,
    skipped: [{ line: 4, reason: "email đã tồn tại" }],
    generated_passwords: [{ email: "hv01@tdmu.edu.vn", password: "Abc23xyzQ9" }],
  });
  const saved = vi.fn(() => "blob:mat-khau");
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: saved, revokeObjectURL: vi.fn() }));
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  signIn();
  renderApp("/users");
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Nhập từ CSV" }));
  const dialog = screen.getByRole("dialog", { name: "Nhập tài khoản từ CSV" });
  await user.upload(
    within(dialog).getByLabelText("File CSV"),
    new File(["email,full_name\nhv01@tdmu.edu.vn,A\n"], "ds.csv", { type: "text/csv" }),
  );
  await user.click(within(dialog).getByRole("button", { name: "Nhập" }));

  expect(await within(dialog).findByText("Đã tạo 2 tài khoản.")).toBeInTheDocument();
  expect(within(dialog).getByText("Dòng 4: email đã tồn tại")).toBeInTheDocument();
  expect(within(dialog).getByText("Abc23xyzQ9")).toBeInTheDocument();
  await user.click(within(dialog).getByRole("button", { name: "Tải danh sách mật khẩu (CSV)" }));
  expect((click.mock.contexts[0] as HTMLAnchorElement).download).toBe("mat-khau-hoc-vien.csv");
  click.mockRestore();
});

test("giảng viên không thấy và không vào được trang tài khoản", async () => {
  installFakeApi(TEACHER);
  signIn();
  renderApp("/users");

  expect(await screen.findByText("Trang này chỉ dành cho quản trị viên.")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Tài khoản" })).toBeNull();
  expect(screen.getByRole("link", { name: "Lớp học" })).toBeInTheDocument();
});

test("lớp học: chia nhóm học viên, giao bài có hạn, gỡ bài", async () => {
  const api = installFakeApi(ADMIN);
  let members: { student_id: string; email: string; full_name: string; study_group: string }[] = [];
  let assigned: {
    exercise_id: string;
    code: string;
    title: string;
    due_at?: string;
    published_revision: null;
  }[] = [];
  api.on("GET", "/classes", [
    {
      id: CLASS_ID,
      name: "Tin học K12",
      teacher_id: TEACHER.id,
      teacher_name: "Giảng Viên A",
      member_count: 0,
    },
  ]);
  api.on("GET", "/classes/:id/members", () => members);
  api.on("PUT", "/classes/:id/members", (_req, _params, body) => {
    members = (body as { student_id: string; study_group: string }[]).map((m) => ({
      ...m,
      email: STUDENT.email,
      full_name: STUDENT.full_name,
    }));
    return null;
  });
  api.on("GET", "/classes/:id/exercises", () => assigned);
  api.on("POST", "/classes/:id/exercises", (_req, _params, body) => {
    const { due_at } = body as { due_at?: string };
    assigned = [
      {
        exercise_id: EXERCISE_ID,
        code: "b22-ham-tinh-tong",
        title: "Hàm SUM",
        due_at,
        published_revision: null,
      },
    ];
    return null;
  });
  api.on("DELETE", "/classes/:id/exercises/:exercise", () => {
    assigned = [];
    return null;
  });
  api.on("GET", "/users", { items: [STUDENT], total: 1 });
  api.on("GET", "/exercises", [exercise()]);
  signIn();
  renderApp(`/classes/${CLASS_ID}`);
  const user = userEvent.setup();

  await user.click(await screen.findByRole("button", { name: "Sửa danh sách và nhóm" }));
  const membersDialog = screen.getByRole("dialog", { name: "Học viên của lớp" });
  await user.click(await within(membersDialog).findByLabelText("Cho Trần Thị B vào lớp"));
  await user.selectOptions(within(membersDialog).getByLabelText("Nhóm của Trần Thị B"), "control");
  await user.click(within(membersDialog).getByRole("button", { name: "Lưu danh sách" }));
  expect(await screen.findByText("Đối chứng (chỉ ghi nhật ký)")).toBeInTheDocument();
  expect(api.callsTo("PUT", `/classes/${CLASS_ID}/members`)[0]?.body).toEqual([
    { student_id: STUDENT.id, study_group: "control" },
  ]);

  await user.click(screen.getByRole("button", { name: "Giao bài" }));
  const assign = screen.getByRole("dialog", { name: "Giao bài cho lớp" });
  await user.selectOptions(await within(assign).findByLabelText("Bài tập"), EXERCISE_ID);
  expect(within(assign).getByText(/Bài chưa phát hành kịch bản/)).toBeInTheDocument();
  await user.type(within(assign).getByLabelText("Hạn hoàn thành (tùy chọn)"), "2027-01-10T17:00");
  await user.click(within(assign).getByRole("button", { name: "Giao bài" }));
  expect(await screen.findByText("Chưa phát hành: học viên chưa làm được")).toBeInTheDocument();
  const sent = api.callsTo("POST", `/classes/${CLASS_ID}/exercises`)[0]?.body as { due_at: string };
  expect(new Date(sent.due_at).getTime()).toBe(new Date("2027-01-10T17:00").getTime());

  await user.click(screen.getByRole("button", { name: "Gỡ" }));
  await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Gỡ bài" }));
  expect(await screen.findByText("Chưa giao bài nào.")).toBeInTheDocument();
});

test("mật khẩu ngẫu nhiên đủ dài, không có chữ dễ nhầm", () => {
  const passwords = Array.from({ length: 50 }, () => randomPassword());
  expect(passwords.every((p) => p.length === 10 && !/[l1IO0o]/.test(p))).toBe(true);
  expect(new Set(passwords).size).toBe(50);
});
