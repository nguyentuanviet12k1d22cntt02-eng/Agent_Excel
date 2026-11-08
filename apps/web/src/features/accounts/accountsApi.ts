/** Tài khoản, lớp học, nhóm thực nghiệm, giao bài (FR-W02, FR-W12). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, sendForm, unwrap } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { components } from "@/api/schema";
import type { Role, StudyGroup, UserCreate } from "@/api/types";

export type ImportResult = components["schemas"]["UserImportResult"];
export const PAGE_SIZE = 50;
/** Chọn học viên cho lớp: một lớp ở trung tâm vài chục học viên, lấy một lần tối đa 200 (giới hạn API). */
const ALL_STUDENTS = 200;

export function useUsers(role: Role | undefined, page = 1, pageSize = PAGE_SIZE) {
  return useQuery({
    queryKey: [...queryKeys.users, role ?? "all", page, pageSize],
    queryFn: () =>
      unwrap(
        api.GET("/users", { params: { query: { page, page_size: pageSize, ...(role ? { role } : {}) } } }),
      ),
  });
}

export function useAllStudents() {
  return useUsers("student", 1, ALL_STUDENTS);
}

export function useCreateUser() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: UserCreate) => unwrap(api.POST("/users", { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.users }),
  });
}

export function useImportUsers() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file, file.name);
      return sendForm<ImportResult>("POST", "/users/import", form);
    },
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.users }),
  });
}

export function useClasses() {
  return useQuery({ queryKey: queryKeys.classes, queryFn: () => unwrap(api.GET("/classes")) });
}

export interface ClassForm {
  name: string;
  teacher_id: string;
  starts_on?: string;
  ends_on?: string;
}

export function useCreateClass() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ClassForm) => unwrap(api.POST("/classes", { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.classes }),
  });
}

const classPath = (classId: string) => ({ path: { class_id: classId } });

export function useClassMembers(classId: string) {
  return useQuery({
    queryKey: [...queryKeys.classes, classId, "members"],
    queryFn: () => unwrap(api.GET("/classes/{class_id}/members", { params: classPath(classId) })),
  });
}

export function useReplaceMembers(classId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (members: { student_id: string; study_group: StudyGroup }[]) =>
      unwrap(api.PUT("/classes/{class_id}/members", { params: classPath(classId), body: members })),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.classes }),
  });
}

export function useClassAssignments(classId: string) {
  return useQuery({
    queryKey: [...queryKeys.classes, classId, "exercises"],
    queryFn: () => unwrap(api.GET("/classes/{class_id}/exercises", { params: classPath(classId) })),
  });
}

export function useAssignExercise() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ classId, exerciseId, dueAt }: { classId: string; exerciseId: string; dueAt?: string }) =>
      unwrap(
        api.POST("/classes/{class_id}/exercises", {
          params: classPath(classId),
          body: { exercise_id: exerciseId, ...(dueAt ? { due_at: dueAt } : {}) },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.classes }),
  });
}

export function useUnassignExercise(classId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (exerciseId: string) =>
      unwrap(
        api.DELETE("/classes/{class_id}/exercises/{exercise_id}", {
          params: { path: { class_id: classId, exercise_id: exerciseId } },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.classes }),
  });
}

export const STUDY_GROUP_LABELS: Record<StudyGroup, string> = {
  experimental: "Thực nghiệm (có gia sư)",
  control: "Đối chứng (chỉ ghi nhật ký)",
};
