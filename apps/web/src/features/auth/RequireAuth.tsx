import { Navigate, Outlet, useLocation } from "react-router";

import type { Role } from "@/api/types";
import { Alert } from "@/components/Alert";
import { Loading } from "@/components/Loading";

import { useAuth } from "./authContext";

/** Chặn trang khi chưa đăng nhập: chuyển về trang đăng nhập, đăng nhập xong quay lại đúng trang. */
export function RequireAuth() {
  const { state } = useAuth();
  const location = useLocation();
  if (state.status === "loading") return <Loading label="Đang mở phiên đăng nhập…" fullPage />;
  if (state.status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <Outlet />;
}

/** Chặn trang theo vai trò (ví dụ trang tài khoản chỉ cho quản trị viên). */
export function RequireRole({ roles }: { roles: readonly Role[] }) {
  const { state } = useAuth();
  if (state.status !== "authenticated" || !roles.includes(state.user.role)) {
    return <Alert kind="error">Trang này chỉ dành cho quản trị viên.</Alert>;
  }
  return <Outlet />;
}
