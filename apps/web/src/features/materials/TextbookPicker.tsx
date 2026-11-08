import { Link } from "react-router";

import { useTextbooks } from "./materialsApi";

/** Chọn giáo trình liên quan tới bài: AI chỉ tìm đoạn trích trong các giáo trình này. */
export function TextbookPicker({ value, onChange }: { value: string[]; onChange: (ids: string[]) => void }) {
  const textbooks = useTextbooks();
  const items = textbooks.data ?? [];

  function toggle(id: string, checked: boolean) {
    onChange(checked ? [...value, id] : value.filter((v) => v !== id));
  }

  return (
    <fieldset className="field fieldset">
      <legend>Giáo trình liên quan</legend>
      {textbooks.isPending && <span className="muted small">Đang tải…</span>}
      {!textbooks.isPending && items.length === 0 && (
        <span className="muted small">
          Chưa có giáo trình. <Link to="/textbooks">Tải giáo trình lên</Link> để AI trích dẫn khi viết gợi ý.
        </span>
      )}
      {items.map((t) => (
        <label key={t.id} className="checkbox">
          <input
            type="checkbox"
            checked={value.includes(t.id)}
            onChange={(e) => toggle(t.id, e.target.checked)}
          />
          {t.title}
          {t.status !== "ready" && <span className="muted small">(chưa sẵn sàng)</span>}
        </label>
      ))}
      <span className="field__hint">Không chọn: AI tìm trong mọi giáo trình đã sẵn sàng.</span>
    </fieldset>
  );
}
