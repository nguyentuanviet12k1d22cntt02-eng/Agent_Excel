import { useState, type SubmitEvent } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError } from "@/api/errors";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { EXERCISE_CODE_PATTERN, slugify } from "@/lib/text";

import { useCreateExercise } from "./materialsApi";
import { TextbookPicker } from "./TextbookPicker";
import { useSheetNames } from "./useSheetNames";

const XLSX_ACCEPT = ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const PROMPT_ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";

/** Lỗi Backend theo trường (path "/starter_file") → câu hiện dưới ô tương ứng. */
function fieldErrors(error: unknown): Record<string, string | undefined> {
  if (!(error instanceof ApiError)) return {};
  return Object.fromEntries(error.errors.map((e) => [e.path.replace(/^\//, ""), e.message]));
}

export function ExerciseCreatePage() {
  const navigate = useNavigate();
  const create = useCreateExercise();
  const [title, setTitle] = useState("");
  const [code, setCode] = useState("");
  const [codeEdited, setCodeEdited] = useState(false);
  const [starterFile, setStarterFile] = useState<File | null>(null);
  const [solutionFile, setSolutionFile] = useState<File | null>(null);
  const [sheetName, setSheetName] = useState("");
  const [promptText, setPromptText] = useState("");
  const [promptFile, setPromptFile] = useState<File | null>(null);
  const [textbookIds, setTextbookIds] = useState<string[]>([]);
  const sheets = useSheetNames(starterFile);
  const errors = fieldErrors(create.error);

  const codeValid = EXERCISE_CODE_PATTERN.test(code);
  const canSubmit = title.trim() && codeValid && starterFile && solutionFile && sheetName.trim();

  function changeTitle(value: string) {
    setTitle(value);
    if (!codeEdited) setCode(slugify(value));
  }

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!starterFile || !solutionFile) return;
    create.mutate(
      {
        code,
        title: title.trim(),
        sheetName: sheetName.trim(),
        starterFile,
        solutionFile,
        promptFile,
        promptText: promptText.trim(),
        textbookIds,
      },
      { onSuccess: (exercise) => void navigate(`/exercises/${exercise.id}`) },
    );
  }

  const sheetOptions = sheets.status === "ok" ? sheets.names : [];
  const codeError =
    errors.code ??
    (code.length > 0 && !codeValid ? "Mã bài chưa đúng dạng (xem hướng dẫn bên dưới)." : undefined);
  return (
    <>
      <PageHeader
        back={<Link to="/exercises">← Bài tập</Link>}
        title="Tạo bài tập"
        subtitle="File đáp án là file đề đã làm xong, lưu bằng Excel (để có giá trị đã tính của công thức)."
      />
      <form className="card" onSubmit={handleSubmit} noValidate>
        <ErrorAlert error={create.error} title="Chưa tạo được bài tập" />
        <div className="form-grid">
          <Field label="Tên bài">
            {(p) => (
              <input
                {...p}
                type="text"
                required
                maxLength={200}
                value={title}
                onChange={(e) => changeTitle(e.target.value)}
              />
            )}
          </Field>
          <Field
            label="Mã bài"
            error={codeError}
            hint="Chữ thường không dấu, số, gạch nối; 3–64 ký tự. Được nhúng vào file đề để Desktop nhận ra bài, không đổi được sau khi phát hành."
          >
            {(p) => (
              <input
                {...p}
                type="text"
                required
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  setCodeEdited(true);
                }}
              />
            )}
          </Field>
          <Field label="File đề (.xlsx)" hint="File học viên nhận được." error={errors.starter_file}>
            {(p) => (
              <input
                {...p}
                type="file"
                accept={XLSX_ACCEPT}
                required
                onChange={(e) => {
                  setStarterFile(e.target.files?.[0] ?? null);
                  setSheetName("");
                }}
              />
            )}
          </Field>
          <Field
            label="File đáp án (.xlsx)"
            hint="Cùng bố cục với file đề, đã làm xong."
            error={errors.solution_file}
          >
            {(p) => (
              <input
                {...p}
                type="file"
                accept={XLSX_ACCEPT}
                required
                onChange={(e) => setSolutionFile(e.target.files?.[0] ?? null)}
              />
            )}
          </Field>
          <Field
            label="Sheet làm bài"
            error={
              errors.sheet_name ??
              (sheets.status === "error" ? `${sheets.message}. Gõ tên sheet bằng tay.` : undefined)
            }
          >
            {(p) =>
              sheetOptions.length > 0 ? (
                <select {...p} required value={sheetName} onChange={(e) => setSheetName(e.target.value)}>
                  <option value="">— Chọn sheet —</option>
                  {sheetOptions.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  {...p}
                  type="text"
                  required
                  maxLength={31}
                  value={sheetName}
                  placeholder={sheets.status === "reading" ? "Đang đọc file đề…" : "Chọn file đề trước"}
                  onChange={(e) => setSheetName(e.target.value)}
                />
              )
            }
          </Field>
          <Field label="Đề bài dạng file (tùy chọn)" hint="PDF hoặc ảnh, để giảng viên khác xem lại.">
            {(p) => (
              <input
                {...p}
                type="file"
                accept={PROMPT_ACCEPT}
                onChange={(e) => setPromptFile(e.target.files?.[0] ?? null)}
              />
            )}
          </Field>
          <Field label="Đề bài dạng chữ (tùy chọn)" hint="AI đọc phần này khi chia bước và viết gợi ý." full>
            {(p) => (
              <textarea
                {...p}
                rows={4}
                maxLength={20000}
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
              />
            )}
          </Field>
          <div className="field--full">
            <TextbookPicker value={textbookIds} onChange={setTextbookIds} />
          </div>
        </div>
        <div className="form-actions">
          <Link to="/exercises" className="btn">
            Hủy
          </Link>
          <button type="submit" className="btn btn--primary" disabled={!canSubmit || create.isPending}>
            {create.isPending ? "Đang kiểm file và tạo…" : "Tạo bài tập"}
          </button>
        </div>
      </form>
    </>
  );
}
