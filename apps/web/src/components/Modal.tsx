import { useEffect, useId, useRef, type ReactNode } from "react";

/**
 * Hộp thoại nổi. Esc hoặc bấm ra ngoài để đóng (trừ khi đang xử lý); mở thì đưa con trỏ vào hộp thoại,
 * đóng thì trả con trỏ về chỗ cũ.
 */
export function Modal({
  title,
  children,
  footer,
  onClose,
  busy = false,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
  busy?: boolean;
  wide?: boolean;
}) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const first = panel.current?.querySelector<HTMLElement>(
      "input, textarea, select, button:not(.modal__close)",
    );
    (first ?? panel.current)?.focus();
    return () => previous?.focus();
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
    };
  }, [busy, onClose]);

  return (
    <div
      className="modal"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div
        ref={panel}
        className={wide ? "modal__panel modal__panel--wide" : "modal__panel"}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <div className="modal__header">
          <h2 id={titleId}>{title}</h2>
          <button
            type="button"
            className="btn btn--ghost btn--small modal__close"
            onClick={onClose}
            disabled={busy}
            aria-label="Đóng"
          >
            ✕
          </button>
        </div>
        <div className="modal__body">{children}</div>
        {footer && <div className="modal__footer">{footer}</div>}
      </div>
    </div>
  );
}
