"""Đọc vị trí ô gộp từ XML Spreadsheet 2003 (Range.Value(11)) — chạy không cần Excel."""

from excel_core.readers.com_reader import merge_starts

XML = """<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="S">
  <Table ss:ExpandedColumnCount="6" ss:ExpandedRowCount="4">
   <Row><Cell ss:MergeAcross="2"><Data ss:Type="String">Tiêu đề</Data></Cell><Cell/></Row>
   <Row ss:Index="3"><Cell ss:Index="2" ss:MergeDown="1"/><Cell ss:MergeAcross="1" ss:MergeDown="1"/></Row>
   <Row><Cell ss:Index="5" ss:MergeAcross="1"/></Row>
  </Table>
 </Worksheet>
</Workbook>"""


def test_merge_starts_follows_index_and_merge_across():
    # A1:C1 (ô sau là D1), B3:B4, C3:D4, rồi dòng 4 bỏ qua các ô bị gộp dọc từ dòng 3 bằng ss:Index
    assert list(merge_starts(XML)) == [(1, 1), (3, 2), (3, 3), (4, 5)]


def test_merge_starts_without_table_is_empty():
    empty = '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet/></Workbook>'
    assert list(merge_starts(empty)) == []
