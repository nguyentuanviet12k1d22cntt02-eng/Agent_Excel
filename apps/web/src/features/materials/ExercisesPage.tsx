import { useDeferredValue, useState } from "react";
import { Link } from "react-router";

import { ErrorAlert } from "@/components/ErrorAlert";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { ScriptStatusBadge } from "@/components/ScriptStatusBadge";

import { useExercises } from "./materialsApi";

export function ExercisesPage() {
  const [search, setSearch] = useState("");
  const query = useDeferredValue(search.trim());
  const exercises = useExercises(query);

  return (
    <>
      <PageHeader
        title="Bài tập"
        subtitle="Mỗi bài gồm file đề và file đáp án cùng bố cục; AI sinh kịch bản hướng dẫn từ hai file này."
        actions={
          <Link to="/exercises/new" className="btn btn--primary">
            Tạo bài tập
          </Link>
        }
      />
      <div className="toolbar">
        <input
          type="search"
          aria-label="Tìm bài tập"
          placeholder="Tìm theo tên hoặc mã bài"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {exercises.isPending && <Loading />}
      <ErrorAlert error={exercises.error} />
      {exercises.data?.length === 0 && (
        <div className="card empty">
          <p>{query ? "Không có bài nào khớp." : "Chưa có bài tập nào."}</p>
        </div>
      )}
      {exercises.data && exercises.data.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Tên bài</th>
                <th>Mã bài</th>
                <th>Sheet làm bài</th>
                <th>Kịch bản mới nhất</th>
                <th>Đang phát hành</th>
              </tr>
            </thead>
            <tbody>
              {exercises.data.map((exercise) => (
                <tr key={exercise.id}>
                  <td>
                    <Link to={`/exercises/${exercise.id}`}>{exercise.title}</Link>
                    {(exercise.warnings?.length ?? 0) > 0 && (
                      <span
                        className="badge badge--yellow badge--inline"
                        title={exercise.warnings?.join("\n")}
                      >
                        {exercise.warnings?.length} cảnh báo
                      </span>
                    )}
                  </td>
                  <td>
                    <code>{exercise.code}</code>
                  </td>
                  <td>{exercise.sheet_name}</td>
                  <td>
                    {exercise.latest_version ? (
                      <span className="row">
                        <span className="muted small">bản {exercise.latest_version.revision}</span>
                        <ScriptStatusBadge status={exercise.latest_version.status} />
                      </span>
                    ) : (
                      <span className="muted">Chưa có</span>
                    )}
                  </td>
                  <td>
                    {exercise.published_version ? (
                      `Bản ${exercise.published_version.revision}`
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
