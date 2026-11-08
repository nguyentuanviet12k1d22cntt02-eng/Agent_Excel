import { useState } from "react";

import { Alert } from "@/components/Alert";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Field } from "@/components/Field";
import { Modal } from "@/components/Modal";

import { csvCell, saveCsv } from "@/lib/download";

import { useImportUsers, type ImportResult } from "./accountsApi";

const TEMPLATE = "email,full_name,role,password\nhv01@tdmu.edu.vn,Nguyễn Văn A,student,\n";

function passwordsCsv(result: ImportResult): string {
  const rows = result.generated_passwords.map((p) => `${csvCell(p.email)},${csvCell(p.password)}`);
  return ["email,password", ...rows].join("\n") + "\n";
}

export function ImportUsersDialog({ onClose }: { onClose: () => void }) {
  const importUsers = useImportUsers();
  const [file, setFile] = useState<File | null>(null);
  const result = importUsers.data;
  const generated = result?.generated_passwords ?? [];

  return (
    <Modal
      title="Nhập tài khoản từ CSV"
      onClose={onClose}
      busy={importUsers.isPending}
      wide
      footer={
        result ? (
          <button type="button" className="btn btn--primary" onClick={onClose}>
            Xong
          </button>
        ) : (
          <>
            <button type="button" className="btn" onClick={onClose} disabled={importUsers.isPending}>
              Hủy
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={!file || importUsers.isPending}
              onClick={() => file && importUsers.mutate(file)}
            >
              {importUsers.isPending ? "Đang nhập…" : "Nhập"}
            </button>
          </>
        )
      }
    >
      {!result && (
        <div className="stack">
          <ErrorAlert error={importUsers.error} />
          <p className="small">
            File CSV UTF-8 có dòng tiêu đề <code>email,full_name,role,password</code>. Bỏ trống{" "}
            <code>role</code> là học viên; bỏ trống <code>password</code> thì hệ thống tạo mật khẩu ngẫu nhiên
            và hiện một lần sau khi nhập.{" "}
            <button
              type="button"
              className="link-button"
              onClick={() => saveCsv(TEMPLATE, "mau-tai-khoan.csv")}
            >
              Tải file mẫu
            </button>
          </p>
          <Field label="File CSV">
            {(p) => (
              <input
                {...p}
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            )}
          </Field>
        </div>
      )}
      {result && (
        <div className="stack">
          <Alert kind="success">Đã tạo {result.created} tài khoản.</Alert>
          {result.skipped.length > 0 && (
            <Alert kind="warning" title={`Bỏ qua ${String(result.skipped.length)} dòng`}>
              <ul>
                {result.skipped.map((s) => (
                  <li key={s.line}>
                    Dòng {s.line}: {s.reason}
                  </li>
                ))}
              </ul>
            </Alert>
          )}
          {generated.length > 0 && (
            <>
              <Alert kind="warning" title="Mật khẩu tạo tự động chỉ hiện lần này">
                Tải danh sách về để phát cho học viên trước khi đóng hộp thoại.
              </Alert>
              <button
                type="button"
                className="btn"
                onClick={() => saveCsv(passwordsCsv(result), "mat-khau-hoc-vien.csv")}
              >
                Tải danh sách mật khẩu (CSV)
              </button>
              <div className="table-wrap">
                <table className="table table--compact">
                  <thead>
                    <tr>
                      <th>Email</th>
                      <th>Mật khẩu</th>
                    </tr>
                  </thead>
                  <tbody>
                    {generated.map((p) => (
                      <tr key={p.email}>
                        <td>{p.email}</td>
                        <td>
                          <code className="secret">{p.password}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </Modal>
  );
}
