import type { Textbook } from "@/api/types";

import { isIndexing } from "./materialsApi";

export function TextbookStatusBadge({ textbook }: { textbook: Textbook }) {
  if (isIndexing(textbook)) {
    return (
      <span className="badge badge--blue">
        <span className="spinner spinner--tiny" aria-hidden="true" />
        Đang lập chỉ mục
      </span>
    );
  }
  if (textbook.status === "ready") {
    return <span className="badge badge--green">Sẵn sàng · {textbook.chunk_count ?? 0} đoạn</span>;
  }
  return <span className="badge badge--red">Lỗi</span>;
}
