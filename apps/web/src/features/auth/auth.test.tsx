import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { getRefreshToken } from "@/api/tokens";
import { installFakeApi, problem, TEACHER } from "@/test/fakeApi";
import { renderApp, signIn } from "@/test/renderApp";

async function fillLogin(email: string, password: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Mật khẩu"), password);
  await user.click(screen.getByRole("button", { name: "Đăng nhập" }));
}

test("chưa đăng nhập thì chuyển về trang đăng nhập, đăng nhập xong quay lại trang đã mở", async () => {
  const api = installFakeApi();
  const { router } = renderApp("/khong-co");

  await fillLogin("gv@tdmu.edu.vn", "matkhau123");

  expect(await screen.findByText("Không có trang này")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/khong-co");
  expect(api.callsTo("GET", "/auth/me")[0]?.authorization).toBe("Bearer access-1");
  expect(getRefreshToken()).toBe("refresh-1");
});

test("sai mật khẩu thì hiện thông báo của Backend", async () => {
  installFakeApi();
  renderApp("/");

  await fillLogin("gv@tdmu.edu.vn", "saimatkhau");

  expect(await screen.findByRole("alert")).toHaveTextContent("Sai email hoặc mật khẩu");
  expect(getRefreshToken()).toBeNull();
});

test("học viên không vào được trang quản trị", async () => {
  installFakeApi({ ...TEACHER, role: "student" });
  renderApp("/");

  await fillLogin("hv@tdmu.edu.vn", "matkhau123");

  expect(await screen.findByText(/Tài khoản học viên dùng ứng dụng/)).toBeInTheDocument();
  expect(getRefreshToken()).toBeNull();
});

test("mở lại trang thì dùng refresh token đã lưu, không bắt đăng nhập lại", async () => {
  installFakeApi();
  signIn();
  renderApp("/");

  expect(await screen.findByText(`Xin chào, ${TEACHER.full_name}`)).toBeInTheDocument();
});

test("refresh token hết hạn thì về trang đăng nhập", async () => {
  const api = installFakeApi();
  api.on("POST", "/auth/refresh", problem(401, "token_expired", "Token đã hết hạn"));
  signIn();
  renderApp("/");

  expect(await screen.findByLabelText("Email")).toBeInTheDocument();
  expect(getRefreshToken()).toBeNull();
});

test("đăng xuất thì xóa token và về trang đăng nhập", async () => {
  installFakeApi();
  signIn();
  renderApp("/");
  await screen.findByText(`Xin chào, ${TEACHER.full_name}`);

  await userEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));

  expect(await screen.findByLabelText("Email")).toBeInTheDocument();
  expect(getRefreshToken()).toBeNull();
});
