// Kiểm src/api/schema.d.ts còn khớp docs/thiet-ke/openapi.yaml (chạy trên CI).
// Sửa đặc tả mà quên sinh lại kiểu thì báo lỗi: chạy `npm run gen:api` rồi commit.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const spec = new URL("../../../docs/thiet-ke/openapi.yaml", import.meta.url);
const committed = fileURLToPath(new URL("../src/api/schema.d.ts", import.meta.url));

// CLI thêm khối chú thích "auto-generated" ở đầu file, bản sinh bằng API thì không
const normalize = (text) =>
  text
    .replace(/\r\n/g, "\n")
    .replace(/^\/\*\*[\s\S]*?\*\/\s*/, "")
    .trim();
const expected = astToString(await openapiTS(spec));
const actual = readFileSync(committed, "utf8");

if (normalize(expected) !== normalize(actual)) {
  console.error("src/api/schema.d.ts đã cũ so với openapi.yaml. Chạy: npm run gen:api");
  process.exit(1);
}
console.log("Kiểu API khớp với openapi.yaml.");
