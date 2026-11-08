/** Khóa cache TanStack Query dùng chung, để sửa ở chỗ này thì làm mới đúng danh sách ở chỗ khác. */
export const queryKeys = {
  textbooks: ["textbooks"] as const,
  passages: (q: string) => ["textbooks", "search", q] as const,
  exercises: ["exercises"] as const,
  exerciseList: (q: string) => ["exercises", "list", q] as const,
  exercise: (id: string) => ["exercises", "detail", id] as const,
  scriptVersions: (exerciseId: string) => ["exercises", "detail", exerciseId, "scripts"] as const,
  generationJobs: (exerciseId: string) => ["exercises", "detail", exerciseId, "jobs"] as const,
  sheetPreview: (exerciseId: string, file: string, sheet: string) =>
    ["exercises", "detail", exerciseId, "preview", file, sheet] as const,
  script: (versionId: string) => ["scripts", versionId] as const,
  generationJob: (jobId: string) => ["generation-jobs", jobId] as const,
  users: ["users"] as const,
  classes: ["classes"] as const,
};
