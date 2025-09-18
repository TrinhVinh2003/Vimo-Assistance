import mimetypes
import os
from typing import Annotated, Optional

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from loguru import logger

from app.schemas.ingest_schema import FileMetadata
from app.schemas.retrieval_schema import RetrievalResponse
from app.services.ingest import IngestService
from app.services.retrieval import RetrievalService

router = APIRouter()
COLLECTION_NAME = "vimo_documents"


@router.post("/ingest")
async def ingest_data(
    files: Annotated[
        list[UploadFile],
        File(description="Multiple files as UploadFile"),
    ],
    ingest_service: IngestService = Depends(),
) -> JSONResponse:
    """Handle file ingestion with MIME type validation and metadata construction."""
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ]

    file_metadata_list = []

    for file in files:
        custom_content_type = file.content_type

        if file.content_type == "application/octet-stream" or not file.content_type:
            guessed_type, _ = mimetypes.guess_type(file.filename)
            if guessed_type:
                custom_content_type = guessed_type
            else:
                file_extension = file.filename.split(".")[-1].lower()
                content_type_map = {
                    "md": "text/markdown",
                    "pdf": "application/pdf",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # noqa: E501
                    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
                    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # noqa: E501
                }
                custom_content_type = content_type_map.get(
                    file_extension,
                    "application/octet-stream",
                )

        if custom_content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file type: {custom_content_type} ({file.filename})"
                ),
            )

        metadata = FileMetadata(
            filename=file.filename,
            content_type=custom_content_type,
            size=file.file.seek(0, os.SEEK_END) or file.file.tell(),
        )
        file.file.seek(0)
        file_metadata_list.append(metadata)

    logger.info(
        "Processing {} files: {}",
        len(files),
        [meta.filename for meta in file_metadata_list],
    )

    try:
        await ingest_service.ingest_multiple(COLLECTION_NAME, files)
        return JSONResponse(content={"message": "All files ingested successfully"})
    except Exception as e:
        logger.exception("Error while ingesting files", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/search")
async def search_data(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
    rerank: bool = True,
    source: Optional[str] = None,
    retrieval_service: RetrievalService = Depends(),
) -> RetrievalResponse:
    try:
        records = await retrieval_service.hybrid_search(
            query=query,
            collection_name=COLLECTION_NAME,
            top_k_semantic=top_k,
            top_k_keyword=top_k,
            score_threshold=score_threshold,
            rerank=rerank,
            top_n=top_k,
            filter_source=source,
        )
        return RetrievalResponse(records=records)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/get_all")
async def get_all_data(
    retrieval_service: RetrievalService = Depends(),
) -> JSONResponse:
    try:
        records = await retrieval_service.get_all_chunks(
            collection_name=COLLECTION_NAME,
        )
        records = [
            {
                "id": record.id,
                "embedding": record.embedding,
                "payload": record.payload,
            }
            for record in records
        ]
        return JSONResponse(content={"records": records})
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/remove_all")
async def remove_all_data(
    retrieval_service: RetrievalService = Depends(),
) -> JSONResponse:
    """Delete all chunks from the collection."""
    try:
        deleted_count = await retrieval_service.delete_all_chunks(
            collection_name=COLLECTION_NAME,
        )
        return JSONResponse(content={"message": f"Successfully deleted {deleted_count} chunks"})
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from None
