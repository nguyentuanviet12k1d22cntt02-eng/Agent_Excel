import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { queryKeys } from "@/api/queryKeys";
import type { Exercise, GenerationJob } from "@/api/types";
import { Alert } from "@/components/Alert";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { formatDuration, formatNumber } from "@/lib/format";

import { GenerationDialog } from "./GenerationDialog";
import { GenerationHistory } from "./GenerationHistory";
import { GenerationProgress } from "./GenerationProgress";
import { isRunning, useGenerationJobs } from "./generationApi";

function JobResult({ job }: { job: GenerationJob }) {
  if (job.status === "failed") {
    return (
      <Alert kind="error" title="Lần sinh gần nhất không thành công">
        {job.error ?? "Không rõ lỗi."}
      </Alert>
    );
  }
  return (
    <Alert kind="success" title="Đã sinh xong bản kịch bản mới">
      <p className="small">
        {job.model} · {job.attempts ?? 0} lần gọi AI · {formatDuration(job.duration_ms)} · token vào/ra{" "}
        {formatNumber(job.prompt_tokens)} / {formatNumber(job.completion_tokens)}
      </p>
      {job.result_version_id && (
        <Link to={`/scripts/${job.result_version_id}`} className="btn btn--primary btn--small">
          Mở bản nháp để xem và sửa
        </Link>
      )}
    </Alert>
  );
}

/** Khi job chạy xong: làm mới thông tin bài và danh sách revision (có bản nháp mới). */
function useRefreshWhenFinished(exerciseId: string, latest: GenerationJob | undefined) {
  const client = useQueryClient();
  const wasRunning = useRef(false);
  const running = isRunning(latest);
  useEffect(() => {
    if (wasRunning.current && !running) {
      void client.invalidateQueries({ queryKey: queryKeys.exercise(exerciseId) });
    }
    wasRunning.current = running;
  }, [client, exerciseId, running]);
}

export function GenerationPanel({ exercise }: { exercise: Exercise }) {
  const jobs = useGenerationJobs(exercise.id);
  const [open, setOpen] = useState(false);
  const latest = jobs.data?.[0];
  const running = isRunning(latest);
  useRefreshWhenFinished(exercise.id, latest);

  return (
    <section className="card">
      <div className="card__title">
        <h2>Sinh kịch bản bằng AI</h2>
        <button
          type="button"
          className="btn btn--primary"
          disabled={running || jobs.isPending}
          onClick={() => setOpen(true)}
        >
          {exercise.latest_version ? "Sinh lại (giữ các bản cũ)" : "Sinh kịch bản"}
        </button>
      </div>
      <p className="muted small">
        Hệ thống so sánh file đề với file đáp án để biết học viên phải làm gì và suy ra điều kiện kiểm chứng;
        AI chỉ chia bước và viết lời hướng dẫn. Kịch bản sinh ra là bản nháp, cần giảng viên xem và duyệt.
      </p>
      {jobs.isPending && <Loading />}
      <ErrorAlert error={jobs.error} />
      {latest && running && <GenerationProgress job={latest} />}
      {latest && !running && <JobResult job={latest} />}
      {jobs.data && jobs.data.length > 0 && <GenerationHistory jobs={jobs.data} />}
      {open && <GenerationDialog exerciseId={exercise.id} onClose={() => setOpen(false)} />}
    </section>
  );
}
