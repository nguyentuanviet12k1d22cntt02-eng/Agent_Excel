import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div className="empty">
      <h1>Không có trang này</h1>
      <p className="muted">Đường dẫn có thể đã cũ hoặc gõ sai.</p>
      <Link to="/" className="btn">
        Về trang chính
      </Link>
    </div>
  );
}
