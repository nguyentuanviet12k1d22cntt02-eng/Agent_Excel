import { useId, type ReactNode } from "react";

export interface FieldControlProps {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
}

/**
 * Ô nhập có nhãn, dòng hướng dẫn và lỗi. Nhãn chỉ gồm tên ô; hướng dẫn và lỗi gắn bằng aria-describedby
 * để trình đọc màn hình đọc đúng.
 */
export function Field({
  label,
  hint,
  error,
  full = false,
  children,
}: {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  full?: boolean;
  children: (props: FieldControlProps) => ReactNode;
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={full ? "field field--full" : "field"}>
      <label htmlFor={id}>{label}</label>
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {error && (
        <span id={errorId} className="field__error">
          {error}
        </span>
      )}
      {hint && (
        <span id={hintId} className="field__hint">
          {hint}
        </span>
      )}
    </div>
  );
}
