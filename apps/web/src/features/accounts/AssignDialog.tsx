import { useState, type SubmitEvent } from "react";

import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";
import { useExercises } from "@/features/materials/materialsApi";

import { useAssignExercise, useClasses } from "./accountsApi";

/**
 * Giao bài cho lớp (FR-W12). Mở từ trang lớp (chọn bài) hoặc trang bài (chọn lớp). Giao lại bài đã giao thì
 * chỉ đổi hạn nộp.
 */
export function AssignDialog({
  classId,
  exerciseId,
  onClose,
}: {
  classId?: string;
  exerciseId?: string;
  onClose: () => void;
}) {
  const assign = useAssignExercise();
  const classes = useClasses();
  const exercises = useExercises("");
  const [chosenClass, setChosenClass] = useState(classId ?? "");
  const [chosenExercise, setChosenExercise] = useState(exerciseId ?? "");
  const [due, setDue] = useState("");
  const published = exercises.data?.find((e) => e.id === chosenExercise)?.published_version;

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    assign.mutate(
      {
        classId: chosenClass,
        exerciseId: chosenExercise,
        // Ô datetime-local là giờ máy người dùng: đổi sang ISO có múi giờ trước khi gửi
        dueAt: due ? new Date(due).toISOString() : undefined,
      },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal
      title="Giao bài cho lớp"
      onClose={onClose}
      busy={assign.isPending}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={assign.isPending}>
            Hủy
          </button>
          <button
            type="submit"
            form="assign-exercise"
            className="btn btn--primary"
            disabled={!chosenClass || !chosenExercise || assign.isPending}
          >
            {assign.isPending ? "Đang giao…" : "Giao bài"}
          </button>
        </>
      }
    >
      <form id="assign-exercise" className="stack" onSubmit={handleSubmit} noValidate>
        <ErrorAlert error={assign.error} />
        {!classId && (
          <Field label="Lớp">
            {(p) => (
              <select {...p} value={chosenClass} onChange={(e) => setChosenClass(e.target.value)}>
                <option value="">— Chọn lớp —</option>
                {classes.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            )}
          </Field>
        )}
        {!exerciseId && (
          <Field label="Bài tập">
            {(p) => (
              <select {...p} value={chosenExercise} onChange={(e) => setChosenExercise(e.target.value)}>
                <option value="">— Chọn bài —</option>
                {exercises.data?.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.title} ({e.code})
                  </option>
                ))}
              </select>
            )}
          </Field>
        )}
        {chosenExercise && !published && exercises.data && (
          <p className="text-warning small">
            Bài chưa phát hành kịch bản: học viên thấy bài nhưng chưa làm được với gia sư cho tới khi phát
            hành.
          </p>
        )}
        <Field label="Hạn hoàn thành (tùy chọn)">
          {(p) => <input {...p} type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} />}
        </Field>
      </form>
    </Modal>
  );
}
