export function Loading({ label = "Đang tải…", fullPage = false }: { label?: string; fullPage?: boolean }) {
  return (
    <div className={fullPage ? "loading loading--page" : "loading"} role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
