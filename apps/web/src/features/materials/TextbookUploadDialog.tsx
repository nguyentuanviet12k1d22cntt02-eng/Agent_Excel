import { useState, type SubmitEvent } from "react";

import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";

import { useUploadTextbook } from "./materialsApi";

const ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

function titleFromFileName(name: string): string {
  return name.replace(/\.(pdf|docx)$/i, "").replace(/[_-]+/g, " ");
}

export function TextbookUploadDialog({ onClose }: { onClose: () => void }) {
  const upload = useUploadTextbook();
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    upload.mutate({ title: title.trim(), file }, { onSuccess: onClose });
  }

  return (
    <Modal
      title="Tải giáo trình lên"
      onClose={onClose}
      busy={upload.isPending}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={upload.isPending}>
            Hủy
          </button>
          <button
            type="submit"
            form="textbook-upload"
            className="btn btn--primary"
            disabled={upload.isPending || !file || !title.trim()}
          >
            {upload.isPending ? "Đang tải lên…" : "Tải lên"}
          </button>
        </>
      }
    >
      <form id="textbook-upload" className="stack" onSubmit={handleSubmit} noValidate>
        <ErrorAlert error={upload.error} />
        <Field
          label="File giáo trình (PDF hoặc DOCX)"
          hint="Hệ thống tách theo chương, mục. PDF phải có chữ (không phải ảnh quét)."
        >
          {(p) => (
            <input
              {...p}
              type="file"
              accept={ACCEPT}
              required
              onChange={(e) => {
                const chosen = e.target.files?.[0] ?? null;
                setFile(chosen);
                if (chosen && !title) setTitle(titleFromFileName(chosen.name));
              }}
            />
          )}
        </Field>
        <Field label="Tên giáo trình">
          {(p) => (
            <input
              {...p}
              type="text"
              required
              maxLength={200}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          )}
        </Field>
      </form>
    </Modal>
  );
}
