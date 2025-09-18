import os
from typing import Generator
from urllib.parse import urljoin

import requests

TIMEOUT = 20

def get_base_url() -> str:
    """Get base URL from environment variables."""
    service_url = os.environ.get("SERVICE_URL")
    if service_url:
        return service_url

    api_host = os.getenv("API_HOST", "api")
    api_port = os.getenv("API_PORT", "8000")
    return f"http://{api_host}:{api_port}"


def chat_stream_completion(model: str, message: str, session_id: str) -> Generator:
    base_url = get_base_url()
    endpoint = "/api/answer"
    chat_url = urljoin(base_url, endpoint)

    headers = {"Accept": "application/x-ndjson"}
    data = {
        "model": model,
        "query": message,
        "session_id": session_id,
    }
    try:
        response = requests.get(
            chat_url,
            params=data,
            headers=headers,
            stream=True,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        print(f"Attempted URL: {chat_url}")
        raise


def upload_file_to_api(files) -> dict:
    """Upload multiple files to API for ingestion"""
    base_url = get_base_url()
    endpoint = "/api/ingest"
    ingest_url = urljoin(base_url, endpoint)

    try:
        if not isinstance(files, list):
            files = [files]

        files_payload = []
        for file in files:
            if hasattr(file, "name") and hasattr(file, "getvalue"):
                ext = file.name.split(".")[-1].lower()
                content_type_map = {
                    "pdf": "application/pdf",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "md": "text/markdown",
                    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                }
                mime_type = content_type_map.get(ext, "application/octet-stream")

                # ✅ Sửa ở đây: dùng đúng biến `file`
                files_payload.append(("files", (file.name, file.getvalue(), mime_type)))
            else:
                raise ValueError(f"Invalid file object: {file}")

        headers = {"Accept": "application/json"}

        response = requests.post(
            ingest_url,
            files=files_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error uploading files: {e}")
        raise
