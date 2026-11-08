import { Link } from "react-router";

import type { GenerationJob } from "@/api/types";
import { formatDateTime, formatDuration, formatNumber } from "@/lib/format";

import { JOB_STATUS_LABELS } from "./generationApi";

/** Mọi lần sinh của bài: mô hình, số lần gọi, token, thời gian (số liệu cho đánh giá kỹ thuật, FR-W06). */
export function GenerationHistory({ jobs }: { jobs: GenerationJob[] }) {
  return (
    <details className="history">
      <summary>Lịch sử sinh ({jobs.length} lần)</summary>
      <div className="table-wrap">
        <table className="table table--compact">
          <thead>
            <tr>
              <th>Thời điểm</th>
              <th>Trạng thái</th>
              <th>Mô hình</th>
              <th>Lần gọi</th>
              <th>Token vào / ra</th>
              <th>Thời gian</th>
              <th>Kết quả</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td className="nowrap">{formatDateTime(job.created_at)}</td>
                <td>
                  {JOB_STATUS_LABELS[job.status]}
                  {job.instructions && (
                    <div className="muted small" title={job.instructions}>
                      Có lưu ý cho AI
                    </div>
                  )}
                </td>
                <td>{job.model ?? "—"}</td>
                <td>{job.attempts ?? 0}</td>
                <td className="nowrap">
                  {formatNumber(job.prompt_tokens)} / {formatNumber(job.completion_tokens)}
                </td>
                <td className="nowrap">{formatDuration(job.duration_ms)}</td>
                <td>
                  {job.result_version_id ? (
                    <Link to={`/scripts/${job.result_version_id}`}>Mở bản kịch bản</Link>
                  ) : (
                    <span className="muted small" title={job.error}>
                      {job.status === "failed" ? "Không có bản nào" : "—"}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
