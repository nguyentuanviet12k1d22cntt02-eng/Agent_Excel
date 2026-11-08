import type { Exercise } from "@/api/types";

import { useTextbooks } from "./materialsApi";

export function ExerciseInfoCard({ exercise }: { exercise: Exercise }) {
  const textbooks = useTextbooks();
  const linked = (textbooks.data ?? []).filter((t) => exercise.textbook_ids?.includes(t.id));

  return (
    <section className="card">
      <div className="card__title">
        <h2>Thông tin bài</h2>
      </div>
      <dl className="details">
        <dt>Đề bài</dt>
        <dd>
          {exercise.prompt_text ? (
            <p className="prewrap">{exercise.prompt_text}</p>
          ) : (
            <span className="muted">Chưa nhập đề bài dạng chữ.</span>
          )}
        </dd>
        <dt>Giáo trình liên quan</dt>
        <dd>
          {linked.length > 0 ? (
            linked.map((t) => t.title).join(", ")
          ) : (
            <span className="muted">Không giới hạn (AI tìm trong mọi giáo trình đã sẵn sàng)</span>
          )}
        </dd>
      </dl>
    </section>
  );
}
