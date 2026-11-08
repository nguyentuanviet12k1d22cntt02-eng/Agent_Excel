import type { Reference, Step } from "@/api/types";
import { Field } from "@/components/Field";

import { issueAt, useEditor } from "./editorContext";
import { move, removeAt, replaceAt } from "./useScriptDraft";

const LEVELS = [
  { name: "Cấp 1 — Định hướng", guide: "Nhắc mục tiêu, kiến thức liên quan. Không nêu tên công cụ." },
  { name: "Cấp 2 — Gợi ý công cụ", guide: "Nêu lệnh, hàm, nút cần dùng." },
  { name: "Cấp 3 — Chỉ vị trí", guide: "Gia sư khoanh vùng ô và nút trên Excel; chữ chỉ cần ngắn gọn." },
  {
    name: "Cấp 4 — Hướng dẫn chi tiết",
    guide: "Các thao tác cụ thể theo thứ tự. Chỉ hiện khi học viên xin hoặc bế tắc lâu.",
  },
] as const;

type Hints = Step["hints"];
type DetailedHint = Hints[3];

function quotesFor(step: Step, references: Reference[] | undefined): Reference[] {
  const ids = new Set([...(step.reference_ids ?? []), ...step.hints.flatMap((h) => h.reference_ids ?? [])]);
  return (references ?? []).filter((r) => ids.has(r.id));
}

/** Bốn cấp gợi ý theo luật gợi ý (luat-goi-y.md): sửa lời, sửa các thao tác của cấp 4. */
export function HintsSection({ step, index }: { step: Step; index: number }) {
  const { draft, issues, report, updateStep, readOnly } = useEditor();
  const base = `/steps/${String(index)}/hints`;
  const textIssues = (report?.hint_text_issues ?? []).filter((i) => i.step_id === step.id);
  const quotes = quotesFor(step, draft.references);

  function setHints(change: (hints: Hints) => Hints) {
    updateStep(index, (s) => ({ ...s, hints: change(s.hints) }));
  }

  function setText(level: number, text: string) {
    setHints((hints) => hints.map((h, i) => (i === level ? { ...h, text } : h)) as Hints);
  }

  function setDetailed(change: (hint: DetailedHint) => DetailedHint) {
    setHints((hints) => [hints[0], hints[1], hints[2], change(hints[3])]);
  }

  const detailed = step.hints[3];
  return (
    <section className="card" aria-labelledby={`hints-${step.id}`}>
      <div className="card__title">
        <h3 id={`hints-${step.id}`}>Gợi ý 4 cấp</h3>
      </div>
      {textIssues.length > 0 && (
        <div className="alert alert--warning">
          <strong className="alert__title">Tự kiểm phát hiện trong chữ gợi ý của bước này</strong>
          <ul>
            {textIssues.map((issue, i) => (
              <li key={i}>
                “{issue.text}”: {issue.issue}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="hints">
        {LEVELS.map((level, i) => {
          const hint = step.hints[i];
          if (!hint) return null;
          return (
            <div key={level.name} className="hint">
              <Field
                label={level.name}
                hint={level.guide}
                error={issueAt(issues, `${base}/${String(i)}/text`)}
              >
                {(p) => (
                  <textarea
                    {...p}
                    rows={i === 3 ? 2 : 3}
                    maxLength={600}
                    value={hint.text}
                    readOnly={readOnly}
                    onChange={(e) => setText(i, e.target.value)}
                  />
                )}
              </Field>
              {i === 2 && (
                <div className="small">
                  <span className="muted">Gia sư khoanh: </span>
                  {step.hints[2].highlight.map((h, j) => (
                    <span key={j} className="chip">
                      {h.cells ? `vùng ${h.cells.range}` : `nút ${h.ui?.label ?? h.ui?.control ?? ""}`}
                    </span>
                  ))}
                </div>
              )}
              {i === 3 && (
                <ActionsEditor
                  actions={detailed.actions}
                  basePath={`${base}/3/actions`}
                  onChange={(actions) => setDetailed((h) => ({ ...h, actions }))}
                />
              )}
              {i === 3 && (
                <Field label="Cách làm khác (tùy chọn)" error={issueAt(issues, `${base}/3/alternative`)}>
                  {(p) => (
                    <textarea
                      {...p}
                      rows={2}
                      maxLength={600}
                      value={detailed.alternative ?? ""}
                      readOnly={readOnly}
                      onChange={(e) =>
                        setDetailed((h) => ({
                          ...h,
                          alternative: e.target.value === "" ? undefined : e.target.value,
                        }))
                      }
                    />
                  )}
                </Field>
              )}
            </div>
          );
        })}
      </div>
      {quotes.length > 0 && (
        <div className="quotes">
          <h4>Đoạn giáo trình được trích</h4>
          {quotes.map((q) => (
            <blockquote key={q.id}>
              <strong>{q.title}</strong>
              {q.location && <span className="muted small"> · {q.location}</span>}
              {q.quote && <p className="prewrap small">{q.quote}</p>}
            </blockquote>
          ))}
        </div>
      )}
    </section>
  );
}

function ActionsEditor({
  actions,
  basePath,
  onChange,
}: {
  actions: string[];
  basePath: string;
  onChange: (actions: string[]) => void;
}) {
  const { issues, readOnly } = useEditor();
  const listError = issueAt(issues, basePath);
  return (
    <fieldset className="fieldset actions-list">
      <legend>Các thao tác (theo thứ tự)</legend>
      {listError && <span className="field__error">{listError}</span>}
      <ol>
        {actions.map((action, i) => {
          const error = issueAt(issues, `${basePath}/${String(i)}`);
          return (
            <li key={i}>
              <div className="row">
                <input
                  type="text"
                  className="grow"
                  aria-label={`Thao tác ${String(i + 1)}`}
                  maxLength={600}
                  value={action}
                  readOnly={readOnly}
                  aria-invalid={!!error}
                  onChange={(e) => onChange(replaceAt(actions, i, e.target.value))}
                />
                <button
                  type="button"
                  className="btn btn--ghost btn--small"
                  aria-label={`Đưa thao tác ${String(i + 1)} lên`}
                  disabled={readOnly || i === 0}
                  onClick={() => onChange(move(actions, i, -1))}
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--small"
                  aria-label={`Đưa thao tác ${String(i + 1)} xuống`}
                  disabled={readOnly || i === actions.length - 1}
                  onClick={() => onChange(move(actions, i, 1))}
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--small"
                  aria-label={`Xóa thao tác ${String(i + 1)}`}
                  disabled={readOnly}
                  onClick={() => onChange(removeAt(actions, i))}
                >
                  ✕
                </button>
              </div>
              {error && <span className="field__error">{error}</span>}
            </li>
          );
        })}
      </ol>
      <button
        type="button"
        className="btn btn--small"
        disabled={readOnly || actions.length >= 10}
        onClick={() => onChange([...actions, ""])}
      >
        Thêm thao tác
      </button>
    </fieldset>
  );
}
