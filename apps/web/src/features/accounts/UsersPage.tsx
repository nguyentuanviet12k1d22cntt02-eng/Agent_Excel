import { useState } from "react";

import type { Role } from "@/api/types";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { ROLE_LABELS } from "@/features/auth/authContext";

import { PAGE_SIZE, useUsers } from "./accountsApi";
import { ImportUsersDialog } from "./ImportUsersDialog";
import { UserCreateDialog } from "./UserCreateDialog";

const FILTERS: { role: Role | undefined; label: string }[] = [
  { role: undefined, label: "Tất cả" },
  { role: "teacher", label: "Giảng viên" },
  { role: "student", label: "Học viên" },
  { role: "admin", label: "Quản trị viên" },
];

export function UsersPage() {
  const [role, setRole] = useState<Role | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [dialog, setDialog] = useState<"create" | "import" | null>(null);
  const users = useUsers(role, page);
  const total = users.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="Tài khoản"
        subtitle="Giảng viên đăng nhập trang này; học viên đăng nhập ứng dụng Gia sư Excel trên máy tính."
        actions={
          <>
            <button type="button" className="btn" onClick={() => setDialog("import")}>
              Nhập từ CSV
            </button>
            <button type="button" className="btn btn--primary" onClick={() => setDialog("create")}>
              Thêm tài khoản
            </button>
          </>
        }
      />
      <div className="toolbar">
        <div className="segmented" role="group" aria-label="Lọc theo vai trò">
          {FILTERS.map((f) => (
            <button
              key={f.label}
              type="button"
              aria-pressed={role === f.role}
              onClick={() => {
                setRole(f.role);
                setPage(1);
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      {users.isPending && <Loading />}
      <ErrorAlert error={users.error} />
      {users.data && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Họ tên</th>
                <th>Email</th>
                <th>Vai trò</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {users.data.items.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>{ROLE_LABELS[u.role]}</td>
                  <td>{u.is_active === false ? <span className="badge">Đã khóa</span> : "Đang dùng"}</td>
                </tr>
              ))}
              {users.data.items.length === 0 && (
                <tr>
                  <td colSpan={4} className="muted">
                    Không có tài khoản nào.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      {pages > 1 && (
        <div className="row section-gap--small">
          <button
            type="button"
            className="btn btn--small"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            ← Trước
          </button>
          <span className="muted small">
            Trang {page}/{pages} · {total} tài khoản
          </span>
          <button
            type="button"
            className="btn btn--small"
            disabled={page >= pages}
            onClick={() => setPage(page + 1)}
          >
            Sau →
          </button>
        </div>
      )}
      {dialog === "create" && <UserCreateDialog onClose={() => setDialog(null)} />}
      {dialog === "import" && <ImportUsersDialog onClose={() => setDialog(null)} />}
    </>
  );
}
