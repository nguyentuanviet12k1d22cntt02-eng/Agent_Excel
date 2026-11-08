import type { SelfCheckReport } from "@/api/types";
import { Alert } from "@/components/Alert";
import { formatPercent } from "@/lib/format";

import type { ScriptIssue } from "./scriptSchema";

/**
 * Tóm tắt kiểm 3 tầng (FR-W07): lỗi lược đồ của bản đang sửa (kiểm ngay trên trình duyệt) và báo cáo tự kiểm
 * của bản đã lưu (lỗi chặn gửi duyệt, cảnh báo, độ phủ thay đổi, chữ gợi ý).
 */
export function SelfCheckSummary({
  report,
  issues,
  dirty,
  onOpenIssue,
}: {
  report: SelfCheckReport | null;
  issues: ScriptIssue[];
  dirty: boolean;
  onOpenIssue: (path: string) => void;
}) {
  const errors = [...(report?.cross_reference_errors ?? []), ...(report?.errors ?? [])];
  const warnings = report?.warnings ?? [];
  const remaining = report?.generation?.remaining_issues ?? [];
  const hintIssues = report?.hint_text_issues ?? [];
  return (
    <section className="card">
      <div className="card__title">
        <h2>Kiểm tra kịch bản</h2>
      </div>
      {issues.length > 0 ? (
        <Alert
          kind="error"
          title={`Bản đang sửa có ${String(issues.length)} lỗi lược đồ, sửa xong mới lưu được`}
        >
          <ul className="issue-list">
            {issues.map((issue) => (
              <li key={issue.path + issue.message}>
                <button type="button" className="link-button" onClick={() => onOpenIssue(issue.path)}>
                  {issue.where}
                </button>
                : {issue.message}
              </li>
            ))}
          </ul>
        </Alert>
      ) : (
        <Alert kind="success">Bản đang sửa khớp lược đồ kịch bản v1.</Alert>
      )}
      <h3 className="section-gap--small">Tự kiểm trên file đề và đáp án (bản đã lưu)</h3>
      {dirty && (
        <p className="muted small">Có thay đổi chưa lưu: báo cáo dưới đây là của bản trước khi sửa.</p>
      )}
      {!report ? (
        <p className="muted">Chưa có báo cáo. Bấm “Chạy lại tự kiểm”.</p>
      ) : (
        <>
          <dl className="details details--compact">
            <dt>Độ phủ thay đổi</dt>
            <dd>
              {formatPercent(report.diff_coverage)}
              {(report.uncovered_ranges?.length ?? 0) > 0 && (
                <span className="muted small">
                  {" "}
                  · chưa có điều kiện kiểm: {report.uncovered_ranges?.join(", ")}
                </span>
              )}
            </dd>
            <dt>Chữ gợi ý</dt>
            <dd>
              {hintIssues.length === 0 ? (
                "Không có địa chỉ ô hay số liệu lạ"
              ) : (
                <span className="text-warning">{hintIssues.length} chỗ cần xem (đánh dấu ở từng bước)</span>
              )}
            </dd>
          </dl>
          {errors.length > 0 && (
            <Alert kind="error" title="Lỗi chặn gửi duyệt">
              <ul>
                {errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </Alert>
          )}
          {remaining.length > 0 && (
            <Alert kind="error" title="AI chưa sửa được sau các lần thử">
              <ul>
                {remaining.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </Alert>
          )}
          {warnings.length > 0 && (
            <Alert kind="warning" title="Nên xem lại">
              <ul>
                {warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </Alert>
          )}
          {errors.length === 0 && remaining.length === 0 && (
            <p className="text-success">Không có lỗi chặn: gửi duyệt được.</p>
          )}
        </>
      )}
    </section>
  );
}
