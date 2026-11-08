import { useState } from "react";

import { errorMessage } from "@/api/errors";

import { downloadStarterFile } from "./publishingApi";

export function DownloadStarterButton({
  exerciseId,
  code,
  primary = false,
}: {
  exerciseId: string;
  code: string;
  primary?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setBusy(true);
    setError(null);
    try {
      await downloadStarterFile(exerciseId, `${code}.xlsx`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="download">
      <button
        type="button"
        className={primary ? "btn btn--primary" : "btn"}
        onClick={() => void handleClick()}
        disabled={busy}
        title="File đề đã nhúng mã bài: học viên mở file này thì gia sư tự nhận ra bài"
      >
        {busy ? "Đang tải…" : "Tải file đề cho học viên"}
      </button>
      {error && (
        <span className="field__error" role="alert">
          {error}
        </span>
      )}
    </span>
  );
}
