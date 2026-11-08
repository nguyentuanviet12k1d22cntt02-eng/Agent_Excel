import { useState } from "react";
import { Link } from "react-router";

import type { Exercise, ScriptVersionSummary } from "@/api/types";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { ScriptStatusBadge } from "@/components/ScriptStatusBadge";
import { formatDateTime } from "@/lib/format";
import { SCRIPT_ORIGIN_LABELS } from "@/lib/scriptLabels";

import { CompareDialog } from "./CompareDialog";
import { DownloadStarterButton } from "./DownloadStarterButton";
import { useScriptVersions } from "./publishingApi";

/** Bản để so với: bản gốc nó được sửa từ, nếu không có thì bản ngay trước. */
function baseOf(
  version: ScriptVersionSummary,
  all: ScriptVersionSummary[],
): ScriptVersionSummary | undefined {
  const parent = all.find((v) => v.id === version.parent_version_id);
  return parent ?? all.find((v) => v.revision === version.revision - 1);
}

/** Lịch sử revision của bài (FR-W10): ai tạo, ai duyệt, lúc nào, góp ý; mở, so sánh, tải file đề. */
export function VersionHistory({ exercise }: { exercise: Exercise }) {
  const versions = useScriptVersions(exercise.id);
  const [comparing, setComparing] = useState<[ScriptVersionSummary, ScriptVersionSummary] | null>(null);
  const published = exercise.published_version;

  return (
    <section className="card">
      <div className="card__title">
        <h2>Các bản kịch bản</h2>
        {published && <DownloadStarterButton exerciseId={exercise.id} code={exercise.code} />}
      </div>
      <p className="muted small">
        {published
          ? `Học viên đang dùng bản ${String(published.revision)} (phát hành ${formatDateTime(published.published_at)}). Bản nháp và bản chờ duyệt học viên không thấy.`
          : "Chưa có bản nào được phát hành: học viên chưa làm được bài này với gia sư."}
      </p>
      {versions.isPending && <Loading />}
      <ErrorAlert error={versions.error} />
      {versions.data?.length === 0 && <p className="muted">Chưa có bản nào. Bấm “Sinh kịch bản” ở trên.</p>}
      {versions.data && versions.data.length > 0 && (
        <div className="table-wrap">
          <table className="table table--compact">
            <thead>
              <tr>
                <th>Bản</th>
                <th>Trạng thái</th>
                <th>Tạo</th>
                <th>Duyệt</th>
                <th className="actions">
                  <span className="sr-only">Thao tác</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {versions.data.map((v) => {
                const base = baseOf(v, versions.data);
                return (
                  <tr key={v.id}>
                    <td>
                      <Link to={`/scripts/${v.id}`}>Bản {v.revision}</Link>
                    </td>
                    <td>
                      <ScriptStatusBadge status={v.status} />
                      {v.published_at && (
                        <div className="muted small">phát hành {formatDateTime(v.published_at)}</div>
                      )}
                    </td>
                    <td>
                      {SCRIPT_ORIGIN_LABELS[v.origin]}
                      <div className="muted small">
                        {v.created_by_name ?? "—"} · {formatDateTime(v.created_at)}
                      </div>
                    </td>
                    <td>
                      {v.reviewed_at ? (
                        <>
                          {v.reviewed_by_name ?? "—"}
                          <div className="muted small">{formatDateTime(v.reviewed_at)}</div>
                          {v.review_note && <div className="small">Góp ý: “{v.review_note}”</div>}
                        </>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td className="actions">
                      {base && (
                        <button
                          type="button"
                          className="btn btn--ghost btn--small"
                          onClick={() => setComparing([base, v])}
                        >
                          So với bản {base.revision}
                        </button>
                      )}
                      <Link to={`/scripts/${v.id}`} className="btn btn--small">
                        Mở
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {comparing && (
        <CompareDialog before={comparing[0]} after={comparing[1]} onClose={() => setComparing(null)} />
      )}
    </section>
  );
}
