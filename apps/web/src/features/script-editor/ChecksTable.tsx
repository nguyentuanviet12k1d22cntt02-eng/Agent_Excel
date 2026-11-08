import { useState } from "react";

import type { Check, GlobalCheck } from "@/api/types";

import { checkRange, checkTypeLabel, describeCheck } from "./checkText";
import { reportForCheck, useEditor } from "./editorContext";
import { JsonEditDialog } from "./JsonEditDialog";
import type { ScriptIssue } from "./scriptSchema";

type AnyCheck = Check | GlobalCheck;

function SelfCheckCell({
  stepId,
  index,
  fresh,
  global,
}: {
  stepId: string | null;
  index: number;
  fresh: boolean;
  global: boolean;
}) {
  const { report } = useEditor();
  if (!fresh) return <span className="muted small">Đã sửa: lưu để tự kiểm lại</span>;
  const result = reportForCheck(report, stepId, index);
  if (!result) return <span className="muted small">—</span>;
  // Điều kiện của bước: phải đạt trên đáp án, chưa đạt trên đề. Điều kiện toàn bài: đạt trên cả hai.
  const starterOk = global ? !result.fails_on_starter : result.fails_on_starter;
  return (
    <span className="selfcheck">
      <span className={result.passes_on_solution ? "ok" : "bad"}>
        {result.passes_on_solution ? "✓" : "✗"} đáp án
      </span>
      <span className={starterOk ? "ok" : "warn"} title={result.code_on_starter ?? undefined}>
        {starterOk ? "✓" : "!"} đề{!global && result.code_on_starter ? ` (${result.code_on_starter})` : ""}
      </span>
    </span>
  );
}

/** Bảng điều kiện kiểm chứng: câu mô tả, kết quả tự kiểm, xem vùng trên lưới, sửa JSON, xóa. */
export function ChecksTable({
  checks,
  stepId,
  basePath,
  fresh,
  onChange,
}: {
  checks: AnyCheck[];
  stepId: string | null;
  basePath: string;
  fresh: boolean;
  onChange: (checks: AnyCheck[]) => void;
}) {
  const { issues, setFocus, readOnly } = useEditor();
  const [editing, setEditing] = useState<number | null>(null);
  const global = stepId === null;

  function issuesOf(i: number): ScriptIssue[] {
    const path = `${basePath}/${String(i)}`;
    return issues.filter((issue) => issue.path === path || issue.path.startsWith(`${path}/`));
  }

  return (
    <>
      <table className="table table--compact">
        <thead>
          <tr>
            <th>#</th>
            <th>Loại</th>
            <th>Nội dung</th>
            <th>Tự kiểm</th>
            <th className="actions">
              <span className="sr-only">Thao tác</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check, i) => {
            const range = checkRange(check);
            const problems = issuesOf(i);
            return (
              <tr key={i} className={problems.length > 0 ? "row--invalid" : undefined}>
                <td>{i + 1}</td>
                <td className="nowrap">{checkTypeLabel(check.type)}</td>
                <td>
                  {describeCheck(check)}
                  {check.description && <div className="muted small">{check.description}</div>}
                  {problems.map((p) => (
                    <div key={p.path + p.message} className="field__error">
                      {p.where.split(" › ").slice(2).join(" › ") || "Điều kiện"}: {p.message}
                    </div>
                  ))}
                </td>
                <td>
                  <SelfCheckCell stepId={stepId} index={i} fresh={fresh} global={global} />
                </td>
                <td className="actions">
                  {range && (
                    <button
                      type="button"
                      className="btn btn--ghost btn--small"
                      onClick={() => setFocus({ ...range, label: describeCheck(check) })}
                    >
                      Xem
                    </button>
                  )}
                  <button type="button" className="btn btn--ghost btn--small" onClick={() => setEditing(i)}>
                    {readOnly ? "JSON" : "Sửa"}
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    aria-label={`Xóa điều kiện ${String(i + 1)}`}
                    disabled={readOnly}
                    onClick={() => onChange(checks.filter((_, j) => j !== i))}
                  >
                    Xóa
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {editing !== null && checks[editing] && (
        <JsonEditDialog
          title={`Điều kiện ${String(editing + 1)}: ${checkTypeLabel(checks[editing].type)}`}
          value={checks[editing]}
          hint="Tham số từng loại điều kiện: docs/thiet-ke/danh-muc-dieu-kien.md. Giá trị kỳ vọng nên lấy từ file đáp án ({“from”: “solution”}), không ghi cứng số liệu."
          onClose={() => setEditing(null)}
          onApply={(value) => {
            if (!readOnly) onChange(checks.map((c, j) => (j === editing ? (value as AnyCheck) : c)));
          }}
        />
      )}
    </>
  );
}
