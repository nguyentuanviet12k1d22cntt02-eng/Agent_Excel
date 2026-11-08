import type { Role } from "@/api/types";

export interface NavItem {
  to: string;
  label: string;
  roles?: readonly Role[]; // bỏ trống: mọi vai trò dùng được Web
}

export const NAV_ITEMS: readonly NavItem[] = [{ to: "/", label: "Tổng quan" }];
