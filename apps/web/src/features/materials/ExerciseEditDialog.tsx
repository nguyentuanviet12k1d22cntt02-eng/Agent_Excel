import { useState, type SubmitEvent } from "react";

import type { Exercise } from "@/api/types";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";

import { useUpdateExercise } from "./materialsApi";
import { TextbookPicker } from "./TextbookPicker";

/** Sửa tên, đề bài, giáo trình liên quan. Mã bài và file không đổi (đổi file thì tạo bài mới). */
export function ExerciseEditDialog({ exercise, onClose }: { exercise: Exercise; onClose: () => void }) {
  const update = useUpdateExercise(exercise.id);
  const [title, setTitle] = useState(exercise.title);
  const [promptText, setPromptText] = useState(exercise.prompt_text ?? "");
  const [textbookIds, setTextbookIds] = useState<string[]>(exercise.textbook_ids ?? []);

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    update.mutate(
      { title: title.trim(), prompt_text: promptText, textbook_ids: textbookIds },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal
      title="Sửa thông tin bài"
      onClose={onClose}
      busy={update.isPending}
      wide
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={update.isPending}>
            Hủy
          </button>
          <button
            type="submit"
            form="exercise-edit"
            className="btn btn--primary"
            disabled={update.isPending || !title.trim()}
          >
            {update.isPending ? "Đang lưu…" : "Lưu"}
          </button>
        </>
      }
    >
      <form id="exercise-edit" className="stack" onSubmit={handleSubmit}>
        <ErrorAlert error={update.error} />
        <Field label="Tên bài">
          {(p) => (
            <input
              {...p}
              type="text"
              required
              maxLength={200}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          )}
        </Field>
        <Field label="Đề bài dạng chữ">
          {(p) => (
            <textarea
              {...p}
              rows={5}
              maxLength={20000}
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
            />
          )}
        </Field>
        <TextbookPicker value={textbookIds} onChange={setTextbookIds} />
        <p className="muted small">
          Muốn đổi file đề hoặc file đáp án thì tạo bài mới: kịch bản đã sinh gắn với đúng hai file cũ.
        </p>
      </form>
    </Modal>
  );
}
