import { useState, type SubmitEvent } from "react";

import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";

import { useStartGeneration } from "./generationApi";

const MAX_INSTRUCTIONS = 2000;

export function GenerationDialog({ exerciseId, onClose }: { exerciseId: string; onClose: () => void }) {
  const start = useStartGeneration(exerciseId);
  const [instructions, setInstructions] = useState("");
  const [model, setModel] = useState("");

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    start.mutate(
      { instructions: instructions.trim() || undefined, model: model.trim() || undefined },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal
      title="Sinh kịch bản bằng AI"
      onClose={onClose}
      busy={start.isPending}
      wide
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={start.isPending}>
            Hủy
          </button>
          <button
            type="submit"
            form="generation-request"
            className="btn btn--primary"
            disabled={start.isPending}
          >
            {start.isPending ? "Đang gửi…" : "Bắt đầu sinh"}
          </button>
        </>
      }
    >
      <form id="generation-request" className="stack" onSubmit={handleSubmit}>
        <ErrorAlert error={start.error} />
        <Field
          label="Lưu ý thêm cho AI (tùy chọn)"
          hint={`Ví dụ: “Tách bước sao chép công thức thành bước riêng”, “Nhấn mạnh địa chỉ tuyệt đối”. Tối đa ${MAX_INSTRUCTIONS} ký tự.`}
        >
          {(p) => (
            <textarea
              {...p}
              rows={4}
              maxLength={MAX_INSTRUCTIONS}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
            />
          )}
        </Field>
        <details>
          <summary className="small">Tùy chọn nâng cao</summary>
          <Field label="Mô hình AI" hint="Bỏ trống: dùng mô hình mặc định của máy chủ.">
            {(p) => (
              <input
                {...p}
                type="text"
                maxLength={80}
                placeholder="mercury-3"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              />
            )}
          </Field>
        </details>
        <p className="muted small">
          Bản kịch bản cũ vẫn được giữ. Bản mới là bản nháp: chưa học viên nào thấy cho tới khi được duyệt và
          phát hành.
        </p>
      </form>
    </Modal>
  );
}
