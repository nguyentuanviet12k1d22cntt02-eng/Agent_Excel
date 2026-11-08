import { NavLink, Outlet, useMatches } from "react-router";

import { ROLE_LABELS, useAuth, useCurrentUser } from "@/features/auth/authContext";

import { NAV_ITEMS } from "./navigation";
import type { RouteHandle } from "./routes";

export function Layout() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const wide = useMatches().some((m) => (m.handle as RouteHandle | undefined)?.wide);
  const items = NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(user.role));
  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="topbar__brand">
          <img src="/favicon.svg" alt="" width={24} height={24} />
          Gia sư Excel
        </NavLink>
        <nav className="topbar__nav" aria-label="Chức năng">
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} className="topbar__link">
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="topbar__user">
          <span title={user.email}>
            {user.full_name} <span className="muted small">· {ROLE_LABELS[user.role]}</span>
          </span>
          <button type="button" className="btn btn--ghost btn--small" onClick={logout}>
            Đăng xuất
          </button>
        </div>
      </header>
      <main className={wide ? "content content--wide" : "content"}>
        <Outlet />
      </main>
    </div>
  );
}
