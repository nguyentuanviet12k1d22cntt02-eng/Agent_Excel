import type { GlobalCheck, Script, Skill } from "@/api/types";
import { Field } from "@/components/Field";

import { ChecksTable } from "./ChecksTable";
import { issueAt, useEditor } from "./editorContext";
import { removeAt, replaceAt } from "./useScriptDraft";

const SKILL_LABELS: Record<Skill, string> = {
  data_entry: "Nhập dữ liệu",
  cell_formatting: "Định dạng ô",
  number_formatting: "Định dạng số",
  sheet_structure: "Cấu trúc trang tính",
  page_setup: "Thiết lập trang in",
  formula_basics: "Công thức cơ bản",
  function_math_stat: "Hàm toán, thống kê",
  function_logical: "Hàm logic",
  function_text: "Hàm chuỗi",
  function_datetime: "Hàm ngày giờ",
  function_lookup: "Hàm tra cứu",
  sort: "Sắp xếp",
  filter: "Lọc",
  chart: "Biểu đồ",
};

/** Tên bài, mô tả ngắn, kỹ năng (cho luật giảm dần trợ giúp theo kỹ năng). */
export function ExerciseInfoPanel() {
  const { draft, issues, update, readOnly } = useEditor();
  const exercise = draft.exercise;
  const skills = exercise.skills ?? [];

  function setExercise(patch: Partial<Script["exercise"]>) {
    update((s) => ({ ...s, exercise: { ...s.exercise, ...patch } }));
  }

  return (
    <section className="card">
      <div className="card__title">
        <h2>Thông tin bài trong kịch bản</h2>
      </div>
      <div className="stack">
        <Field label="Tên bài hiện cho học viên" error={issueAt(issues, "/exercise/title")}>
          {(p) => (
            <input
              {...p}
              type="text"
              maxLength={200}
              value={exercise.title}
              readOnly={readOnly}
              onChange={(e) => setExercise({ title: e.target.value })}
            />
          )}
        </Field>
        <Field label="Học viên cần làm gì (1–3 câu)" error={issueAt(issues, "/exercise/summary")}>
          {(p) => (
            <textarea
              {...p}
              rows={3}
              maxLength={1000}
              value={exercise.summary ?? ""}
              readOnly={readOnly}
              onChange={(e) => setExercise({ summary: e.target.value === "" ? undefined : e.target.value })}
            />
          )}
        </Field>
        <fieldset className="fieldset">
          <legend>Kỹ năng</legend>
          <div className="skills">
            {(Object.keys(SKILL_LABELS) as Skill[]).map((skill) => (
              <label key={skill} className="checkbox small">
                <input
                  type="checkbox"
                  checked={skills.includes(skill)}
                  disabled={readOnly}
                  onChange={(e) => {
                    const next = e.target.checked ? [...skills, skill] : skills.filter((s) => s !== skill);
                    setExercise({ skills: next.length > 0 ? next : undefined });
                  }}
                />
                {SKILL_LABELS[skill]}
              </label>
            ))}
          </div>
        </fieldset>
      </div>
    </section>
  );
}

/** Điều kiện toàn bài: bảo vệ dữ liệu gốc, công thức có sẵn (gõ đè thì gia sư nhắc Ctrl+Z ngay). */
export function GlobalChecksPanel() {
  const { draft, saved, update } = useEditor();
  const checks = draft.global_checks ?? [];
  const fresh = JSON.stringify(saved.global_checks ?? []) === JSON.stringify(checks);
  return (
    <section className="card">
      <div className="card__title">
        <h2>Điều kiện toàn bài</h2>
      </div>
      <p className="muted small">
        Kiểm ở mọi bước. Không đạt (học viên sửa dữ liệu gốc, gõ đè công thức có sẵn) thì gia sư phản hồi
        ngay. Phải đạt trên cả file đề và file đáp án.
      </p>
      {checks.length === 0 ? (
        <p className="muted">Không có.</p>
      ) : (
        <ChecksTable
          checks={checks}
          stepId={null}
          basePath="/global_checks"
          fresh={fresh}
          onChange={(next) =>
            update((s) => ({ ...s, global_checks: next.length > 0 ? (next as GlobalCheck[]) : undefined }))
          }
        />
      )}
    </section>
  );
}

/** Lời chúc khi hoàn thành bài và tiêu chí của giảng viên đối chiếu với các bước. */
export function CompletionPanel() {
  const { draft, issues, update, readOnly } = useEditor();
  const completion = draft.completion ?? {};
  const criteria = completion.criteria ?? [];

  function setCompletion(patch: Partial<NonNullable<Script["completion"]>>) {
    update((s) => {
      const next = { ...(s.completion ?? {}), ...patch };
      const empty = !next.message && (next.criteria?.length ?? 0) === 0;
      return { ...s, completion: empty ? undefined : next };
    });
  }

  function setCriterion(i: number, patch: Partial<(typeof criteria)[number]>) {
    const current = criteria[i];
    if (current) setCompletion({ criteria: replaceAt(criteria, i, { ...current, ...patch }) });
  }

  return (
    <section className="card">
      <div className="card__title">
        <h2>Màn hình hoàn thành</h2>
        <button
          type="button"
          className="btn btn--small"
          disabled={readOnly}
          onClick={() =>
            setCompletion({ criteria: [...criteria, { text: "", step_ids: [draft.steps[0]?.id ?? ""] }] })
          }
        >
          Thêm tiêu chí
        </button>
      </div>
      <div className="stack">
        <Field label="Lời chúc khi xong bài" error={issueAt(issues, "/completion/message")}>
          {(p) => (
            <textarea
              {...p}
              rows={2}
              maxLength={600}
              value={completion.message ?? ""}
              readOnly={readOnly}
              onChange={(e) => setCompletion({ message: e.target.value === "" ? undefined : e.target.value })}
            />
          )}
        </Field>
        {criteria.map((criterion, i) => (
          <div key={i} className="criterion">
            <Field
              label={`Tiêu chí ${String(i + 1)}`}
              error={issueAt(issues, `/completion/criteria/${String(i)}/text`)}
            >
              {(p) => (
                <input
                  {...p}
                  type="text"
                  maxLength={600}
                  value={criterion.text}
                  readOnly={readOnly}
                  onChange={(e) => setCriterion(i, { text: e.target.value })}
                />
              )}
            </Field>
            <div className="row small">
              <span className="muted">Đạt khi xong các bước:</span>
              {draft.steps.map((step, n) => (
                <label key={step.id} className="checkbox">
                  <input
                    type="checkbox"
                    checked={criterion.step_ids.includes(step.id)}
                    disabled={readOnly}
                    onChange={(e) =>
                      setCriterion(i, {
                        step_ids: e.target.checked
                          ? [...criterion.step_ids, step.id]
                          : criterion.step_ids.filter((id) => id !== step.id),
                      })
                    }
                  />
                  {n + 1}
                </label>
              ))}
              <span className="spacer" />
              <button
                type="button"
                className="btn btn--ghost btn--small"
                disabled={readOnly}
                onClick={() => setCompletion({ criteria: removeAt(criteria, i) })}
              >
                Xóa tiêu chí
              </button>
            </div>
            {issueAt(issues, `/completion/criteria/${String(i)}/step_ids`) && (
              <span className="field__error">
                {issueAt(issues, `/completion/criteria/${String(i)}/step_ids`)}
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

const REFERENCE_KINDS = {
  textbook: "Giáo trình",
  exercise_file: "Trong file bài tập",
  teacher_note: "Ghi chú",
};

/** Nguồn trích dẫn (đoạn giáo trình RAG) và bước nào dùng nó (FR-W07). */
export function ReferencesPanel() {
  const { draft } = useEditor();
  const references = draft.references ?? [];
  return (
    <section className="card">
      <div className="card__title">
        <h2>Nguồn trích dẫn</h2>
      </div>
      {references.length === 0 && (
        <p className="muted">
          Kịch bản không trích giáo trình (bài chưa gắn giáo trình, hoặc không tìm thấy đoạn phù hợp).
        </p>
      )}
      {references.map((ref) => {
        const usedBy = draft.steps
          .map((s, n) => ({ n, s }))
          .filter(
            ({ s }) =>
              (s.reference_ids ?? []).includes(ref.id) ||
              s.hints.some((h) => (h.reference_ids ?? []).includes(ref.id)),
          )
          .map(({ n }) => n + 1);
        return (
          <blockquote key={ref.id} className="quote">
            <div className="row">
              <span className="badge">{REFERENCE_KINDS[ref.kind]}</span>
              <strong>{ref.title}</strong>
              {ref.location && <span className="muted small">{ref.location}</span>}
            </div>
            {ref.quote && <p className="prewrap small">{ref.quote}</p>}
            <span className="muted small">
              {usedBy.length > 0 ? `Dùng ở bước ${usedBy.join(", ")}` : "Chưa bước nào dùng"}
            </span>
          </blockquote>
        );
      })}
    </section>
  );
}
