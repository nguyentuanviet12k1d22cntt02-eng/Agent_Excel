// Bỏ các chữ dễ nhầm khi đọc cho học viên (l, 1, I, O, 0, o)
const PASSWORD_CHARS = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
// Bỏ byte ≥ 224 (= 4 × 56) để mỗi ký tự có xác suất như nhau (không lệch do phép chia lấy dư)
const UNBIASED_LIMIT = 256 - (256 % PASSWORD_CHARS.length);

/** Mật khẩu ngẫu nhiên (mặc định 10 ký tự) cho tài khoản mới. */
export function randomPassword(length = 10): string {
  let result = "";
  while (result.length < length) {
    for (const byte of crypto.getRandomValues(new Uint8Array(length * 2))) {
      if (byte < UNBIASED_LIMIT && result.length < length)
        result += PASSWORD_CHARS.charAt(byte % PASSWORD_CHARS.length);
    }
  }
  return result;
}
