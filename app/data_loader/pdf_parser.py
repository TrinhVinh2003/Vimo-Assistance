from typing import List, Tuple


def read_pdf_file(response_data: dict) -> Tuple[List[str], List[str]]:
    sections_data = response_data.get("sections", [])
    text_sections = []
    table_sections = []

    for section in sections_data:
        # Mỗi section được giả định là list, phần tử đầu tiên chứa nội dung text
        if isinstance(section, list) and section:
            content = section[0]
            # Nếu content là chuỗi và bắt đầu với <table, ta coi đó là table
            if isinstance(content, str) and content.strip().startswith("<table"):
                table_sections.append(content)
            else:
                text_sections.append(content)
    return text_sections, table_sections
