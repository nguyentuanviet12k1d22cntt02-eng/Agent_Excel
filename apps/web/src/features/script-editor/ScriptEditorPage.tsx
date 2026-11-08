import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useBlocker, useLocation, useNavigate, useParams } from "react-router";

import { ApiError } from "@/api/errors";
import type { Exercise, ScriptVersion } from "@/api/types";
import { Alert } from "@/components/Alert";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { ScriptStatusBadge } from "@/components/ScriptStatusBadge";
import { useExercise } from "@/features/materials/materialsApi";
import { formatDateTime } from "@/lib/format";
import { SCRIPT_ORIGIN_LABELS } from "@/lib/scriptLabels";

import { checkRange } from "./checkText";
import { EditorContext, type EditorContextValue, type FocusRange } from "./editorContext";
import { EditorOutline } from "./EditorOutline";
import { GridPanel, type RangeMark } from "./GridPanel";
import { CompletionPanel, ExerciseInfoPanel, GlobalChecksPanel, ReferencesPanel } from "./OtherPanels";
import { useRerunSelfCheck, useSaveScript, useScriptVersion } from "./scriptApi";
import { describePath, validateScript } from "./scriptSchema";
import { sectionKey, type Section } from "./sections";
import { SelfCheckSummary } from "./SelfCheckSummary";
import { StepPanel } from "./StepPanel";
import { useScriptDraft } from "./useScriptDraft";

import "./editor.css";

interface SavedState {
  savedRevision?: number;
}

/** Lỗi Backend khi lưu: đường dẫn JSON trong kịch bản → vị trí dễ đọc. */
function SaveError({ error, script }: { error: unknown; script: unknown }) {
  if (!(error instanceof ApiError) || error.errors.length === 0) return <ErrorAlert error={error} />;
  return (
    <Alert kind="error" title={error.message}>
      <ul>
        {error.errors.map((e, i) => (
          <li key={i}>
            {e.path.startsWith("/") && e.path !== "/self_check" ? `${describePath(e.path, script)}: ` : ""}
            {e.message}
          </li>
        ))}
      </ul>
    </Alert>
  );
}

function sectionForPath(path: string): Section {
  const step = /^\/steps\/(\d+)/.exec(path)?.[1];
  if (step !== undefined) return { kind: "step", index: Number(step) };
  if (path.startsWith("/global_checks")) return { kind: "global" };
  if (path.startsWith("/completion")) return { kind: "completion" };
  return { kind: "overview" };
}

export function ScriptEditorPage() {
  const { versionId = "" } = useParams();
  const version = useScriptVersion(versionId);
  const exercise = useExercise(version.data?.exercise_id ?? "");

  if (version.isPending) return <Loading />;
  if (version.error) return <ErrorAlert error={version.error} />;
  if (exercise.error) return <ErrorAlert error={exercise.error} />;
  if (!exercise.data) return <Loading />;
  return <Editor version={version.data} exercise={exercise.data} />;
}

function Editor({ version, exercise }: { version: ScriptVersion; exercise: Exercise }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { draft, dirty, update, updateStep, moveStep, removeStep, reset } = useScriptDraft(version);
  const save = useSaveScript(exercise.id, version.id);
  const rerun = useRerunSelfCheck(version.id);
  const [section, setSection] = useState<Section>({ kind: "overview" });
  const [focus, setFocus] = useState<FocusRange | null>(null);
  const leaving = useRef(false);
  const issues = useMemo(() => validateScript(draft), [draft]);
  const savedRevision = (location.state as SavedState | null)?.savedRevision;

  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    return dirty && !leaving.current && currentLocation.pathname !== nextLocation.pathname;
  });

  // Đã sang revision vừa lưu: bật lại cảnh báo rời trang cho lần sửa tiếp theo
  useEffect(() => {
    leaving.current = false;
  }, [version.id]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => {
      window.removeEventListener("beforeunload", warn);
    };
  }, [dirty]);

  function select(next: Section) {
    setSection(next);
    setFocus(null);
  }

  function handleSave() {
    save.mutate(draft, {
      onSuccess: (saved) => {
        leaving.current = true;
        void navigate(`/scripts/${saved.id}`, {
          state: { savedRevision: saved.revision } satisfies SavedState,
        });
      },
    });
  }

  const context: EditorContextValue = {
    draft,
    saved: version.content,
    report: version.self_check_report ?? null,
    issues,
    readOnly: save.isPending,
    update,
    updateStep,
    focus,
    setFocus,
  };

  const marks = useMemo<RangeMark[]>(() => {
    const result: RangeMark[] = [];
    if (section.kind === "step") {
      for (const cell of draft.steps[section.index]?.targets.cells ?? []) {
        result.push({ range: cell.range, sheet: cell.sheet, kind: cell.role, label: cell.label });
      }
    } else if (section.kind === "global") {
      for (const check of draft.global_checks ?? []) {
        const range = checkRange(check);
        if (range) result.push({ ...range, kind: "source" });
      }
    } else {
      for (const step of draft.steps) {
        for (const cell of step.targets.cells) {
          if (cell.role === "target")
            result.push({ range: cell.range, sheet: cell.sheet, kind: "target", label: step.title });
        }
      }
    }
    if (focus) result.push({ ...focus, kind: "focus" });
    return result;
  }, [draft, section, focus]);

  let panel: ReactNode;
  const step = section.kind === "step" ? draft.steps[section.index] : undefined;
  if (section.kind === "step" && step) {
    panel = (
      <StepPanel
        key={step.id}
        step={step}
        index={section.index}
        total={draft.steps.length}
        onMove={(delta) => {
          moveStep(section.index, delta);
          select({ kind: "step", index: section.index + delta });
        }}
        onRemove={() => {
          removeStep(section.index);
          select({ kind: "overview" });
        }}
      />
    );
  } else if (section.kind === "global") {
    panel = <GlobalChecksPanel />;
  } else if (section.kind === "completion") {
    panel = <CompletionPanel />;
  } else if (section.kind === "references") {
    panel = <ReferencesPanel />;
  } else {
    panel = (
      <div className="stack">
        <SelfCheckSummary
          report={version.self_check_report ?? null}
          issues={issues}
          dirty={dirty}
          onOpenIssue={(path) => select(sectionForPath(path))}
        />
        <ExerciseInfoPanel />
      </div>
    );
  }

  return (
    <EditorContext value={context}>
      <header className="page-header">
        <div>
          <div className="page-header__back">
            <Link to={`/exercises/${exercise.id}`}>← {exercise.title}</Link>
          </div>
          <h1 className="row">
            Kịch bản bản {version.revision} <ScriptStatusBadge status={version.status} />
          </h1>
          <p className="muted small">
            {SCRIPT_ORIGIN_LABELS[version.origin]} · tạo lúc {formatDateTime(version.created_at)}
            {version.review_note && ` · góp ý khi duyệt: “${version.review_note}”`}
          </p>
        </div>
        <div className="page-header__actions">
          {dirty && (
            <button type="button" className="btn" onClick={reset} disabled={save.isPending}>
              Bỏ thay đổi
            </button>
          )}
          {!dirty && (
            <button type="button" className="btn" onClick={() => rerun.mutate()} disabled={rerun.isPending}>
              {rerun.isPending ? "Đang tự kiểm…" : "Chạy lại tự kiểm"}
            </button>
          )}
          <button
            type="button"
            className="btn btn--primary"
            onClick={handleSave}
            disabled={!dirty || issues.length > 0 || save.isPending}
            title={issues.length > 0 ? "Sửa hết lỗi lược đồ trước khi lưu" : undefined}
          >
            {save.isPending ? "Đang lưu và tự kiểm…" : "Lưu thành bản mới"}
          </button>
        </div>
      </header>
      {savedRevision !== undefined && !dirty && (
        <Alert kind="success">Đã lưu thành bản {savedRevision} (nháp). Bản cũ vẫn được giữ.</Alert>
      )}
      {dirty && (
        <Alert kind="info">
          Có thay đổi chưa lưu. Lưu sẽ tạo bản mới (nháp); bản {version.revision} giữ nguyên.
          {issues.length > 0 && ` Còn ${String(issues.length)} lỗi cần sửa trước khi lưu.`}
        </Alert>
      )}
      {save.error && <SaveError error={save.error} script={draft} />}
      <ErrorAlert error={rerun.error} />
      <div className="editor">
        <aside className="editor__outline">
          <EditorOutline current={section} onSelect={select} />
        </aside>
        <div className="editor__main" key={sectionKey(section)}>
          {panel}
        </div>
        <aside className="editor__grid">
          <GridPanel exerciseId={exercise.id} defaultSheet={draft.exercise.sheet} marks={marks} />
        </aside>
      </div>
      {blocker.state === "blocked" && (
        <ConfirmDialog
          title="Rời trang khi chưa lưu?"
          confirmLabel="Bỏ thay đổi và rời trang"
          danger
          onCancel={() => blocker.reset()}
          onConfirm={() => blocker.proceed()}
        >
          <p>Các thay đổi chưa lưu sẽ mất.</p>
        </ConfirmDialog>
      )}
    </EditorContext>
  );
}
