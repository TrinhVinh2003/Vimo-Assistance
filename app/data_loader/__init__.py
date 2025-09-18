from io import BytesIO
from typing import Any, Dict

import requests
from fastapi import UploadFile
from loguru import logger

from app.data_loader.docx_parser import read_docx_file
from app.data_loader.md_parser import read_md_file
from app.data_loader.pdf_parser import read_pdf_file
from app.data_loader.pptx_parser import read_pptx_file
from app.data_loader.xlsx_parser import read_xlsx_file

DEEPDOCS_API_URL = "https://3d4f-113-190-253-97.ngrok-free.app/api/parser/upload"


def call_deepdocs_api(file: UploadFile, file_extension: str) -> Dict[str, Any]:
    """Gửi tài liệu đến API DeepDocs và nhận kết quả."""

    # Xác định parser_type dựa trên định dạng file
    parser_type = "manual" if file_extension == "pdf" else "general"
    headers = {"accept": "application/json"}
    data = {
        "parser_type": parser_type,
        "from_page": "0",
        "to_page": "100000",
        "parser_config": '{"chunk_token_num":128}',
    }
    file_content = file.file.read()
    file.file.seek(0)  # Reset lại con trỏ file
    files = {"file": (file.filename, BytesIO(file_content), file.content_type)}

    try:
        response = requests.post(
            DEEPDOCS_API_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=60,
        )
        response.raise_for_status()

        # Kiểm tra response có phải là JSON không
        try:
            json_data = response.json()
            if not isinstance(json_data, dict):
                logger.error(
                    "DeepDocs API returned an invalid format (not a dictionary)",
                )
                return {"sections": [], "tables": []}
            return json_data
        except ValueError:
            logger.error("Failed to parse JSON from DeepDocs API response")
            return {"sections": [], "tables": []}

    except requests.RequestException as e:
        logger.error(f"DeepDocs API request failed: {e}")
        return {"sections": [], "tables": []}


def read_document(file: UploadFile) -> str:
    file_type = file.filename.split(".")[-1].lower()
    response_data = call_deepdocs_api(file, file_type)

    # Kiểm tra nếu response_data không phải dictionary
    if not isinstance(response_data, dict):
        logger.error("DeepDocs API response is not a valid dictionary")
        return {"sections": [], "tables": []}

    if file_type == "pdf":
        sections, tables = read_pdf_file(response_data)
    elif file_type == "docx":
        sections, tables = read_docx_file(response_data)
    elif file_type == "md":
        sections, tables = read_md_file(response_data)
    elif file_type == "xlsx":
        sections, tables = read_xlsx_file(response_data)
    elif file_type == "pptx":
        sections, tables = read_pptx_file(response_data)

    return sections, tables
