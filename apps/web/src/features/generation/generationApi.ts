/** Sinh kịch bản bằng AI chạy nền (T5.5): yêu cầu sinh, hỏi trạng thái định kỳ, lịch sử sinh. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { GenerationJob } from "@/api/types";

/** Một lần sinh mất 5–20 giây (T5.8): hỏi lại mỗi 1,5 giây cho thanh tiến trình kịp đổi giai đoạn. */
const RUNNING_POLL_MS = 1500;

export function isRunning(job: GenerationJob | undefined): boolean {
  return job?.status === "queued" || job?.status === "running";
}

export function useGenerationJobs(exerciseId: string) {
  return useQuery({
    queryKey: queryKeys.generationJobs(exerciseId),
    queryFn: () =>
      unwrap(
        api.GET("/exercises/{exercise_id}/generation-jobs", {
          params: { path: { exercise_id: exerciseId } },
        }),
      ),
    refetchInterval: (query) => (isRunning(query.state.data?.[0]) ? RUNNING_POLL_MS : false),
  });
}

export interface GenerationRequest {
  instructions?: string;
  model?: string;
}

export function useStartGeneration(exerciseId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: GenerationRequest) =>
      unwrap(
        api.POST("/exercises/{exercise_id}/generation-jobs", {
          params: { path: { exercise_id: exerciseId } },
          body,
        }),
      ),
    onSuccess: (job) => {
      // Hiện ngay job vừa xếp hàng, không chờ lần hỏi tiếp theo
      client.setQueryData<GenerationJob[]>(queryKeys.generationJobs(exerciseId), (jobs) => [
        job,
        ...(jobs ?? []).filter((j) => j.id !== job.id),
      ]);
      // Khóa của bài bao cả lịch sử sinh; job chạy rất nhanh có thể đã xong ngay khi trả về
      return client.invalidateQueries({ queryKey: queryKeys.exercise(exerciseId) });
    },
  });
}

/** Giai đoạn của job theo thứ tự chạy (generation_service: diff → rag → llm → self_check). */
export const STAGES = [
  { id: "diff", label: "So sánh file đề với file đáp án" },
  { id: "rag", label: "Tìm đoạn giáo trình liên quan" },
  { id: "llm", label: "AI chia bước và viết gợi ý" },
  { id: "self_check", label: "Tự kiểm kịch bản trên file đề và đáp án" },
] as const;

export const JOB_STATUS_LABELS: Record<GenerationJob["status"], string> = {
  queued: "Đang chờ",
  running: "Đang chạy",
  succeeded: "Xong",
  failed: "Lỗi",
};
