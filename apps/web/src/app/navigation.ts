import type { Role } from "@/api/types";

export interface NavItem {
  to: string;
  label: string;
  roles?: readonly Role[]; // bỏ trống: mọi vai trò dùng được Web
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: "/exercises", label: "Bài tập" },
  { to: "/textbooks", label: "Giáo trình" },
  { to: "/classes", label: "Lớp học" },
  { to: "/users", label: "Tài khoản", roles: ["admin"] },
];
