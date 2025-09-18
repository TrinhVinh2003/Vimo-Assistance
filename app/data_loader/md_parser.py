import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup


def read_md_file(response_data: dict) -> Tuple[List[str], List[str]]:
    """Extracts text from sections and tables in a DOCX file."""
    sections_raw = response_data.get("sections", [])
    section_texts = []
    for section in sections_raw:
        if isinstance(section, list) and len(section) > 0 and section[0]:
            section_texts.append(section[0])

    tables_raw = response_data.get("tables", [])
    table_texts = []
    for table in tables_raw:
        if isinstance(table, list) and len(table) > 0:
            first_item = table[0]
            if isinstance(first_item, list) and len(first_item) > 1 and first_item[1]:
                table_texts.append(first_item[1])
            elif isinstance(first_item, str):
                table_texts.append(first_item)
    return section_texts, table_texts


def clean_html_table(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" | ")


def extract_title_from_sections(sections: List[str]) -> Optional[str]:
    for line in sections:
        match = re.match(r"#\s*(.+)", line)
        if match:
            return match.group(1).strip()
    return None
