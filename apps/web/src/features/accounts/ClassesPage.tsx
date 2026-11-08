import { useState, type SubmitEvent } from "react";
import { Link } from "react-router";

import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Loading } from "@/components/Loading";
import { Modal } from "@/components/Modal";
import { PageHeader } from "@/components/PageHeader";
import { useCurrentUser } from "@/features/auth/authContext";

import { useClasses, useCreateClass, useUsers } from "./accountsApi";

function formatDate(iso: string | undefined): string {
  return iso ? new Date(`${iso}T00:00:00`).toLocaleDateString("vi-VN") : "—";
}

export function ClassesPage() {
  const user = useCurrentUser();
  const classes = useClasses();
  const [creating, setCreating] = useState(false);
  const isAdmin = user.role === "admin";

  return (
    <>
      <PageHeader
        title="Lớp học"
        subtitle={
          isAdmin
            ? "Lớp, học viên, nhóm thực nghiệm / đối chứng và bài được giao."
            : "Các lớp bạn phụ trách: học viên và bài được giao."
        }
        actions={
          isAdmin && (
            <button type="button" className="btn btn--primary" onClick={() => setCreating(true)}>
              Tạo lớp
            </button>
          )
        }
      />
      {classes.isPending && <Loading />}
      <ErrorAlert error={classes.error} />
      {classes.data?.length === 0 && (
        <div className="card empty">
          <p>
            {isAdmin
              ? "Chưa có lớp nào."
              : "Bạn chưa phụ trách lớp nào. Liên hệ quản trị viên để được gán lớp."}
          </p>
        </div>
      )}
      {classes.data && classes.data.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Lớp</th>
                <th>Giảng viên</th>
                <th>Thời gian</th>
                <th>Học viên</th>
              </tr>
            </thead>
            <tbody>
              {classes.data.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/classes/${c.id}`}>{c.name}</Link>
                  </td>
                  <td>{c.teacher_name ?? "—"}</td>
                  <td className="nowrap">
                    {formatDate(c.starts_on)} – {formatDate(c.ends_on)}
                  </td>
                  <td>{c.member_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {creating && <ClassCreateDialog onClose={() => setCreating(false)} />}
    </>
  );
}

function ClassCreateDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateClass();
  const teachers = useUsers("teacher", 1, 200);
  const [name, setName] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate(
      {
        name: name.trim(),
        teacher_id: teacherId,
        ...(startsOn ? { starts_on: startsOn } : {}),
        ...(endsOn ? { ends_on: endsOn } : {}),
      },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal
      title="Tạo lớp"
      onClose={onClose}
      busy={create.isPending}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={create.isPending}>
            Hủy
          </button>
          <button
            type="submit"
            form="class-create"
            className="btn btn--primary"
            disabled={!name.trim() || !teacherId || create.isPending}
          >
            {create.isPending ? "Đang tạo…" : "Tạo lớp"}
          </button>
        </>
      }
    >
      <form id="class-create" className="stack" onSubmit={handleSubmit} noValidate>
        <ErrorAlert error={create.error} />
        <Field label="Tên lớp">
          {(p) => (
            <input
              {...p}
              type="text"
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          )}
        </Field>
        <Field
          label="Giảng viên phụ trách"
          hint={
            teachers.data?.items.length === 0
              ? "Chưa có tài khoản giảng viên: tạo ở trang Tài khoản."
              : undefined
          }
        >
          {(p) => (
            <select {...p} value={teacherId} onChange={(e) => setTeacherId(e.target.value)}>
              <option value="">— Chọn giảng viên —</option>
              {teachers.data?.items.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.full_name} ({t.email})
                </option>
              ))}
            </select>
          )}
        </Field>
        <div className="form-grid">
          <Field label="Ngày bắt đầu (tùy chọn)">
            {(p) => (
              <input {...p} type="date" value={startsOn} onChange={(e) => setStartsOn(e.target.value)} />
            )}
          </Field>
          <Field label="Ngày kết thúc (tùy chọn)">
            {(p) => <input {...p} type="date" value={endsOn} onChange={(e) => setEndsOn(e.target.value)} />}
          </Field>
        </div>
      </form>
    </Modal>
  );
}
