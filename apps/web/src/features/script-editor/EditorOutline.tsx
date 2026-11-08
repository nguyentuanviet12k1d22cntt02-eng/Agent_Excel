import type { SelfCheckReport } from "@/api/types";

import { useEditor } from "./editorContext";
import { issuesUnder } from "./scriptSchema";
import { sectionKey, type Section } from "./sections";

/** Mục của báo cáo tự kiểm thuộc bước nào ("bước nhap_so_luong, điều kiện 0 …"). */
function reportProblems(report: SelfCheckReport | null, stepId: string): number {
  const prefix = new RegExp(`^bước ${stepId}[,:]`);
  const errors = (report?.errors ?? []).filter((e) => prefix.test(e)).length;
  const hints = (report?.hint_text_issues ?? []).filter((i) => i.step_id === stepId).length;
  return errors + hints;
}

/** Mục lục bên trái: tổng quan, các bước (đánh dấu bước có lỗi), toàn bài, hoàn thành, nguồn trích. */
export function EditorOutline({
  current,
  onSelect,
}: {
  current: Section;
  onSelect: (section: Section) => void;
}) {
  const { draft, issues, report } = useEditor();
  const active = sectionKey(current);

  function item(section: Section, label: string, badge?: { count: number; kind: "red" | "yellow" }) {
    const key = sectionKey(section);
    return (
      <li key={key}>
        <button
          type="button"
          className={key === active ? "outline__item outline__item--active" : "outline__item"}
          aria-current={key === active ? "true" : undefined}
          onClick={() => onSelect(section)}
        >
          <span className="outline__label">{label}</span>
          {badge && badge.count > 0 && (
            <span className={`badge badge--${badge.kind}`} title="Số lỗi cần sửa">
              {badge.count}
            </span>
          )}
        </button>
      </li>
    );
  }

  const schemaIssuesOutsideSteps = issues.filter((i) => !i.path.startsWith("/steps/")).length;
  return (
    <nav aria-label="Các phần của kịch bản">
      <ul className="outline">
        {item({ kind: "overview" }, "Tổng quan và kiểm tra", {
          count: schemaIssuesOutsideSteps,
          kind: "red",
        })}
      </ul>
      <h3 className="outline__heading">Các bước</h3>
      <ol className="outline">
        {draft.steps.map((step, index) => {
          const schemaCount = issuesUnder(issues, `/steps/${String(index)}`).length;
          const reportCount = reportProblems(report, step.id);
          return item(
            { kind: "step", index },
            `${String(index + 1)}. ${step.title || "(chưa có tên)"}`,
            schemaCount > 0 ? { count: schemaCount, kind: "red" } : { count: reportCount, kind: "yellow" },
          );
        })}
      </ol>
      <ul className="outline">
        {item({ kind: "global" }, `Điều kiện toàn bài (${String(draft.global_checks?.length ?? 0)})`, {
          count: issuesUnder(issues, "/global_checks").length,
          kind: "red",
        })}
        {item({ kind: "completion" }, "Màn hình hoàn thành", {
          count: issuesUnder(issues, "/completion").length,
          kind: "red",
        })}
        {item({ kind: "references" }, `Nguồn trích dẫn (${String(draft.references?.length ?? 0)})`)}
      </ul>
    </nav>
  );
}
