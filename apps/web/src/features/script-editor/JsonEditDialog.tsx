import { useState } from "react";

import { Alert } from "@/components/Alert";
import { Modal } from "@/components/Modal";

/**
 * Sửa trực tiếp JSON của một phần kịch bản (điều kiện, cả bước). Dành cho chỗ biểu mẫu chưa có ô sửa riêng;
 * sau khi áp dụng, cả kịch bản được kiểm lại theo lược đồ.
 */
export function JsonEditDialog({
  title,
  value,
  hint,
  onApply,
  onClose,
}: {
  title: string;
  value: unknown;
  hint?: string;
  onApply: (value: unknown) => void;
  onClose: () => void;
}) {
  const [text, setText] = useState(() => JSON.stringify(value, null, 2));
  const [error, setError] = useState<string | null>(null);

  function apply() {
    try {
      onApply(JSON.parse(text) as unknown);
      onClose();
    } catch (err) {
      setError(`JSON sai cú pháp: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return (
    <Modal
      title={title}
      onClose={onClose}
      wide
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            Hủy
          </button>
          <button type="button" className="btn btn--primary" onClick={apply}>
            Áp dụng
          </button>
        </>
      }
    >
      {error && <Alert kind="error">{error}</Alert>}
      {hint && <p className="muted small">{hint}</p>}
      <textarea
        aria-label="Nội dung JSON"
        className="json-editor"
        rows={18}
        spellCheck={false}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setError(null);
        }}
      />
    </Modal>
  );
}
