import { useMemo, useState } from "react";

import type { StudyGroup } from "@/api/types";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { Modal } from "@/components/Modal";

import { STUDY_GROUP_LABELS, useAllStudents, useClassMembers, useReplaceMembers } from "./accountsApi";

type Selection = Record<string, StudyGroup | undefined>; // học viên → nhóm (undefined: không trong lớp)

/** Chọn học viên của lớp và chia nhóm thực nghiệm / đối chứng (lưu là thay toàn bộ danh sách). */
export function MembersDialog({ classId, onClose }: { classId: string; onClose: () => void }) {
  const students = useAllStudents();
  const members = useClassMembers(classId);
  const replace = useReplaceMembers(classId);
  const [filter, setFilter] = useState("");
  const [edits, setEdits] = useState<Selection>({});

  const selection = useMemo<Selection>(() => {
    const current: Selection = Object.fromEntries(
      (members.data ?? []).map((m) => [m.student_id, m.study_group]),
    );
    return { ...current, ...edits };
  }, [members.data, edits]);
  const chosen = Object.entries(selection).filter((entry): entry is [string, StudyGroup] => !!entry[1]);
  const visible = (students.data?.items ?? []).filter((s) =>
    `${s.full_name} ${s.email}`.toLowerCase().includes(filter.trim().toLowerCase()),
  );

  function set(studentId: string, group: StudyGroup | undefined) {
    setEdits((prev) => ({ ...prev, [studentId]: group }));
  }

  return (
    <Modal
      title="Học viên của lớp"
      onClose={onClose}
      busy={replace.isPending}
      wide
      footer={
        <>
          <span className="muted small spacer">Đã chọn {chosen.length} học viên</span>
          <button type="button" className="btn" onClick={onClose} disabled={replace.isPending}>
            Hủy
          </button>
          <button
            type="button"
            className="btn btn--primary"
            disabled={replace.isPending || members.isPending}
            onClick={() =>
              replace.mutate(
                chosen.map(([student_id, study_group]) => ({ student_id, study_group })),
                { onSuccess: onClose },
              )
            }
          >
            {replace.isPending ? "Đang lưu…" : "Lưu danh sách"}
          </button>
        </>
      }
    >
      <ErrorAlert error={replace.error ?? students.error ?? members.error} />
      {(students.isPending || members.isPending) && <Loading />}
      <input
        type="search"
        aria-label="Tìm học viên"
        placeholder="Tìm theo tên hoặc email"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      <div className="table-wrap section-gap--small">
        <table className="table table--compact">
          <thead>
            <tr>
              <th>Trong lớp</th>
              <th>Học viên</th>
              <th>Nhóm</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((s) => {
              const group = selection[s.id];
              return (
                <tr key={s.id}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Cho ${s.full_name} vào lớp`}
                      checked={!!group}
                      onChange={(e) => set(s.id, e.target.checked ? "experimental" : undefined)}
                    />
                  </td>
                  <td>
                    {s.full_name}
                    <div className="muted small">{s.email}</div>
                  </td>
                  <td>
                    <select
                      aria-label={`Nhóm của ${s.full_name}`}
                      value={group ?? ""}
                      disabled={!group}
                      onChange={(e) => set(s.id, e.target.value as StudyGroup)}
                    >
                      {!group && <option value="">—</option>}
                      {(Object.keys(STUDY_GROUP_LABELS) as StudyGroup[]).map((g) => (
                        <option key={g} value={g}>
                          {STUDY_GROUP_LABELS[g]}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {students.data?.items.length === 0 && (
        <p className="muted">Chưa có tài khoản học viên. Tạo ở trang Tài khoản (nhập CSV cho nhanh).</p>
      )}
    </Modal>
  );
}
