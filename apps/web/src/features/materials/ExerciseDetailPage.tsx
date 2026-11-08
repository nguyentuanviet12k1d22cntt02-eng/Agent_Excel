import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { errorMessage } from "@/api/errors";
import { Alert } from "@/components/Alert";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { GenerationPanel } from "@/features/generation/GenerationPanel";

import { ExerciseEditDialog } from "./ExerciseEditDialog";
import { ExerciseInfoCard } from "./ExerciseInfoCard";
import { useDeleteExercise, useExercise } from "./materialsApi";

export function ExerciseDetailPage() {
  const { exerciseId = "" } = useParams();
  const navigate = useNavigate();
  const exercise = useExercise(exerciseId);
  const remove = useDeleteExercise();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (exercise.isPending) return <Loading />;
  if (exercise.error) return <ErrorAlert error={exercise.error} />;
  const data = exercise.data;

  return (
    <>
      <PageHeader
        back={<Link to="/exercises">← Bài tập</Link>}
        title={data.title}
        subtitle={
          <>
            Mã bài <code>{data.code}</code> · sheet <strong>{data.sheet_name}</strong>
          </>
        }
        actions={
          <>
            <button type="button" className="btn" onClick={() => setEditing(true)}>
              Sửa thông tin
            </button>
            <button
              type="button"
              className="btn btn--danger"
              onClick={() => {
                remove.reset();
                setDeleting(true);
              }}
            >
              Xóa bài
            </button>
          </>
        }
      />
      {(data.warnings?.length ?? 0) > 0 && (
        <Alert kind="warning" title="Cần xem lại file đề và đáp án">
          <ul>
            {data.warnings?.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Alert>
      )}
      <ExerciseInfoCard exercise={data} />
      <GenerationPanel exercise={data} />

      {editing && <ExerciseEditDialog exercise={data} onClose={() => setEditing(false)} />}
      {deleting && (
        <ConfirmDialog
          title="Xóa bài tập"
          confirmLabel="Xóa bài"
          danger
          busy={remove.isPending}
          error={remove.error ? errorMessage(remove.error) : null}
          onCancel={() => setDeleting(false)}
          onConfirm={() =>
            remove.mutate(data.id, {
              onSuccess: () => void navigate("/exercises", { replace: true }),
            })
          }
        >
          <p>
            Xóa bài <strong>{data.title}</strong> cùng file đề, file đáp án và mọi bản kịch bản? Bài đã có học
            viên làm thì không xóa được.
          </p>
        </ConfirmDialog>
      )}
    </>
  );
}
