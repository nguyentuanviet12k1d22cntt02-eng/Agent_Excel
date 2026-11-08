import { api, API_BASE_URL, filenameFrom, unwrap } from "./client";
import { ApiError, errorMessage, NETWORK_ERROR, toApiError } from "./errors";
import { getRefreshToken, onSessionExpired, saveTokens } from "./tokens";
import { installFakeApi, problem } from "@/test/fakeApi";

function signIn() {
  saveTokens({ access_token: "old", refresh_token: "refresh-0", expires_in: 3600 });
}

test("đường dẫn API mặc định là /api/v1 trên cùng máy chủ", () => {
  expect(API_BASE_URL).toBe(`${window.location.origin}/api/v1`);
});

test("gắn access token vào mọi yêu cầu", async () => {
  const fake = installFakeApi();
  fake.on("GET", "/exercises", []);
  signIn();

  await unwrap(api.GET("/exercises"));

  expect(fake.callsTo("GET", "/exercises")[0]?.authorization).toBe("Bearer old");
});

test("token hết hạn thì làm mới một lần rồi gửi lại", async () => {
  const fake = installFakeApi();
  fake.on("GET", "/exercises", (request) =>
    request.headers.get("Authorization") === "Bearer old" ? problem(401, "token_expired", "hết hạn") : [],
  );
  signIn();

  const [first, second] = await Promise.all([unwrap(api.GET("/exercises")), unwrap(api.GET("/exercises"))]);

  expect(first).toEqual([]);
  expect(second).toEqual([]);
  expect(fake.callsTo("POST", "/auth/refresh")).toHaveLength(1);
  expect(fake.callsTo("GET", "/exercises").at(-1)?.authorization).toBe("Bearer access-1");
});

test("làm mới thất bại thì báo phiên hết hạn", async () => {
  const fake = installFakeApi();
  fake.on("GET", "/exercises", problem(401, "token_expired", "hết hạn"));
  fake.on("POST", "/auth/refresh", problem(401, "token_expired", "hết hạn"));
  const expired = vi.fn();
  const stop = onSessionExpired(expired);
  signIn();

  await expect(unwrap(api.GET("/exercises"))).rejects.toMatchObject({ status: 401 });

  expect(expired).toHaveBeenCalledOnce();
  expect(getRefreshToken()).toBeNull();
  stop();
});

test("lỗi problem+json giữ mã và chi tiết từng trường", async () => {
  const fake = installFakeApi();
  fake.on(
    "POST",
    "/exercises/:id/scripts",
    problem(422, "script_invalid", "Kịch bản không hợp lệ", [{ path: "/steps/0/title", message: "trống" }]),
  );
  signIn();

  const call = unwrap(
    api.POST("/exercises/{exercise_id}/scripts", {
      params: { path: { exercise_id: "e1" } },
      body: { content: {} as never },
    }),
  );

  await expect(call).rejects.toEqual(
    new ApiError(422, "script_invalid", "Kịch bản không hợp lệ", [
      { path: "/steps/0/title", message: "trống" },
    ]),
  );
});

test("lỗi không theo problem+json thì dùng câu theo mã HTTP", () => {
  expect(toApiError(403, "Forbidden").message).toBe("Tài khoản của bạn không có quyền làm việc này.");
  expect(toApiError(418, undefined).message).toBe("Yêu cầu không thành công (mã 418).");
  expect(errorMessage(new TypeError("Failed to fetch"))).toBe(NETWORK_ERROR);
});

test("đọc tên file tải về từ Content-Disposition", () => {
  expect(filenameFrom("attachment; filename*=utf-8''b%C3%A0i%2022.xlsx")).toBe("bài 22.xlsx");
  expect(filenameFrom('attachment; filename="de.xlsx"')).toBe("de.xlsx");
  expect(filenameFrom(null)).toBeNull();
});
