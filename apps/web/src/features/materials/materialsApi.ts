/** Gọi API giáo trình và bài tập (T5.3, T5.4). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, sendForm, unwrap } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Exercise, Textbook } from "@/api/types";

/** Giáo trình đang tách đoạn, lập chỉ mục: hỏi lại định kỳ tới khi xong. */
const INDEXING_POLL_MS = 2000;

export function isIndexing(textbook: Textbook): boolean {
  return textbook.status === "uploaded" || textbook.status === "indexing";
}

export function useTextbooks() {
  return useQuery({
    queryKey: queryKeys.textbooks,
    queryFn: () => unwrap(api.GET("/textbooks")),
    refetchInterval: (query) => (query.state.data?.some(isIndexing) ? INDEXING_POLL_MS : false),
  });
}

export function useUploadTextbook() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ title, file }: { title: string; file: File }) => {
      const form = new FormData();
      form.append("title", title);
      form.append("file", file, file.name);
      return sendForm<Textbook>("POST", "/textbooks", form);
    },
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.textbooks }),
  });
}

export function useDeleteTextbook() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE("/textbooks/{textbook_id}", { params: { path: { textbook_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.textbooks }),
  });
}

export function useSearchPassages(q: string) {
  return useQuery({
    queryKey: queryKeys.passages(q),
    queryFn: () => unwrap(api.GET("/textbooks/search", { params: { query: { q, limit: 5 } } })),
    enabled: q.length > 0,
  });
}

export function useExercises(q: string) {
  return useQuery({
    queryKey: queryKeys.exerciseList(q),
    queryFn: () => unwrap(api.GET("/exercises", { params: { query: q ? { q } : {} } })),
  });
}

export function useExercise(id: string) {
  return useQuery({
    queryKey: queryKeys.exercise(id),
    queryFn: () => unwrap(api.GET("/exercises/{exercise_id}", { params: { path: { exercise_id: id } } })),
  });
}

export interface ExerciseForm {
  code: string;
  title: string;
  sheetName: string;
  starterFile: File;
  solutionFile: File;
  promptFile?: File | null;
  promptText?: string;
  textbookIds: string[];
}

export function useCreateExercise() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: ExerciseForm) => {
      const form = new FormData();
      form.append("code", data.code);
      form.append("title", data.title);
      form.append("sheet_name", data.sheetName);
      form.append("starter_file", data.starterFile, data.starterFile.name);
      form.append("solution_file", data.solutionFile, data.solutionFile.name);
      if (data.promptFile) form.append("prompt_file", data.promptFile, data.promptFile.name);
      if (data.promptText) form.append("prompt_text", data.promptText);
      for (const id of data.textbookIds) form.append("textbook_ids", id);
      return sendForm<Exercise>("POST", "/exercises", form);
    },
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.exercises }),
  });
}

export interface ExercisePatch {
  title?: string;
  prompt_text?: string;
  textbook_ids?: string[];
}

export function useUpdateExercise(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ExercisePatch) =>
      unwrap(api.PATCH("/exercises/{exercise_id}", { params: { path: { exercise_id: id } }, body })),
    onSuccess: (exercise) => {
      client.setQueryData(queryKeys.exercise(id), exercise);
      return client.invalidateQueries({ queryKey: queryKeys.exercises });
    },
  });
}

export function useDeleteExercise() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE("/exercises/{exercise_id}", { params: { path: { exercise_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.exercises }),
  });
}
