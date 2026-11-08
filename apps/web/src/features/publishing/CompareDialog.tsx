import { useMemo } from "react";

import type { ScriptVersionSummary } from "@/api/types";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { Modal } from "@/components/Modal";
import { useScriptVersion } from "@/features/script-editor/scriptApi";

import { changedSteps, diffScripts } from "./diffScripts";

const KIND_LABELS = { added: "Thêm", removed: "Bỏ", changed: "Sửa" } as const;

/** Khác biệt giữa hai revision theo từng trường (FR-W09). */
export function CompareDialog({
  before,
  after,
  onClose,
}: {
  before: ScriptVersionSummary;
  after: ScriptVersionSummary;
  onClose: () => void;
}) {
  const a = useScriptVersion(before.id);
  const b = useScriptVersion(after.id);
  const changes = useMemo(
    () => (a.data && b.data ? diffScripts(a.data.content, b.data.content) : []),
    [a.data, b.data],
  );

  return (
    <Modal
      title={`So sánh bản ${String(before.revision)} → bản ${String(after.revision)}`}
      onClose={onClose}
      wide
    >
      {(a.isPending || b.isPending) && <Loading />}
      <ErrorAlert error={a.error ?? b.error} />
      {a.data && b.data && (
        <>
          <p className="muted small">
            {changes.length === 0
              ? "Hai bản giống nhau về nội dung."
              : `${String(changes.length)} chỗ khác, ở ${String(changedSteps(changes))}/${String(a.data.content.steps.length)} bước.`}
          </p>
          {changes.length > 0 && (
            <div className="table-wrap">
              <table className="table table--compact diff">
                <thead>
                  <tr>
                    <th>Vị trí</th>
                    <th>Bản {before.revision}</th>
                    <th>Bản {after.revision}</th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((c) => (
                    <tr key={c.path}>
                      <td>
                        <span className={`badge diff__kind diff__kind--${c.kind}`}>
                          {KIND_LABELS[c.kind]}
                        </span>{" "}
                        {c.where}
                      </td>
                      <td className="diff__before">{c.before ?? "—"}</td>
                      <td className="diff__after">{c.after ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
