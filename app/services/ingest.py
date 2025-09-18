import hashlib
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from fastapi import UploadFile
from loguru import logger

from app.data_loader import read_document
from app.db.dependencies import pg_client
from app.db.models import PgVectorCollection
from app.text_splitter import split_text_into_chunks
from app.utils.openai_connect import embed

CHUNK_SIZE = 1440
OVERLAP_SIZE = 256
DIMENSION = 1536


def clean_html_table(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" | ")


def extract_title_from_sections(sections: List[str]) -> Optional[str]:
    for line in sections:
        match = re.match(r"#\s*(.+)", line)
        if match:
            return match.group(1).strip()
    return None


class IngestService:
    def __init__(self, client: pg_client) -> None:
        self.client = client
        self.batch_size = 32

    async def ingest_multiple(
        self,
        collection_name: str,
        files: List[UploadFile],
    ) -> None:
        for file in files:
            await self.ingest_single(collection_name, file)

    async def ingest_single(self, collection_name: str, file: UploadFile) -> None:
        sections, tables = self.parse_document(file)
        doc_title = extract_title_from_sections(sections)

        data_chunks = {
            "sections": sections,
            "tables": tables,
        }

        section_texts, table_texts = self.chunking(
            data_chunks,
            CHUNK_SIZE,
            OVERLAP_SIZE,
        )

        if section_texts:
            await self.insert_data(
                collection_name,
                DIMENSION,
                section_texts,
                "section",
                file.filename,
                doc_title,
            )
        if table_texts:
            await self.insert_data(
                collection_name,
                DIMENSION,
                table_texts,
                "table",
                file.filename,
                doc_title,
            )

    def parse_document(self, file: UploadFile) -> str:
        sections, tables = read_document(file)
        return sections, tables

    def chunking(self, data_chunks: dict, chunk_size: int, overlap_size: int) -> str:
        section_texts, table_texts = split_text_into_chunks(
            data_chunks,
            chunk_size,
            overlap_size,
        )
        return section_texts, table_texts

    async def insert_data(
        self,
        collection_name: str,
        dimension: int,
        data: list,
        data_type: str,
        file_name: Optional[str] = None,
        title_from_doc: Optional[str] = None,
    ) -> None:
        collection = await self.get_collection(collection_name, dimension)

        title_pattern = re.compile(r"#\s*(.+)")
        extracted_title = None
        for chunk in data:
            match = title_pattern.search(chunk["chunk"])
            if match:
                extracted_title = match.group(1).strip()
                break

        for chunk in data:
            text_content = chunk["chunk"]
            chunk_id = hashlib.md5(text_content.encode()).hexdigest()  # noqa: S324

            try:
                existing_record = await collection.get(chunk_id)
            except ValueError:
                existing_record = None

            if existing_record is None:
                # Làm sạch bảng nếu cần
                if data_type == "table":
                    text_content_clean = clean_html_table(text_content)
                else:
                    text_content_clean = text_content

                # Dùng title từ chunk, nếu không có thì fallback từ doc
                title = (
                    extracted_title or title_from_doc or f"{data_type} from {file_name}"
                )

                # Gộp title + content để embedding
                text_for_embedding = f"{title}\n{text_content_clean}"

                is_success, embeddings, usage = embed([text_for_embedding])
                if not is_success:
                    raise ValueError("Failed to embed chunk")

                payload = {
                    "content": text_content,
                    "type": data_type,
                    "source": file_name,
                    "title": title,
                }
                if "metadata" in chunk:
                    payload.update(chunk["metadata"])

                await collection.upsert(
                    id=chunk_id,
                    embedding=embeddings[0],
                    payload=payload,
                )

    async def get_collection(
        self,
        collection_name: str,
        dimension: int,
    ) -> PgVectorCollection:
        try:
            return await self.client.get_or_create_collection(
                collection_name,
                dimension,
            )
        except Exception as e:
            logger.exception(e)
            raise e
