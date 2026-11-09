import { useState } from "react";

import type { ScriptVersion } from "@/api/types";
import { Alert } from "@/components/Alert";
import { Modal } from "@/components/Modal";

/**
 * Hướng dẫn chạy thử kịch bản ngay trên Excel bằng ứng dụng gia sư (chế độ giảng viên): app mở một bản sao
 * file đề trong Excel, hiện cửa sổ gia sư bên cạnh, khoanh vùng ô và nút Ribbon theo gợi ý, tự chuyển bước.
 */
export function RunInExcelDialog({
  version,
  dirty,
  onClose,
}: {
  version: ScriptVersion;
  dirty: boolean;
  onClose: () => void;
}) {
  const command = `.venv\\Scripts\\python -m tutor_desktop --version ${version.id}`;
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Modal
      title="Chạy thử trên Excel"
      onClose={onClose}
      wide
      footer={
        <button type="button" className="btn btn--primary" onClick={onClose}>
          Đóng
        </button>
      }
    >
      {dirty && (
        <Alert kind="warning">
          Đang có thay đổi chưa lưu: ứng dụng chạy bản {version.revision} đã lưu. Lưu thành bản mới rồi mở lại
          hộp thoại này để chạy thử bản mới.
        </Alert>
      )}
      <ol className="run-steps">
        <li>
          Mở PowerShell ở thư mục dự án và chạy lệnh dưới đây (Backend phải đang chạy):
          <div className="run-command">
            <code>{command}</code>
            <button type="button" className="btn btn--small" onClick={() => void copy()}>
              {copied ? "Đã chép" : "Chép lệnh"}
            </button>
          </div>
        </li>
        <li>
          Đăng nhập bằng tài khoản giảng viên. Ứng dụng tải một bản sao file đề và mở trong Excel của bạn.
        </li>
        <li>
          Làm bài trong Excel như một học viên. Cửa sổ gia sư bên phải hiện thẻ yêu cầu của bước, tự chuyển
          bước khi bạn làm đúng, hiện phản hồi khi làm sai và nhắc ngay khi sửa nhầm dữ liệu gốc.
        </li>
        <li>
          Bấm <strong>Xin gợi ý</strong> để xem từng cấp. Ở cấp 3, ứng dụng khoanh vùng ô và nút trên Ribbon
          ngay trên Excel; đánh dấu “Khoanh vùng của bước” để luôn thấy vùng mục tiêu.
        </li>
      </ol>
      <p className="muted small">
        Ứng dụng chỉ đọc Excel, không sửa file nào khác và không đóng Excel của bạn. Mỗi lần chạy thử dùng một
        bản sao mới của file đề gốc.
      </p>
    </Modal>
  );
}
