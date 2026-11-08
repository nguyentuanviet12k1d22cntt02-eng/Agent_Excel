import type { Feedback, Step, StepSignals } from "@/api/types";

import { issueAt, useEditor } from "./editorContext";
import { stepCodes } from "./scriptSchema";
import { removeAt, replaceAt } from "./useScriptDraft";

/** Phản hồi riêng theo mã lỗi hay gặp, và tín hiệu (thời gian chờ, cấp gợi ý tự đưa, mã phản hồi ngay). */
export function FeedbackSection({ step, index }: { step: Step; index: number }) {
  const { issues, updateStep, readOnly } = useEditor();
  const feedback = step.feedback ?? [];
  const codes = stepCodes(step);
  const base = `/steps/${String(index)}/feedback`;

  function setFeedback(next: Feedback[]) {
    updateStep(index, (s) => ({ ...s, feedback: next.length > 0 ? next : undefined }));
  }

  function change(i: number, patch: Partial<Feedback>) {
    const current = feedback[i];
    if (current) setFeedback(replaceAt(feedback, i, { ...current, ...patch }));
  }

  const unused = codes.find((c) => !feedback.some((f) => f.code === c));
  return (
    <section className="card" aria-labelledby={`feedback-${step.id}`}>
      <div className="card__title">
        <h3 id={`feedback-${step.id}`}>Phản hồi theo lỗi hay gặp</h3>
        <button
          type="button"
          className="btn btn--small"
          disabled={readOnly || !unused}
          onClick={() =>
            unused && setFeedback([...feedback, { code: unused, message: "", severity: "error" }])
          }
        >
          Thêm phản hồi
        </button>
      </div>
      {feedback.length === 0 && (
        <p className="muted small">Chưa có. Không có phản hồi riêng thì gia sư dùng gợi ý theo cấp.</p>
      )}
      {feedback.map((item, i) => {
        const options = codes.includes(item.code) ? codes : [item.code, ...codes];
        const error = issueAt(issues, `${base}/${String(i)}/message`);
        return (
          <div key={i} className="feedback-row">
            <div className="row">
              <label className="small" htmlFor={`fb-code-${step.id}-${String(i)}`}>
                Khi gặp lỗi
              </label>
              <select
                id={`fb-code-${step.id}-${String(i)}`}
                value={item.code}
                disabled={readOnly}
                onChange={(e) => change(i, { code: e.target.value })}
              >
                {options.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
              <select
                aria-label={`Mức của phản hồi ${String(i + 1)}`}
                value={item.severity}
                disabled={readOnly}
                onChange={(e) => change(i, { severity: e.target.value as Feedback["severity"] })}
              >
                <option value="error">Chưa đạt</option>
                <option value="info">Chấp nhận, nhắc nhẹ</option>
              </select>
              <span className="spacer" />
              <button
                type="button"
                className="btn btn--ghost btn--small"
                aria-label={`Xóa phản hồi ${String(i + 1)}`}
                disabled={readOnly}
                onClick={() => setFeedback(removeAt(feedback, i))}
              >
                Xóa
              </button>
            </div>
            <textarea
              aria-label={`Lời nhắn khi gặp lỗi ${item.code}`}
              rows={2}
              maxLength={600}
              value={item.message}
              readOnly={readOnly}
              aria-invalid={!!error}
              onChange={(e) => change(i, { message: e.target.value })}
            />
            {error && <span className="field__error">{error}</span>}
          </div>
        );
      })}
    </section>
  );
}

const AUTO_LEVELS = [
  { value: "", label: "Mặc định (theo luật gợi ý)" },
  { value: "1", label: "Tối đa cấp 1" },
  { value: "2", label: "Tối đa cấp 2" },
  { value: "3", label: "Tối đa cấp 3" },
  { value: "4", label: "Tới cấp 4" },
];

export function SignalsSection({ step, index }: { step: Step; index: number }) {
  const { issues, updateStep, readOnly } = useEditor();
  const signals = step.signals ?? {};
  const codes = stepCodes(step);
  const immediate = signals.immediate_codes ?? [];
  const base = `/steps/${String(index)}/signals`;

  function setSignals(patch: Partial<StepSignals>) {
    updateStep(index, (s) => {
      const merged: StepSignals = { ...(s.signals ?? {}), ...patch };
      // Ô bỏ trống là dùng mặc định: bỏ hẳn khóa, không ghi undefined vào kịch bản
      const next: StepSignals = {
        ...(merged.idle_seconds !== undefined && { idle_seconds: merged.idle_seconds }),
        ...(merged.max_auto_level !== undefined && { max_auto_level: merged.max_auto_level }),
        ...(merged.immediate_codes !== undefined && { immediate_codes: merged.immediate_codes }),
      };
      return { ...s, signals: Object.keys(next).length > 0 ? next : undefined };
    });
  }

  const idleError = issueAt(issues, `${base}/idle_seconds`);
  return (
    <section className="card" aria-labelledby={`signals-${step.id}`}>
      <div className="card__title">
        <h3 id={`signals-${step.id}`}>Tín hiệu và mức tự gợi ý</h3>
      </div>
      <div className="form-grid">
        <div className="field">
          <label htmlFor={`idle-${step.id}`}>Dừng bao lâu thì nhắc (giây)</label>
          <input
            id={`idle-${step.id}`}
            type="number"
            min={15}
            max={600}
            placeholder="Mặc định"
            value={signals.idle_seconds ?? ""}
            readOnly={readOnly}
            aria-invalid={!!idleError}
            onChange={(e) =>
              setSignals({ idle_seconds: e.target.value === "" ? undefined : Number(e.target.value) })
            }
          />
          {idleError && <span className="field__error">{idleError}</span>}
          <span className="field__hint">15–600 giây, bỏ trống dùng mặc định.</span>
        </div>
        <div className="field">
          <label htmlFor={`auto-${step.id}`}>Cấp gợi ý gia sư tự đưa ra</label>
          <select
            id={`auto-${step.id}`}
            value={signals.max_auto_level === undefined ? "" : String(signals.max_auto_level)}
            disabled={readOnly}
            onChange={(e) =>
              setSignals({ max_auto_level: e.target.value === "" ? undefined : Number(e.target.value) })
            }
          >
            {AUTO_LEVELS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <span className="field__hint">Cấp cao hơn chỉ hiện khi học viên bấm trợ giúp.</span>
        </div>
      </div>
      {codes.length > 0 && (
        <fieldset className="fieldset section-gap--small">
          <legend>Phản hồi ngay, không chờ (ví dụ gõ đè lên công thức)</legend>
          <div className="row">
            {codes.map((code) => (
              <label key={code} className="checkbox small">
                <input
                  type="checkbox"
                  checked={immediate.includes(code)}
                  disabled={readOnly}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...immediate, code]
                      : immediate.filter((c) => c !== code);
                    setSignals({ immediate_codes: next.length > 0 ? next : undefined });
                  }}
                />
                {code}
              </label>
            ))}
          </div>
        </fieldset>
      )}
    </section>
  );
}
