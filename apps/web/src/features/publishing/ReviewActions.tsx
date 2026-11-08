import { useState } from "react";

import { errorMessage } from "@/api/errors";
import type { Exercise, ScriptVersion } from "@/api/types";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";

import { DownloadStarterButton } from "./DownloadStarterButton";
import { useReviewAction } from "./publishingApi";

const MAX_NOTE = 2000;

/**
 * Nút chuyển trạng thái theo vòng đời kịch bản (FR-W10, FR-W11): nháp → gửi duyệt → duyệt (hoặc từ chối
 * kèm góp ý) → phát hành. Không có đường nào phát hành mà bỏ qua bước duyệt (NFR-13).
 */
export function ReviewActions({
  version,
  exercise,
  dirty,
}: {
  version: ScriptVersion;
  exercise: Exercise;
  dirty: boolean;
}) {
  const review = useReviewAction(version);
  const [dialog, setDialog] = useState<"reject" | "publish" | null>(null);
  const [note, setNote] = useState("");
  const blocked = dirty || review.isPending;
  const hint = dirty ? "Lưu hoặc bỏ thay đổi trước" : undefined;
  const published = exercise.published_version;

  function close() {
    setDialog(null);
    review.reset();
  }

  return (
    <>
      {version.status === "draft" && (
        <button
          type="button"
          className="btn btn--primary"
          disabled={blocked}
          title={hint}
          onClick={() => review.mutate({ action: "submit" })}
        >
          Gửi duyệt
        </button>
      )}
      {version.status === "pending_review" && (
        <>
          <button
            type="button"
            className="btn btn--danger"
            disabled={blocked}
            onClick={() => setDialog("reject")}
          >
            Từ chối
          </button>
          <button
            type="button"
            className="btn btn--primary"
            disabled={blocked}
            title={hint}
            onClick={() => review.mutate({ action: "approve" })}
          >
            Duyệt
          </button>
        </>
      )}
      {version.status === "approved" && (
        <button
          type="button"
          className="btn btn--primary"
          disabled={blocked}
          title={hint}
          onClick={() => setDialog("publish")}
        >
          Phát hành
        </button>
      )}
      {version.status === "published" && (
        <DownloadStarterButton exerciseId={exercise.id} code={exercise.code} primary />
      )}
      {dialog === null && review.error && (
        <div className="review-error">
          <ErrorAlert error={review.error} title="Chưa chuyển được trạng thái" />
        </div>
      )}

      {dialog === "reject" && (
        <Modal
          title="Từ chối kèm góp ý"
          onClose={close}
          busy={review.isPending}
          footer={
            <>
              <button type="button" className="btn" onClick={close} disabled={review.isPending}>
                Hủy
              </button>
              <button
                type="button"
                className="btn btn--danger"
                disabled={review.isPending || !note.trim()}
                onClick={() => review.mutate({ action: "reject", note: note.trim() }, { onSuccess: close })}
              >
                Từ chối
              </button>
            </>
          }
        >
          {review.error && <ErrorAlert error={review.error} />}
          <Field
            label="Góp ý cho người sửa"
            hint="Bản này quay về nháp; người sửa thấy góp ý ở đầu trình sửa."
          >
            {(p) => (
              <textarea
                {...p}
                rows={4}
                maxLength={MAX_NOTE}
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            )}
          </Field>
        </Modal>
      )}
      {dialog === "publish" && (
        <ConfirmDialog
          title={`Phát hành bản ${String(version.revision)}`}
          confirmLabel="Phát hành"
          busy={review.isPending}
          error={review.error ? errorMessage(review.error) : null}
          onCancel={close}
          onConfirm={() => review.mutate({ action: "publish" }, { onSuccess: close })}
        >
          <ul>
            <li>
              Hệ thống nhúng mã bài <code>{exercise.code}</code> vào file đề; học viên mở file đó thì gia sư
              tự nhận ra bài.
            </li>
            <li>Học viên được giao bài sẽ nhận bản này ở lần mở bài tiếp theo.</li>
            {published && <li>Bản đang phát hành (bản {published.revision}) chuyển sang lưu trữ.</li>}
          </ul>
        </ConfirmDialog>
      )}
    </>
  );
}
