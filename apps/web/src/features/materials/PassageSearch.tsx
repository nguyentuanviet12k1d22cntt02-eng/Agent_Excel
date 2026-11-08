import { useState, type SubmitEvent } from "react";

import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";

import { useSearchPassages } from "./materialsApi";

const PREVIEW_CHARS = 400;

/** Thử tìm đoạn giáo trình như AI sẽ tìm khi sinh kịch bản (BM25, gõ không dấu vẫn được). */
export function PassageSearch() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const result = useSearchPassages(query);

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(input.trim());
  }

  return (
    <section className="card section-gap">
      <div className="card__title">
        <h2>Thử tìm trong giáo trình</h2>
      </div>
      <p className="muted small">
        Gõ chủ đề của bài (ví dụ “hàm VLOOKUP”, “định dạng số”) để xem AI sẽ trích những đoạn nào. Chỉ tìm
        trong giáo trình đã sẵn sàng.
      </p>
      <form className="row" onSubmit={handleSubmit} role="search">
        <input
          type="search"
          aria-label="Từ khóa"
          placeholder="Từ khóa"
          maxLength={500}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="grow"
        />
        <button type="submit" className="btn" disabled={!input.trim()}>
          Tìm
        </button>
      </form>
      {result.isFetching && <Loading label="Đang tìm…" />}
      <ErrorAlert error={result.error} />
      {result.data?.length === 0 && <p className="muted">Không tìm thấy đoạn nào phù hợp.</p>}
      {result.data && result.data.length > 0 && (
        <ol className="passages">
          {result.data.map((p) => (
            <li key={p.chunk_id}>
              <div className="passages__head">
                <strong>{p.heading}</strong>
                <span className="muted small">
                  {p.textbook_title}
                  {p.page != null && ` · trang ${p.page}`} · điểm{" "}
                  {p.score.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}
                </span>
              </div>
              <p className="passages__text">
                {p.content.length > PREVIEW_CHARS ? `${p.content.slice(0, PREVIEW_CHARS)}…` : p.content}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
