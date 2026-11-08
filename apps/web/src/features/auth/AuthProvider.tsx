import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, refreshTokens, unwrap } from "@/api/client";
import { ApiError } from "@/api/errors";
import { clearTokens, getRefreshToken, onSessionExpired, saveTokens } from "@/api/tokens";
import type { User } from "@/api/types";

import { AuthContext, WEB_ROLES, type AuthContextValue, type AuthState } from "./authContext";

const STUDENT_NOTICE =
  "Tài khoản học viên dùng ứng dụng Gia sư Excel trên máy tính, không dùng trang quản trị.";
const EXPIRED_NOTICE = "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.";

async function fetchMe(): Promise<User> {
  return unwrap(api.GET("/auth/me"));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>(() =>
    getRefreshToken() ? { status: "loading" } : { status: "anonymous" },
  );

  const signOut = useCallback(
    (notice?: string) => {
      clearTokens();
      queryClient.clear();
      setState({ status: "anonymous", notice });
    },
    [queryClient],
  );

  const accept = useCallback(
    (user: User) => {
      if (!WEB_ROLES.includes(user.role)) {
        signOut(STUDENT_NOTICE);
        return;
      }
      setState({ status: "authenticated", user });
    },
    [signOut],
  );

  // Mở lại trang: dùng refresh token đã lưu để vào thẳng, không bắt đăng nhập lại
  useEffect(() => {
    if (state.status !== "loading") return;
    let cancelled = false;
    refreshTokens()
      .then(async (ok) => {
        if (!ok) throw new ApiError(401, "token_expired", EXPIRED_NOTICE);
        const user = await fetchMe();
        if (!cancelled) accept(user);
      })
      .catch(() => {
        if (!cancelled) signOut();
      });
    return () => {
      cancelled = true;
    };
  }, [state.status, accept, signOut]);

  useEffect(() => onSessionExpired(() => signOut(EXPIRED_NOTICE)), [signOut]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await unwrap(api.POST("/auth/login", { body: { email, password } }));
      saveTokens(tokens);
      accept(await fetchMe());
    },
    [accept],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ state, login, logout: () => signOut() }),
    [state, login, signOut],
  );
  return <AuthContext value={value}>{children}</AuthContext>;
}
