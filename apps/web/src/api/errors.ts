/** Lỗi gọi API: Backend trả `application/problem+json` có `code` ổn định và `message` tiếng Việt. */
import type { Problem } from "./types";

export interface FieldError {
  path: string;
  message: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly errors: FieldError[];

  constructor(status: number, code: string, message: string, errors: FieldError[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  401: "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.",
  403: "Tài khoản của bạn không có quyền làm việc này.",
  404: "Không tìm thấy dữ liệu (có thể đã bị xóa).",
  413: "File quá lớn.",
  500: "Máy chủ gặp lỗi. Thử lại sau hoặc báo nhóm phát triển.",
  502: "Không kết nối được máy chủ Backend.",
  503: "Máy chủ đang bận, thử lại sau.",
};

function isProblem(value: unknown): value is Problem {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).code === "string" &&
    typeof (value as Record<string, unknown>).message === "string"
  );
}

function fieldErrors(problem: Problem): FieldError[] {
  return (problem.errors ?? []).map((e) => ({ path: e.path ?? "", message: e.message ?? "" }));
}

/** Dựng ApiError từ phần thân lỗi (đã đọc JSON hoặc chưa đọc được). */
export function toApiError(status: number, body: unknown): ApiError {
  if (isProblem(body)) return new ApiError(status, body.code, body.message, fieldErrors(body));
  const message = STATUS_MESSAGES[status] ?? `Yêu cầu không thành công (mã ${status}).`;
  return new ApiError(status, `http_${status}`, message);
}

export const NETWORK_ERROR = "Không kết nối được máy chủ. Kiểm tra Backend đã chạy chưa.";

/** Câu thông báo để hiện cho người dùng, từ mọi loại lỗi. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return NETWORK_ERROR; // fetch ném TypeError khi mất kết nối
  if (error instanceof Error) return error.message;
  return "Đã có lỗi xảy ra.";
}
