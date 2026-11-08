import type { CellTarget, Step } from "@/api/types";

import { issueAt, useEditor } from "./editorContext";
import { removeAt, replaceAt } from "./useScriptDraft";

const ROLE_LABELS: Record<CellTarget["role"], string> = {
  target: "Học viên làm ở đây",
  source: "Dữ liệu nguồn (chỉ đọc)",
};

/** Vùng liên quan tới bước: vùng học viên phải làm (khoanh khi chỉ vị trí) và vùng dữ liệu nguồn. */
export function TargetsSection({ step, index }: { step: Step; index: number }) {
  const { issues, updateStep, setFocus, readOnly } = useEditor();
  const cells = step.targets.cells;
  const base = `/steps/${String(index)}/targets/cells`;

  function setCells(next: CellTarget[]) {
    updateStep(index, (s) => ({ ...s, targets: { ...s.targets, cells: next } }));
  }

  function change(i: number, patch: Partial<CellTarget>) {
    const current = cells[i];
    if (current) setCells(replaceAt(cells, i, { ...current, ...patch }));
  }

  return (
    <section className="card" aria-labelledby={`targets-${step.id}`}>
      <div className="card__title">
        <h3 id={`targets-${step.id}`}>Vùng liên quan</h3>
        <button
          type="button"
          className="btn btn--small"
          disabled={readOnly}
          onClick={() => setCells([...cells, { range: "A1", role: "target" }])}
        >
          Thêm vùng
        </button>
      </div>
      <p className="muted small">
        Vùng “học viên làm ở đây” được khoanh trên Excel khi gia sư chỉ vị trí và là nơi gia sư theo dõi thay
        đổi.
      </p>
      <table className="table table--compact table--form">
        <thead>
          <tr>
            <th>Vai trò</th>
            <th>Vùng</th>
            <th>Tên gọi hiện cho học viên</th>
            <th className="actions">
              <span className="sr-only">Thao tác</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {cells.map((cell, i) => {
            const rangeError = issueAt(issues, `${base}/${String(i)}/range`);
            return (
              <tr key={i}>
                <td>
                  <select
                    aria-label={`Vai trò vùng ${String(i + 1)}`}
                    value={cell.role}
                    disabled={readOnly}
                    onChange={(e) => change(i, { role: e.target.value as CellTarget["role"] })}
                  >
                    {Object.entries(ROLE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="text"
                    aria-label={`Địa chỉ vùng ${String(i + 1)}`}
                    className="input--range"
                    value={cell.range}
                    readOnly={readOnly}
                    aria-invalid={!!rangeError}
                    title={rangeError}
                    onChange={(e) => change(i, { range: e.target.value.toUpperCase().trim() })}
                    onFocus={() => setFocus({ range: cell.range, sheet: cell.sheet, label: cell.label })}
                  />
                  {cell.sheet && <div className="muted small">sheet {cell.sheet}</div>}
                  {rangeError && <div className="field__error">{rangeError}</div>}
                </td>
                <td>
                  <input
                    type="text"
                    aria-label={`Tên gọi vùng ${String(i + 1)}`}
                    maxLength={60}
                    placeholder="ví dụ: cột Số lượng"
                    value={cell.label ?? ""}
                    readOnly={readOnly}
                    onChange={(e) => change(i, { label: e.target.value || undefined })}
                  />
                </td>
                <td className="actions">
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={() => setFocus({ range: cell.range, sheet: cell.sheet, label: cell.label })}
                  >
                    Xem
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    disabled={readOnly || cells.length <= 1}
                    aria-label={`Xóa vùng ${String(i + 1)}`}
                    onClick={() => setCells(removeAt(cells, i))}
                  >
                    Xóa
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {(step.targets.ui?.length ?? 0) > 0 && (
        <div className="section-gap--small">
          <span className="muted small">Nút trên Ribbon gia sư chỉ tới: </span>
          {step.targets.ui?.map((ui) => (
            <span key={ui.control} className="chip" title={`${ui.tab ?? ""} › ${ui.control}`}>
              {ui.label ?? ui.control}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
