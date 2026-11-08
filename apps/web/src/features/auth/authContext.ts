import { createContext, useContext } from "react";

import type { Role, User } from "@/api/types";

export type AuthState =
  { status: "loading" } | { status: "anonymous"; notice?: string } | { status: "authenticated"; user: User };

export interface AuthContextValue {
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth phải dùng bên trong AuthProvider");
  return value;
}

/** Người đang đăng nhập (chỉ dùng trong trang đã qua RequireAuth). */
export function useCurrentUser(): User {
  const { state } = useAuth();
  if (state.status !== "authenticated") throw new Error("Chưa đăng nhập");
  return state.user;
}

/** Web quản trị dành cho giảng viên và quản trị viên; học viên dùng ứng dụng Desktop. */
export const WEB_ROLES: readonly Role[] = ["admin", "teacher"];

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Quản trị viên",
  teacher: "Giảng viên",
  student: "Học viên",
};
