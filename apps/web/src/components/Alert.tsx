import type { ReactNode } from "react";

export type AlertKind = "info" | "success" | "warning" | "error";

export function Alert({
  kind = "info",
  title,
  children,
}: {
  kind?: AlertKind;
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className={`alert alert--${kind}`} role={kind === "error" ? "alert" : "status"}>
      {title && <strong className="alert__title">{title}</strong>}
      {children}
    </div>
  );
}
