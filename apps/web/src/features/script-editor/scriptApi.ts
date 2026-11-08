/** Gọi API revision kịch bản (T5.6) và xem trước trang tính cho trình sửa (T6.4). */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { components } from "@/api/schema";
import type { Script, ScriptVersion } from "@/api/types";

// Kiểu trả về của openapi-fetch đi qua bộ biến đổi Readable (bộ 4 cấp gợi ý thành mảng thường) và kiểu
// TutorScript có thêm khóa "$defs" (xem api/types.ts): ép về kiểu kịch bản ở đúng một chỗ này.
const asVersion = (data: unknown) => data as ScriptVersion;
const asContent = (script: Script) => script as unknown as components["schemas"]["TutorScript"];

export type PreviewFile = "starter" | "solution";

export function useScriptVersion(versionId: string) {
  return useQuery({
    queryKey: queryKeys.script(versionId),
    queryFn: async () =>
      asVersion(
        await unwrap(api.GET("/scripts/{version_id}", { params: { path: { version_id: versionId } } })),
      ),
  });
}

export function useSheetPreview(
  exerciseId: string | undefined,
  file: PreviewFile,
  sheet: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.sheetPreview(exerciseId ?? "", file, sheet ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/exercises/{exercise_id}/sheet-preview", {
          params: { path: { exercise_id: exerciseId ?? "" }, query: { file, ...(sheet ? { sheet } : {}) } },
        }),
      ),
    enabled: !!exerciseId,
    staleTime: Infinity, // file đề, đáp án không đổi sau khi tạo bài
    placeholderData: keepPreviousData,
  });
}

/** Lưu bản sửa thành revision mới (nháp); Backend kiểm lược đồ, tham chiếu chéo và chạy tự kiểm. */
export function useSaveScript(exerciseId: string, parentVersionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (content: Script) =>
      asVersion(
        await unwrap(
          api.POST("/exercises/{exercise_id}/scripts", {
            params: { path: { exercise_id: exerciseId } },
            body: { parent_version_id: parentVersionId, content: asContent(content) },
          }),
        ),
      ),
    onSuccess: (version) => {
      client.setQueryData(queryKeys.script(version.id), version);
      return client.invalidateQueries({ queryKey: queryKeys.exercise(exerciseId) });
    },
  });
}

export function useRerunSelfCheck(versionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () =>
      unwrap(api.POST("/scripts/{version_id}/self-check", { params: { path: { version_id: versionId } } })),
    onSuccess: (report) => {
      client.setQueryData<ScriptVersion>(queryKeys.script(versionId), (version) =>
        version ? { ...version, self_check_report: report } : version,
      );
    },
  });
}
