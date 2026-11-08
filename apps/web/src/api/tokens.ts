/**
 * Giữ token đăng nhập.
 *
 * Access token chỉ nằm trong bộ nhớ (hết hạn sau 60 phút). Refresh token lưu trong localStorage để mở lại
 * trình duyệt không phải đăng nhập lại; đăng xuất thì xóa.
 */
import type { TokenPair } from "./types";

const REFRESH_KEY = "tutor.refresh_token";

let accessToken: string | null = null;
const expiredListeners = new Set<() => void>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null; // trình duyệt chặn lưu trữ: chỉ đăng nhập trong phiên hiện tại
  }
}

export function saveTokens(tokens: TokenPair): void {
  accessToken = tokens.access_token;
  try {
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } catch {
    // không lưu được thì thôi: vẫn dùng được tới khi đóng trang
  }
}

export function clearTokens(): void {
  accessToken = null;
  try {
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    // không có gì để xóa
  }
}

/** Báo cho giao diện khi phiên đăng nhập hết hạn hẳn (refresh token cũng hết hạn). */
export function onSessionExpired(listener: () => void): () => void {
  expiredListeners.add(listener);
  return () => expiredListeners.delete(listener);
}

export function notifySessionExpired(): void {
  clearTokens();
  for (const listener of expiredListeners) listener();
}
