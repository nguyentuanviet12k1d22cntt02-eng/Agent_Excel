const DATE_TIME = new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" });
const NUMBER = new Intl.NumberFormat("vi-VN");

/** Ngày giờ theo kiểu Việt Nam, ví dụ "14:05 08/11/2026". Không có thì "—". */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "—" : DATE_TIME.format(date);
}

export function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : NUMBER.format(value);
}

/** Thời lượng từ mili giây, ví dụ "8,6 giây" hoặc "1 phút 5 giây". */
export function formatDuration(ms: number | null | undefined): string {
  if (!ms) return "—";
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} phút ${Math.round(seconds % 60)} giây`;
}

export function formatPercent(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined) return "—";
  return `${Math.round(ratio * 100)}%`;
}
