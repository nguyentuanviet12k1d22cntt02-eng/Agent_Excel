import { useEffect, useState } from "react";

import { readSheetNames } from "@/lib/xlsxSheets";

export type SheetNames =
  | { status: "idle" }
  | { status: "reading" }
  | { status: "ok"; names: string[] }
  | { status: "error"; message: string };

interface ReadResult {
  file: File;
  result: SheetNames;
}

/** Tên các sheet của file .xlsx vừa chọn (đọc trên trình duyệt). */
export function useSheetNames(file: File | null): SheetNames {
  const [read, setRead] = useState<ReadResult | null>(null);

  useEffect(() => {
    if (!file) return;
    let cancelled = false;
    readSheetNames(file)
      .then((names) => {
        if (!cancelled) setRead({ file, result: { status: "ok", names } });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Không đọc được file";
        if (!cancelled) setRead({ file, result: { status: "error", message } });
      });
    return () => {
      cancelled = true;
    };
  }, [file]);

  if (!file) return { status: "idle" };
  // Kết quả của file chọn trước đó không dùng cho file mới
  return read?.file === file ? read.result : { status: "reading" };
}
