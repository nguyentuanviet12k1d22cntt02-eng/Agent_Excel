import { useState } from "react";
import { Link, useParams } from "react-router";

import { errorMessage } from "@/api/errors";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { useCurrentUser } from "@/features/auth/authContext";
import { formatDateTime } from "@/lib/format";

import {
  STUDY_GROUP_LABELS,
  useClassAssignments,
  useClasses,
  useClassMembers,
  useUnassignExercise,
} from "./accountsApi";
import { AssignDialog } from "./AssignDialog";
import { MembersDialog } from "./MembersDialog";

export function ClassDetailPage() {
  const { classId = "" } = useParams();
  const user = useCurrentUser();
  const classes = useClasses();
  const members = useClassMembers(classId);
  const assignments = useClassAssignments(classId);
  const unassign = useUnassignExercise(classId);
  const [dialog, setDialog] = useState<"members" | "assign" | null>(null);
  const [removing, setRemoving] = useState<{ id: string; title: string } | null>(null);
  const info = classes.data?.find((c) => c.id === classId);
  const isAdmin = user.role === "admin";

  if (classes.isPending) return <Loading />;
  if (!info)
    return (
      <ErrorAlert
        error={classes.error ?? new Error("Không tìm thấy lớp hoặc bạn không phụ trách lớp này.")}
      />
    );

  const counts = (members.data ?? []).reduce(
    (acc, m) => ({ ...acc, [m.study_group]: acc[m.study_group] + 1 }),
    { experimental: 0, control: 0 },
  );
  return (
    <>
      <PageHeader
        back={<Link to="/classes">← Lớp học</Link>}
        title={info.name}
        subtitle={`Giảng viên: ${info.teacher_name ?? "—"} · ${String(info.member_count ?? 0)} học viên`}
      />
      <section className="card">
        <div className="card__title">
          <h2>Học viên</h2>
          {isAdmin && (
            <button type="button" className="btn" onClick={() => setDialog("members")}>
              Sửa danh sách và nhóm
            </button>
          )}
        </div>
        <p className="muted small">
          Nhóm thực nghiệm làm bài có gia sư hướng dẫn; nhóm đối chứng chỉ ghi nhật ký, không có gợi ý (để so
          sánh công bằng). Hiện có {counts.experimental} thực nghiệm, {counts.control} đối chứng.
        </p>
        {members.isPending && <Loading />}
        <ErrorAlert error={members.error} />
        {members.data && members.data.length > 0 && (
          <div className="table-wrap">
            <table className="table table--compact">
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>Email</th>
                  <th>Nhóm</th>
                </tr>
              </thead>
              <tbody>
                {members.data.map((m) => (
                  <tr key={m.student_id}>
                    <td>{m.full_name}</td>
                    <td>{m.email}</td>
                    <td>{STUDY_GROUP_LABELS[m.study_group]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {members.data?.length === 0 && <p className="muted">Lớp chưa có học viên.</p>}
      </section>

      <section className="card">
        <div className="card__title">
          <h2>Bài đã giao</h2>
          <button type="button" className="btn btn--primary" onClick={() => setDialog("assign")}>
            Giao bài
          </button>
        </div>
        {assignments.isPending && <Loading />}
        <ErrorAlert error={assignments.error} />
        {assignments.data?.length === 0 && <p className="muted">Chưa giao bài nào.</p>}
        {assignments.data && assignments.data.length > 0 && (
          <div className="table-wrap">
            <table className="table table--compact">
              <thead>
                <tr>
                  <th>Bài</th>
                  <th>Hạn</th>
                  <th>Kịch bản</th>
                  <th className="actions">
                    <span className="sr-only">Thao tác</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {assignments.data.map((a) => (
                  <tr key={a.exercise_id}>
                    <td>
                      <Link to={`/exercises/${a.exercise_id}`}>{a.title}</Link>{" "}
                      <code className="small">{a.code}</code>
                    </td>
                    <td className="nowrap">{formatDateTime(a.due_at)}</td>
                    <td>
                      {a.published_revision != null ? (
                        `Đang phát hành bản ${String(a.published_revision)}`
                      ) : (
                        <span className="text-warning">Chưa phát hành: học viên chưa làm được</span>
                      )}
                    </td>
                    <td className="actions">
                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        onClick={() => {
                          unassign.reset();
                          setRemoving({ id: a.exercise_id, title: a.title });
                        }}
                      >
                        Gỡ
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {dialog === "members" && <MembersDialog classId={classId} onClose={() => setDialog(null)} />}
      {dialog === "assign" && <AssignDialog classId={classId} onClose={() => setDialog(null)} />}
      {removing && (
        <ConfirmDialog
          title="Gỡ bài khỏi lớp"
          confirmLabel="Gỡ bài"
          danger
          busy={unassign.isPending}
          error={unassign.error ? errorMessage(unassign.error) : null}
          onCancel={() => setRemoving(null)}
          onConfirm={() =>
            unassign.mutate(removing.id, {
              onSuccess: () => setRemoving(null),
            })
          }
        >
          <p>
            Gỡ bài <strong>{removing.title}</strong> khỏi lớp? Học viên không còn thấy bài này trong danh
            sách; tiến độ đã ghi vẫn giữ.
          </p>
        </ConfirmDialog>
      )}
    </>
  );
}
