import { useState, type SubmitEvent } from "react";

import type { Role } from "@/api/types";
import { Alert } from "@/components/Alert";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";
import { ROLE_LABELS } from "@/features/auth/authContext";

import { randomPassword } from "@/lib/password";

import { useCreateUser } from "./accountsApi";

const MIN_PASSWORD = 8;
export function UserCreateDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateUser();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("teacher");
  const [password, setPassword] = useState(() => randomPassword());
  const [created, setCreated] = useState<{ email: string; password: string } | null>(null);
  const valid = email.includes("@") && fullName.trim() && password.length >= MIN_PASSWORD;

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate(
      { email: email.trim(), full_name: fullName.trim(), role, password },
      { onSuccess: (user) => setCreated({ email: user.email, password }) },
    );
  }

  if (created) {
    return (
      <Modal
        title="Đã tạo tài khoản"
        onClose={onClose}
        footer={
          <button type="button" className="btn btn--primary" onClick={onClose}>
            Xong
          </button>
        }
      >
        <Alert kind="warning">
          Ghi lại mật khẩu để gửi cho người dùng: đóng hộp thoại là không xem lại được.
        </Alert>
        <dl className="details">
          <dt>Email</dt>
          <dd>{created.email}</dd>
          <dt>Mật khẩu</dt>
          <dd>
            <code className="secret">{created.password}</code>
          </dd>
        </dl>
      </Modal>
    );
  }

  return (
    <Modal
      title="Thêm tài khoản"
      onClose={onClose}
      busy={create.isPending}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={create.isPending}>
            Hủy
          </button>
          <button
            type="submit"
            form="user-create"
            className="btn btn--primary"
            disabled={!valid || create.isPending}
          >
            {create.isPending ? "Đang tạo…" : "Tạo tài khoản"}
          </button>
        </>
      }
    >
      <form id="user-create" className="stack" onSubmit={handleSubmit} noValidate>
        <ErrorAlert error={create.error} />
        <Field label="Họ tên">
          {(p) => (
            <input
              {...p}
              type="text"
              maxLength={200}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}
        </Field>
        <Field label="Email đăng nhập">
          {(p) => <input {...p} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />}
        </Field>
        <Field label="Vai trò">
          {(p) => (
            <select {...p} value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABELS[r]}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field
          label="Mật khẩu"
          hint={`Ít nhất ${String(MIN_PASSWORD)} ký tự. Đã tạo sẵn mật khẩu ngẫu nhiên.`}
        >
          {(p) => (
            <div className="row">
              <input
                {...p}
                type="text"
                className="grow"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button type="button" className="btn btn--small" onClick={() => setPassword(randomPassword())}>
                Tạo lại
              </button>
            </div>
          )}
        </Field>
      </form>
    </Modal>
  );
}
