/** Duyệt, phát hành, lịch sử revision, tải file đề đã nhúng mã bài (T5.6). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, downloadFile, unwrap } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ScriptVersion, ScriptVersionSummary } from "@/api/types";

export function useScriptVersions(exerciseId: string) {
  return useQuery({
    queryKey: queryKeys.scriptVersions(exerciseId),
    queryFn: () =>
      unwrap(api.GET("/exercises/{exercise_id}/scripts", { params: { path: { exercise_id: exerciseId } } })),
  });
}

export type ReviewAction = "submit" | "approve" | "reject" | "publish";

function callAction(versionId: string, action: ReviewAction, note: string | undefined) {
  const params = { path: { version_id: versionId } };
  switch (action) {
    case "submit":
      return unwrap(api.POST("/scripts/{version_id}/submit", { params }));
    case "approve":
      return unwrap(api.POST("/scripts/{version_id}/approve", { params }));
    case "reject":
      return unwrap(api.POST("/scripts/{version_id}/reject", { params, body: { note: note ?? "" } }));
    case "publish":
      return unwrap(api.POST("/scripts/{version_id}/publish", { params }));
  }
}

/** Chuyển trạng thái một revision; xong thì cập nhật revision đang mở, lịch sử và thông tin bài. */
export function useReviewAction(version: { id: string; exercise_id: string }) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ action, note }: { action: ReviewAction; note?: string }) =>
      callAction(version.id, action, note),
    onSuccess: (summary: ScriptVersionSummary) => {
      client.setQueryData<ScriptVersion>(queryKeys.script(version.id), (current) =>
        current ? { ...current, ...summary } : current,
      );
      // Phát hành bản mới thì bản phát hành cũ thành "lưu trữ": làm mới mọi revision của bài
      void client.invalidateQueries({ queryKey: ["scripts"] });
      return client.invalidateQueries({ queryKey: queryKeys.exercise(version.exercise_id) });
    },
    // Gửi duyệt bị chặn vì tự kiểm thì Backend đã lưu báo cáo mới: lấy lại để hiện đúng lỗi
    onError: () => client.invalidateQueries({ queryKey: queryKeys.script(version.id) }),
  });
}

/** Tải file đề đã nhúng mã bài và revision (chỉ có khi đã phát hành) để phát cho học viên. */
export async function downloadStarterFile(exerciseId: string, fallbackName: string): Promise<void> {
  const { blob, filename } = await downloadFile(`/exercises/${exerciseId}/starter-file`);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename ?? fallbackName;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
