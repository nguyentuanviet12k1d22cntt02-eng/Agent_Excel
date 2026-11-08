import type { ScriptStatus } from "@/api/types";
import { SCRIPT_STATUS_LABELS } from "@/lib/scriptLabels";

const STATUS_COLORS: Record<ScriptStatus, string> = {
  draft: "",
  pending_review: "badge--yellow",
  approved: "badge--blue",
  published: "badge--green",
  archived: "",
};

export function ScriptStatusBadge({ status }: { status: ScriptStatus }) {
  return <span className={`badge ${STATUS_COLORS[status]}`}>{SCRIPT_STATUS_LABELS[status]}</span>;
}
