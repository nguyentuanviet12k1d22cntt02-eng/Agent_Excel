import type { ReactNode } from "react";

import { Alert } from "./Alert";
import { Modal } from "./Modal";

/** Hỏi lại trước thao tác khó hoàn tác (xóa, phát hành). */
export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  danger = false,
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal
      title={title}
      onClose={onCancel}
      busy={busy}
      footer={
        <>
          <button type="button" className="btn" onClick={onCancel} disabled={busy}>
            Hủy
          </button>
          <button
            type="button"
            className={danger ? "btn btn--danger" : "btn btn--primary"}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? "Đang xử lý…" : confirmLabel}
          </button>
        </>
      }
    >
      {error && <Alert kind="error">{error}</Alert>}
      {children}
    </Modal>
  );
}
