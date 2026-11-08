import { useState } from "react";

import type { Textbook } from "@/api/types";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { errorMessage } from "@/api/errors";

import { useDeleteTextbook, useTextbooks } from "./materialsApi";
import { PassageSearch } from "./PassageSearch";
import { TextbookStatusBadge } from "./TextbookStatusBadge";
import { TextbookUploadDialog } from "./TextbookUploadDialog";

export function TextbooksPage() {
  const textbooks = useTextbooks();
  const remove = useDeleteTextbook();
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState<Textbook | null>(null);

  function confirmDelete() {
    if (!deleting) return;
    remove.mutate(deleting.id, {
      onSuccess: () => {
        setDeleting(null);
      },
    });
  }

  return (
    <>
      <PageHeader
        title="Giáo trình"
        subtitle="AI trích đoạn giáo trình liên quan khi viết gợi ý cho học viên."
        actions={
          <button type="button" className="btn btn--primary" onClick={() => setUploading(true)}>
            Tải giáo trình lên
          </button>
        }
      />
      {textbooks.isPending && <Loading />}
      <ErrorAlert error={textbooks.error} />
      {textbooks.data?.length === 0 && (
        <div className="card empty">
          <p>Chưa có giáo trình nào.</p>
          <p className="muted small">Tải lên file PDF hoặc DOCX có tiêu đề chương, mục rõ ràng.</p>
        </div>
      )}
      {textbooks.data && textbooks.data.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Tên giáo trình</th>
                <th>Loại file</th>
                <th>Trạng thái</th>
                <th className="actions">
                  <span className="sr-only">Thao tác</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {textbooks.data.map((textbook) => (
                <tr key={textbook.id}>
                  <td>{textbook.title}</td>
                  <td>{textbook.file_type?.toUpperCase() ?? "—"}</td>
                  <td>
                    <TextbookStatusBadge textbook={textbook} />
                    {textbook.status === "failed" && textbook.error && (
                      <div className="field__error">{textbook.error}</div>
                    )}
                  </td>
                  <td className="actions">
                    <button
                      type="button"
                      className="btn btn--danger btn--small"
                      onClick={() => {
                        remove.reset();
                        setDeleting(textbook);
                      }}
                    >
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <PassageSearch />

      {uploading && <TextbookUploadDialog onClose={() => setUploading(false)} />}
      {deleting && (
        <ConfirmDialog
          title="Xóa giáo trình"
          confirmLabel="Xóa"
          danger
          busy={remove.isPending}
          error={remove.error ? errorMessage(remove.error) : null}
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        >
          <p>
            Xóa giáo trình <strong>{deleting.title}</strong> và các đoạn đã lập chỉ mục? Kịch bản đã sinh vẫn
            giữ đoạn trích cũ.
          </p>
        </ConfirmDialog>
      )}
    </>
  );
}
