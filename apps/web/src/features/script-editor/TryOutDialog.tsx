import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { sendForm } from "@/api/client";
import type { components } from "@/api/schema";
import type { Script, ScriptVersion } from "@/api/types";
import { Alert } from "@/components/Alert";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";

import { checkTypeLabel, describeCheck } from "./checkText";

type TryOutReport = components["schemas"]["TryOutReport"];
type CheckGrade = components["schemas"]["CheckGrade"];

const MARKS = { passed: "✓", failed: "✗", not_evaluable: "?" } as const;
const STATUS_TEXT = {
  passed: "Đạt",
  failed: "Chưa đạt",
  not_evaluable: "Không chấm được trên file",
} as const;
const MAX_CELLS = 6;

function useTryOut(versionId: string) {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file, file.name);
      return sendForm<TryOutReport>("POST", `/scripts/${versionId}/try-out`, form);
    },
  });
}

function CheckLine({ grade, check }: { grade: CheckGrade; check: object | undefined }) {
  const cells =
    grade.cells.length > MAX_CELLS
      ? `${grade.cells.slice(0, MAX_CELLS).join(", ")}…`
      : grade.cells.join(", ");
  return (
    <li className={`tryout__check tryout__check--${grade.status}`}>
      <span aria-hidden="true">{MARKS[grade.status]}</span>{" "}
      {check ? describeCheck(check) : checkTypeLabel(grade.type)}
      {grade.status === "failed" && (
        <span className="muted small">
          {" "}
          — mã lỗi <code>{grade.code}</code>
          {cells && ` ở ${cells}`}
        </span>
      )}
      {grade.status === "not_evaluable" && <span className="muted small"> — {grade.detail}</span>}
    </li>
  );
}

function Report({ report, script }: { report: TryOutReport; script: Script }) {
  const current = report.steps.find((s) => s.step_id === report.current_step_id);
  const brokenGlobals = report.global_checks.filter((g) => g.status === "failed");
  return (
    <div className="stack">
      {current ? (
        <Alert
          kind="info"
          title={`Học viên đang ở bước ${String(report.steps.indexOf(current) + 1)}: ${current.title}`}
        >
          Gia sư hiện thẻ yêu cầu của bước này và chờ tín hiệu để gợi ý.
        </Alert>
      ) : (
        <Alert kind="success" title="Đã xong cả bài">
          Mọi bước đều đạt: gia sư sẽ hiện màn hình hoàn thành.
        </Alert>
      )}
      {brokenGlobals.length > 0 && (
        <Alert kind="warning" title="Gia sư sẽ nhắc ngay (dữ liệu gốc bị sửa, công thức có sẵn bị gõ đè)">
          <ul>
            {brokenGlobals.map((g) => (
              <CheckLine key={g.index} grade={g} check={script.global_checks?.[g.index]} />
            ))}
          </ul>
        </Alert>
      )}
      <ol className="tryout">
        {report.steps.map((step, n) => {
          const definition = script.steps.find((s) => s.id === step.step_id);
          return (
            <li key={step.step_id} className={`tryout__step tryout__step--${step.status}`}>
              <div className="row">
                <strong>
                  {MARKS[step.status]} Bước {n + 1}: {step.title}
                </strong>
                <span className="muted small">{STATUS_TEXT[step.status]}</span>
              </div>
              {step.status !== "passed" && (
                <ul className="tryout__checks">
                  {step.checks.map((g) => (
                    <CheckLine key={g.index} grade={g} check={definition?.checks[g.index]} />
                  ))}
                </ul>
              )}
              {step.feedback.map((f) => (
                <p key={f.code} className="tryout__feedback">
                  Gia sư nói: “{f.message}”
                </p>
              ))}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/**
 * Chấm thử kịch bản bằng file Excel thật trước khi có Desktop: giảng viên làm bài như học viên rồi tải file
 * lên, hệ thống chấm từng bước bằng đúng các điều kiện Desktop sẽ dùng.
 */
export function TryOutDialog({
  version,
  dirty,
  onClose,
}: {
  version: ScriptVersion;
  dirty: boolean;
  onClose: () => void;
}) {
  const tryOut = useTryOut(version.id);
  const [file, setFile] = useState<File | null>(null);

  return (
    <Modal
      title="Chấm thử bằng file Excel"
      onClose={onClose}
      busy={tryOut.isPending}
      wide
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={tryOut.isPending}>
            Đóng
          </button>
          <button
            type="button"
            className="btn btn--primary"
            disabled={!file || tryOut.isPending}
            onClick={() => file && tryOut.mutate(file)}
          >
            {tryOut.isPending ? "Đang chấm…" : tryOut.data ? "Chấm lại" : "Chấm"}
          </button>
        </>
      }
    >
      <ol className="small tryout__howto">
        <li>Mở file đề bằng Excel (file bạn đã tải lên khi tạo bài), làm vài bước như một học viên.</li>
        <li>Lưu file (Ctrl+S) để Excel ghi kết quả công thức, rồi chọn file đó ở đây và bấm Chấm.</li>
        <li>Sửa tiếp trong Excel, lưu, bấm Chấm lại để xem gia sư phản ứng thế nào ở từng bước.</li>
      </ol>
      {dirty && (
        <Alert kind="warning">Đang có thay đổi chưa lưu: chấm theo bản {version.revision} đã lưu.</Alert>
      )}
      <Field label="File bài làm (.xlsx)">
        {(p) => (
          <input
            {...p}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              tryOut.reset();
            }}
          />
        )}
      </Field>
      <ErrorAlert error={tryOut.error} />
      {tryOut.data && <Report report={tryOut.data} script={version.content} />}
    </Modal>
  );
}
