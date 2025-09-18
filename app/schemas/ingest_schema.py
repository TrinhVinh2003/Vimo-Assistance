from typing import Optional

from pydantic import BaseModel, field_validator


class FileMetadata(BaseModel):
    filename: str
    content_type: Optional[str]
    size: int

    @field_validator("content_type")
    def validate_content_type(cls, value):
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/csv",
            "text/markdown",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]
        if value not in allowed_types:
            raise ValueError("Unsupported file type")
        return value

    @field_validator("size")
    def validate_size(cls, value):
        max_size = 15 * 1024 * 1024  # 15 MB
        if value > max_size:
            raise ValueError(
                f"File size exceeds the limit of {max_size // 1024 // 1024} MB"
            )
        return value


class IngestRequest(BaseModel):
    chunk_size: int = 256
    overlap_size: int = 64
    dimension: int = 1536
    chunking_strategy: str = "fixed_size"

    @field_validator("chunk_size")
    def validate_chunk_size(cls, value):
        if value <= 0:
            raise ValueError("chunk_size must be greater than 0")
        return value

    @field_validator("dimension")
    def validate_dimension(cls, value):
        if value <= 0:
            raise ValueError("dimension must be greater than 0")
        return value

    @field_validator("overlap_size")
    def validate_overlap_size(cls, value):
        if value < 0:
            raise ValueError("overlap_size cannot be negative")
        return value
