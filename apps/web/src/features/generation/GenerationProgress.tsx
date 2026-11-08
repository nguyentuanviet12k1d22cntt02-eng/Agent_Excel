import type { GenerationJob } from "@/api/types";

import { STAGES } from "./generationApi";

function secondsSince(iso: string | undefined): number | null {
  if (!iso) return null;
  return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
}

/** Các giai đoạn của job đang chạy: xong (✓), đang chạy (vòng quay), chưa tới. */
export function GenerationProgress({ job }: { job: GenerationJob }) {
  const current = STAGES.findIndex((s) => s.id === job.stage);
  const elapsed = secondsSince(job.started_at);
  return (
    <div className="progress" role="status" aria-live="polite">
      <p>
        <strong>{job.status === "queued" ? "Đang chờ tới lượt…" : "Đang sinh kịch bản…"}</strong>
        {elapsed !== null && <span className="muted small"> đã chạy {elapsed} giây</span>}
      </p>
      <ol className="progress__stages">
        {STAGES.map((stage, index) => {
          const state = index < current ? "done" : index === current ? "active" : "todo";
          return (
            <li key={stage.id} className={`progress__stage progress__stage--${state}`}>
              <span className="progress__icon" aria-hidden="true">
                {state === "done" ? (
                  "✓"
                ) : state === "active" ? (
                  <span className="spinner spinner--tiny" />
                ) : (
                  "•"
                )}
              </span>
              {stage.label}
              {state === "active" && stage.id === "llm" && (job.attempts ?? 0) > 1 && (
                <span className="muted small"> (lần gọi thứ {job.attempts}: AI sửa lỗi tự kiểm)</span>
              )}
              <span className="sr-only">
                {state === "done" ? " — xong" : state === "active" ? " — đang chạy" : ""}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="muted small">Thường mất 5–20 giây. Có thể rời trang, quay lại vẫn thấy kết quả.</p>
    </div>
  );
}
