from typing import Dict, List, Tuple

from langchain.text_splitter import RecursiveCharacterTextSplitter


def split_sections_into_chunks(
    sections: List[str],
    chunk_size: int,
    overlap_size: int,
) -> List[Dict[str, str]]:
    """Split sections into chunks."""
    chunks = []
    text_content = "\n".join(sections)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap_size,
        separators=["\n\n", "\n", " "],  # Separators to use for splitting
    )
    text_chunks = text_splitter.split_text(text_content)

    improved_chunks = []
    prev_chunk = ""
    for chunk in text_chunks:
        if prev_chunk and prev_chunk.isupper():  # Keep previous chunk if it's uppercase
            improved_chunks[-1]["chunk"] += "\n" + chunk
        else:
            improved_chunks.append({"chunk": chunk, "metadata": {"type": "text"}})
        prev_chunk = chunk

    # Handle the last chunk separately
    final_chunks = []
    buffer = ""
    for chunk in improved_chunks:
        if chunk["chunk"].strip().startswith(("-", "•", "*")):
            buffer += "\n" + chunk["chunk"]
        else:
            if buffer:
                final_chunks.append({"chunk": buffer, "metadata": {"type": "text"}})
                buffer = ""
            final_chunks.append(chunk)

    if buffer:
        final_chunks.append({"chunk": buffer, "metadata": {"type": "text"}})

    chunks.extend(final_chunks)
    return chunks


def split_tables_into_chunks(
    tables: List[str],
    chunk_size: int,
    overlap_size: int,
) -> List[Dict[str, str]]:
    """Split tables into chunks."""
    chunks = []

    for table in tables:
        # Tách bảng thành các hàng
        rows = table.split("\n")
        # Loại bỏ các hàng rỗng
        rows = [row for row in rows if row.strip()]

        if not rows:
            continue

        # Giả định hàng đầu tiên là tiêu đề (nếu có)
        header = rows[0] if rows else ""
        content_rows = rows[1:] if len(rows) > 1 else []
        num_rows = len(content_rows)

        if num_rows <= chunk_size:
            # Nếu bảng nhỏ, giữ nguyên toàn bộ bảng trong một chunk
            chunk = {
                "chunk": table,
                "metadata": {"type": "table", "header": header, "row_count": num_rows},
            }
            chunks.append(chunk)
        else:
            # Nếu bảng lớn, chia thành các phần
            for i in range(0, num_rows, chunk_size - overlap_size):
                part_rows = content_rows[i : i + chunk_size]
                # Thêm tiêu đề vào mỗi chunk để giữ ngữ cảnh
                part_table = "\n".join([header, *part_rows])
                chunk = {
                    "chunk": part_table,
                    "metadata": {
                        "type": "table",
                        "header": header,
                        "start_row": i + 1,  # Vị trí bắt đầu (bỏ qua tiêu đề)
                        "row_count": len(part_rows),
                    },
                }
                chunks.append(chunk)

    return chunks


def split_text_into_chunks(
    data: Dict[str, List[str]],
    chunk_size: int,
    overlap_size: int,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Gọi hai hàm chunking riêng biệt cho văn bản và bảng."""
    sections = data.get("sections", [])
    tables = data.get("tables", [])

    text_chunks = split_sections_into_chunks(sections, chunk_size, overlap_size)
    table_chunks = split_tables_into_chunks(tables, chunk_size, overlap_size)

    return text_chunks, table_chunks
