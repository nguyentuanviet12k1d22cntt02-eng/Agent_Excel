"""Danh mục nút Ribbon cho AI chọn khi sinh kịch bản (danh sách đóng, AI không bịa được mã).

Mã là AutomationId = idMso, không đổi theo ngôn ngữ Office (T2.4, spikes/t2-4-uia-ribbon/danh-muc-idmso.md).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RibbonControl:
    control: str  # AutomationId (idMso)
    tab: str
    label: str  # tên hiện cho học viên (tiếng Anh như trên Office đang dùng ở trung tâm, kèm nghĩa)


_CONTROLS = [
    # Thẻ Home
    ("Copy", "TabHome", "Copy (sao chép)"),
    ("Paste", "TabHome", "Paste (dán)"),
    ("FormatPainter", "TabHome", "Format Painter (chổi sao định dạng)"),
    ("Font", "TabHome", "ô chọn phông chữ"),
    ("FontSize", "TabHome", "ô chọn cỡ chữ"),
    ("Bold", "TabHome", "Bold (in đậm)"),
    ("Italic", "TabHome", "Italic (in nghiêng)"),
    ("Underline", "TabHome", "Underline (gạch chân)"),
    ("BordersGallery_Dropdown", "TabHome", "Borders (kẻ viền)"),
    ("CellFillColorPicker", "TabHome", "Fill Color (màu nền)"),
    ("FontColorPicker", "TabHome", "Font Color (màu chữ)"),
    ("AlignLeft", "TabHome", "Align Left (căn trái)"),
    ("AlignCenter", "TabHome", "Center (căn giữa)"),
    ("AlignRight", "TabHome", "Align Right (căn phải)"),
    ("AlignTopExcel", "TabHome", "Top Align (căn trên)"),
    ("AlignMiddleExcel", "TabHome", "Middle Align (căn giữa theo chiều dọc)"),
    ("AlignBottomExcel", "TabHome", "Bottom Align (căn dưới)"),
    ("WrapText", "TabHome", "Wrap Text (xuống dòng trong ô)"),
    ("MergeCenter", "TabHome", "Merge & Center (gộp ô và căn giữa)"),
    ("NumberFormatGallery", "TabHome", "ô chọn kiểu định dạng số"),
    ("InternationalCurrency", "TabHome", "Accounting Number Format (định dạng kế toán)"),
    ("PercentStyle", "TabHome", "Percent Style (phần trăm)"),
    ("CommaStyle", "TabHome", "Comma Style (dấu phân cách hàng nghìn)"),
    ("DecimalsIncrease", "TabHome", "Increase Decimal (tăng số lẻ)"),
    ("DecimalsDecrease", "TabHome", "Decrease Decimal (giảm số lẻ)"),
    ("FormatCellsNumberDialog", "TabHome", "hộp thoại Format Cells, thẻ Number"),
    ("FormatCellsFontDialog", "TabHome", "hộp thoại Format Cells, thẻ Font"),
    ("CellAlignmentOptions", "TabHome", "hộp thoại Format Cells, thẻ Alignment"),
    ("CellsInsertSmart", "TabHome", "Insert (chèn ô/dòng/cột)"),
    ("CellsDeleteSmart", "TabHome", "Delete (xóa ô/dòng/cột)"),
    ("FormatCellsMenu", "TabHome", "Format (chiều cao dòng, độ rộng cột, ẩn/hiện)"),
    ("CellsInsertSmart", "TabHome", "Insert (chèn ô, dòng, cột)"),
    ("CellsDeleteSmart", "TabHome", "Delete (xóa ô, dòng, cột)"),
    ("AutoSum", "TabHome", "AutoSum (Σ, tự gõ hàm SUM)"),
    ("FillMenu", "TabHome", "Fill (điền dữ liệu)"),
    ("SortFilterMenu", "TabHome", "Sort & Filter (sắp xếp và lọc)"),
    # Thẻ Insert
    ("ChartInsertGalleryNew", "TabInsert", "Recommended Charts (biểu đồ đề xuất)"),
    ("ChartTypeColumnInsertGallery", "TabInsert", "Insert Column or Bar Chart (biểu đồ cột/thanh)"),
    ("ChartTypeLineInsertGallery", "TabInsert", "Insert Line or Area Chart (biểu đồ đường)"),
    ("ChartTypePieInsertGallery", "TabInsert", "Insert Pie or Doughnut Chart (biểu đồ tròn)"),
    # Thẻ Page Layout
    ("PageMarginsGallery", "TabPageLayoutExcel", "Margins (lề trang)"),
    ("PageOrientationGallery", "TabPageLayoutExcel", "Orientation (hướng giấy)"),
    ("PageSizeGallery", "TabPageLayoutExcel", "Size (khổ giấy)"),
    ("PrintAreaMenu", "TabPageLayoutExcel", "Print Area (vùng in)"),
    ("PageSetupPageDialog", "TabPageLayoutExcel", "hộp thoại Page Setup"),
    ("PageScaleToFitWidth", "TabPageLayoutExcel", "Width (ép vừa chiều ngang trang)"),
    ("PageScaleToFitHeight", "TabPageLayoutExcel", "Height (ép vừa chiều dọc trang)"),
    ("PrintTitles", "TabPageLayoutExcel", "Print Titles (in lặp tiêu đề)"),
    # Thẻ Formulas
    ("FunctionWizard", "TabFormulas", "Insert Function (fx, chèn hàm)"),
    ("FunctionsMathTrigInsertGallery", "TabFormulas", "Math & Trig (nhóm hàm toán học)"),
    ("FunctionsLogicalInsertGallery", "TabFormulas", "Logical (nhóm hàm logic)"),
    ("FunctionsTextInsertGallery", "TabFormulas", "Text (nhóm hàm chuỗi)"),
    ("FunctionsDateTimeInsertGallery", "TabFormulas", "Date & Time (nhóm hàm ngày giờ)"),
    ("FunctionsLookupReferenceInsertGallery", "TabFormulas", "Lookup & Reference (nhóm hàm tra cứu)"),
    # Thẻ Data
    ("SortAscendingExcel", "TabData", "Sort Smallest to Largest (sắp tăng dần)"),
    ("SortDescendingExcel", "TabData", "Sort Largest to Smallest (sắp giảm dần)"),
    ("SortDialog", "TabData", "Sort (hộp thoại sắp xếp)"),
    ("Filter", "TabData", "Filter (bật bộ lọc)"),
    ("SortClear", "TabData", "Clear (bỏ lọc)"),
]

RIBBON: dict[str, RibbonControl] = {c: RibbonControl(c, tab, label) for c, tab, label in _CONTROLS}


def catalog_text() -> str:
    """Danh mục dạng chữ để đưa vào prompt."""
    return "\n".join(f"- {c.control}: {c.label}" for c in RIBBON.values())
