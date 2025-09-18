from typing import List


def read_xlsx_file(response_data: dict) -> List[str]:
    """Convert file to html table format."""
    sections = response_data.get("sections", [])
    section = []
    tables = []
    current_table_rows = []
    current_caption = None

    for row in sections:
        if row and isinstance(row, list) and row[0]:
            # Lấy nội dung của hàng, tách theo dấu ";" và loại bỏ tiền tố "None："
            content = row[0]
            cells = [cell.replace("None：", "").strip() for cell in content.split(";")]
            # Nếu dòng có 1 ô hoặc các ô sau ô đầu đều rỗng -> coi là dòng caption
            if len(cells) == 1 or all(cell == "" for cell in cells[1:]):
                # Nếu đã có dữ liệu của một bảng trước đó thì xuất bảng hiện hành
                if current_table_rows:
                    table_html = "<table>\n"
                    if current_caption:
                        table_html += f"<caption>{current_caption}</caption>\n"
                    for table_row in current_table_rows:
                        table_html += (
                            "<tr>"
                            + "".join(f"<td>{cell}</td>" for cell in table_row)
                            + "</tr>\n"
                        )
                    table_html += "</table>"
                    tables.append(table_html)
                    current_table_rows = []
                # Cập nhật caption mới cho bảng hiện hành
                current_caption = cells[0]
            else:
                # Dòng bình thường, thêm vào bảng hiện hành
                current_table_rows.append(cells)

    # Xuất bảng cuối nếu còn dữ liệu
    if current_table_rows:
        table_html = "<table>\n"
        if current_caption:
            table_html += f"<caption>{current_caption}</caption>\n"
        for table_row in current_table_rows:
            table_html += (
                "<tr>" + "".join(f"<td>{cell}</td>" for cell in table_row) + "</tr>\n"
            )
        table_html += "</table>"
        tables.append(table_html)

    return section, tables
