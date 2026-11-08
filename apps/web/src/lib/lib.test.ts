import { fixtureXlsx } from "@/test/fixtures";

import { formatDuration, formatPercent } from "./format";
import { EXERCISE_CODE_PATTERN, slugify, stripAccents } from "./text";
import { readSheetNames, sheetNamesFromWorkbookXml, XlsxReadError } from "./xlsxSheets";

test("đọc tên sheet từ file .xlsx thật, đúng thứ tự, giữ dấu tiếng Việt", async () => {
  expect(await readSheetNames(fixtureXlsx("b22", "de.xlsx"))).toContain("Bài 01");
  const b09 = await readSheetNames(fixtureXlsx("b09", "de.xlsx"));
  expect(b09).toContain("2. Bang_Ke_Ban_Hang");
});

test("file không phải .xlsx thì báo lỗi dễ hiểu", async () => {
  await expect(readSheetNames(new File(["xin chào"], "a.xlsx"))).rejects.toBeInstanceOf(XlsxReadError);
});

test("tên sheet có ký tự đặc biệt được giải mã", () => {
  const xml = `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheets><sheet name="Đề &amp; đáp án" sheetId="1"/><sheet name="Bài 2" sheetId="2"/></sheets></workbook>`;
  expect(sheetNamesFromWorkbookXml(xml)).toEqual(["Đề & đáp án", "Bài 2"]);
});

test("gợi ý mã bài từ tên tiếng Việt", () => {
  expect(stripAccents("Định dạng Đơn giá")).toBe("Dinh dang Don gia");
  expect(slugify("Bài 22: Hàm tính tổng SUM")).toBe("bai-22-ham-tinh-tong-sum");
  expect(EXERCISE_CODE_PATTERN.test(slugify("Bài 22: Hàm tính tổng SUM"))).toBe(true);
  expect(slugify("x".repeat(80))).toHaveLength(64);
});

test("định dạng thời lượng và phần trăm", () => {
  expect(formatDuration(8600)).toBe("8,6 giây");
  expect(formatDuration(65_000)).toBe("1 phút 5 giây");
  expect(formatDuration(0)).toBe("—");
  expect(formatPercent(0.875)).toBe("88%");
});
