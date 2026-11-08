import { useState, type SubmitEvent } from "react";
import { Navigate, useLocation } from "react-router";

import { errorMessage } from "@/api/errors";
import { Alert } from "@/components/Alert";

import { useAuth } from "./authContext";

interface FromState {
  from?: string;
}

export function LoginPage() {
  const { state, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (state.status === "authenticated") {
    const from = (location.state as FromState | null)?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const notice = state.status === "anonymous" ? state.notice : undefined;
  return (
    <main className="login">
      <form className="login__card" onSubmit={(e) => void handleSubmit(e)} noValidate={false}>
        <div className="login__brand">
          <img src="/favicon.svg" alt="" width={40} height={40} />
          <div>
            <h1>Gia sư Excel</h1>
            <p className="muted">Trang quản trị cho giảng viên</p>
          </div>
        </div>
        {notice && <Alert kind="warning">{notice}</Alert>}
        {error && <Alert kind="error">{error}</Alert>}
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Mật khẩu</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
        <p className="muted small">Chưa có tài khoản? Liên hệ quản trị viên của trung tâm để được cấp.</p>
      </form>
    </main>
  );
}
