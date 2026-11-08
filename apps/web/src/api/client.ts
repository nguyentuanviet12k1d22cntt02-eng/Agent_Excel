/**
 * Client gọi Backend, kiểu dữ liệu sinh từ openapi.yaml.
 *
 * Mọi yêu cầu tự gắn access token. Gặp 401 thì đổi refresh token lấy token mới một lần rồi gửi lại; vẫn
 * 401 thì báo phiên hết hạn để giao diện quay về trang đăng nhập.
 */
import createClient from "openapi-fetch";

import { ApiError, toApiError } from "./errors";
import type { paths } from "./schema";
import { getAccessToken, getRefreshToken, notifySessionExpired, saveTokens } from "./tokens";
import type { TokenPair } from "./types";

/** Đường dẫn gốc của API. Mặc định cùng máy chủ với Web (Vite chuyển tiếp /api khi chạy dev). */
const CONFIGURED_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";
// Đổi thành địa chỉ tuyệt đối: Request ngoài trình duyệt (test) không tự hiểu đường dẫn tương đối
export const API_BASE_URL = new URL(CONFIGURED_BASE, window.location.origin).href.replace(/\/$/, "");

const AUTH_PATHS = ["/auth/login", "/auth/refresh"];

function withToken(request: Request): Request {
  const token = getAccessToken();
  if (!token) return request;
  const headers = new Headers(request.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return new Request(request, { headers });
}

let refreshing: Promise<boolean> | null = null;

async function requestNewTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;
  saveTokens((await response.json()) as TokenPair);
  return true;
}

/** Làm mới token; nhiều yêu cầu cùng gặp 401 chỉ gọi /auth/refresh một lần. */
export function refreshTokens(): Promise<boolean> {
  refreshing ??= requestNewTokens().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

function isAuthRequest(request: Request): boolean {
  const path = new URL(request.url).pathname;
  return AUTH_PATHS.some((p) => path.endsWith(p));
}

export async function authFetch(request: Request): Promise<Response> {
  const retry = request.clone();
  const response = await fetch(withToken(request));
  if (response.status !== 401 || isAuthRequest(request)) return response;
  if (await refreshTokens()) return fetch(withToken(retry));
  notifySessionExpired();
  return response;
}

export const api = createClient<paths>({ baseUrl: API_BASE_URL, fetch: authFetch });

interface FetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Lấy dữ liệu từ kết quả openapi-fetch; lỗi thì ném ApiError. */
export async function unwrap<T>(call: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok) throw toApiError(response.status, error);
  return data as T;
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

/**
 * Gửi multipart/form-data (tải file lên). openapi-fetch không kiểm được kiểu FormData theo đặc tả, nên kiểu
 * kết quả do nơi gọi chỉ rõ bằng kiểu sinh từ đặc tả (ví dụ `Exercise`).
 */
export async function sendForm<T>(method: "POST" | "PUT", path: string, form: FormData): Promise<T> {
  const response = await authFetch(new Request(`${API_BASE_URL}${path}`, { method, body: form }));
  const body = await readBody(response);
  if (!response.ok) throw toApiError(response.status, body);
  return body as T;
}

/** Tải file về (file đề đã nhúng mã bài): trả nội dung và tên file do Backend đặt. */
export async function downloadFile(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const response = await authFetch(new Request(`${API_BASE_URL}${path}`));
  if (!response.ok) throw toApiError(response.status, await readBody(response));
  return { blob: await response.blob(), filename: filenameFrom(response.headers.get("Content-Disposition")) };
}

export function filenameFrom(disposition: string | null): string | null {
  if (!disposition) return null;
  const encoded = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(disposition);
  if (encoded?.[1]) return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, ""));
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  return plain?.[1] ?? null;
}

export { ApiError };
