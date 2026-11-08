import { ApiError, errorMessage } from "@/api/errors";

import { Alert } from "./Alert";

/** Hiện lỗi gọi API: câu thông báo của Backend và chi tiết từng mục (nếu có). */
export function ErrorAlert({ error, title }: { error: unknown; title?: string }) {
  if (!error) return null;
  const details = error instanceof ApiError ? error.errors : [];
  return (
    <Alert kind="error" title={title}>
      {errorMessage(error)}
      {details.length > 0 && (
        <ul>
          {details.map((d, i) => (
            <li key={`${d.path}-${i}`}>{d.message}</li>
          ))}
        </ul>
      )}
    </Alert>
  );
}
