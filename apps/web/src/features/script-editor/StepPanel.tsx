import { useState } from "react";

import type { Step } from "@/api/types";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Field } from "@/components/Field";

import { ChecksTable } from "./ChecksTable";
import { issueAt, stepChecksUnchanged, useEditor } from "./editorContext";
import { FeedbackSection, SignalsSection } from "./FeedbackSection";
import { HintsSection } from "./HintsSection";
import { JsonEditDialog } from "./JsonEditDialog";
import { TargetsSection } from "./TargetsSection";

export function StepPanel({
  step,
  index,
  total,
  onMove,
  onRemove,
}: {
  step: Step;
  index: number;
  total: number;
  onMove: (delta: -1 | 1) => void;
  onRemove: () => void;
}) {
  const { saved, issues, updateStep, readOnly } = useEditor();
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [editingJson, setEditingJson] = useState(false);
  const base = `/steps/${String(index)}`;

  return (
    <div className="stack">
      <div className="row row--between">
        <h2>
          Bước {index + 1}/{total} <code className="muted small">{step.id}</code>
        </h2>
        <div className="row">
          <button
            type="button"
            className="btn btn--small"
            disabled={readOnly || index === 0}
            onClick={() => onMove(-1)}
          >
            ↑ Lên
          </button>
          <button
            type="button"
            className="btn btn--small"
            disabled={readOnly || index === total - 1}
            onClick={() => onMove(1)}
          >
            ↓ Xuống
          </button>
          <button type="button" className="btn btn--small" onClick={() => setEditingJson(true)}>
            JSON của bước
          </button>
          <button
            type="button"
            className="btn btn--small btn--danger"
            disabled={readOnly || total <= 1}
            onClick={() => setConfirmRemove(true)}
          >
            Xóa bước
          </button>
        </div>
      </div>

      <section className="card">
        <div className="stack">
          <Field label="Tên bước" error={issueAt(issues, `${base}/title`)}>
            {(p) => (
              <input
                {...p}
                type="text"
                maxLength={120}
                value={step.title}
                readOnly={readOnly}
                onChange={(e) => updateStep(index, (s) => ({ ...s, title: e.target.value }))}
              />
            )}
          </Field>
          <Field
            label="Thẻ yêu cầu"
            hint="Nói học viên phải đạt gì, không nói cách làm. Luôn hiện khi học viên đang ở bước này."
            error={issueAt(issues, `${base}/task`)}
          >
            {(p) => (
              <textarea
                {...p}
                rows={3}
                maxLength={600}
                value={step.task}
                readOnly={readOnly}
                onChange={(e) => updateStep(index, (s) => ({ ...s, task: e.target.value }))}
              />
            )}
          </Field>
        </div>
      </section>

      <TargetsSection step={step} index={index} />
      <HintsSection step={step} index={index} />

      <section className="card" aria-labelledby={`checks-${step.id}`}>
        <div className="card__title">
          <h3 id={`checks-${step.id}`}>Điều kiện kiểm chứng</h3>
        </div>
        <p className="muted small">
          Bước đạt khi mọi điều kiện đạt. Điều kiện do hệ thống suy ra từ file đáp án; tự kiểm cho biết điều
          kiện đạt trên file đáp án và chưa đạt trên file đề.
        </p>
        {issueAt(issues, `${base}/checks`) && (
          <p className="field__error">{issueAt(issues, `${base}/checks`)}</p>
        )}
        <ChecksTable
          checks={step.checks}
          stepId={step.id}
          basePath={`${base}/checks`}
          fresh={stepChecksUnchanged(saved, step)}
          onChange={(checks) => updateStep(index, (s) => ({ ...s, checks }))}
        />
      </section>

      <FeedbackSection step={step} index={index} />
      <SignalsSection step={step} index={index} />

      {confirmRemove && (
        <ConfirmDialog
          title="Xóa bước"
          confirmLabel="Xóa bước"
          danger
          onCancel={() => setConfirmRemove(false)}
          onConfirm={() => {
            setConfirmRemove(false);
            onRemove();
          }}
        >
          <p>
            Xóa bước <strong>{step.title}</strong>? Thay đổi chỉ được ghi khi bấm “Lưu thành bản mới”.
          </p>
        </ConfirmDialog>
      )}
      {editingJson && (
        <JsonEditDialog
          title={`JSON của bước ${String(index + 1)}`}
          value={step}
          hint="Sửa những phần biểu mẫu chưa có ô riêng (ví dụ nút Ribbon, kỹ năng của bước). Lược đồ: schemas/tutor-script/v1."
          onClose={() => setEditingJson(false)}
          onApply={(value) => {
            if (!readOnly) updateStep(index, () => value as Step);
          }}
        />
      )}
    </div>
  );
}
