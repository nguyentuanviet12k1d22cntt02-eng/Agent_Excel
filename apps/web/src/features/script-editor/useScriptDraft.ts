import { useCallback, useMemo, useState } from "react";

import type { Script, ScriptVersion, Step } from "@/api/types";

interface DraftState {
  versionId: string;
  draft: Script;
}

export interface ScriptDraft {
  draft: Script;
  dirty: boolean;
  update: (change: (script: Script) => Script) => void;
  updateStep: (index: number, change: (step: Step) => Step) => void;
  moveStep: (index: number, delta: -1 | 1) => void;
  removeStep: (index: number) => void;
  reset: () => void;
}

export function replaceAt<T>(items: readonly T[], index: number, value: T): T[] {
  return items.map((item, i) => (i === index ? value : item));
}

export function removeAt<T>(items: readonly T[], index: number): T[] {
  return items.filter((_, i) => i !== index);
}

export function move<T>(items: readonly T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (target < 0 || target >= items.length) return [...items];
  const copy = [...items];
  const [item] = copy.splice(index, 1);
  if (item !== undefined) copy.splice(target, 0, item);
  return copy;
}

/** Xóa bước, gỡ luôn bước đó khỏi tiêu chí hoàn thành (tiêu chí không còn bước nào thì bỏ). */
export function withoutStep(script: Script, index: number): Script {
  const id = script.steps[index]?.id;
  const criteria = script.completion?.criteria
    ?.map((c) => ({ ...c, step_ids: c.step_ids.filter((s) => s !== id) }))
    .filter((c) => c.step_ids.length > 0);
  return {
    ...script,
    steps: removeAt(script.steps, index),
    ...(script.completion ? { completion: { ...script.completion, criteria } } : {}),
  };
}

/**
 * Bản đang sửa của một revision. Mở revision khác thì tự lấy lại nội dung của revision đó (không giữ bản
 * sửa dở của revision cũ). Sửa nhiều chỗ rồi lưu một lần thành revision mới.
 */
export function useScriptDraft(version: ScriptVersion): ScriptDraft {
  const [state, setState] = useState<DraftState>({ versionId: version.id, draft: version.content });
  const draft = state.versionId === version.id ? state.draft : version.content;

  const update = useCallback(
    (change: (script: Script) => Script) => {
      setState((prev) => {
        const current = prev.versionId === version.id ? prev.draft : version.content;
        return { versionId: version.id, draft: change(current) };
      });
    },
    [version.id, version.content],
  );

  const dirty = useMemo(
    () => draft !== version.content && JSON.stringify(draft) !== JSON.stringify(version.content),
    [draft, version.content],
  );

  return {
    draft,
    dirty,
    update,
    updateStep: (index, change) => {
      update((s) => ({ ...s, steps: replaceAt(s.steps, index, change(s.steps[index] as Step)) }));
    },
    moveStep: (index, delta) => {
      update((s) => ({ ...s, steps: move(s.steps, index, delta) }));
    },
    removeStep: (index) => {
      update((s) => withoutStep(s, index));
    },
    reset: () => {
      setState({ versionId: version.id, draft: version.content });
    },
  };
}
