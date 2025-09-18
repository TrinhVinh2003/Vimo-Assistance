import os

from fastapi.responses import FileResponse
from fastapi.routing import APIRouter

from app.core.settings import settings
from app.web.api import chat, crawl, echo, ingest_api, monitoring

api_router = APIRouter()
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(echo.router, prefix="/echo", tags=["echo"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(ingest_api.router, tags=["ingest"])
api_router.include_router(crawl.router, tags=["crawl"])


@api_router.get("/<filename>")
async def save_media(filename: str) -> FileResponse:
    """Download a file from the media directory.

    Args:
        filename (str): The name of the file to download.

    Returns:
        FileResponse: The file to download.
    """
    file_path = os.path.join(settings.media_dir_static, filename)

    return FileResponse(
        file_path,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
