from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from loguru import logger
from pydantic import BaseModel, HttpUrl

from app.services.crawl import CrawlService

router = APIRouter()


class CrawlRequest(BaseModel):
    url: HttpUrl


class CrawlResponse(BaseModel):
    title: str
    description: Optional[str] = None
    media_files: list[str] = []


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_url(
    request: CrawlRequest,
    crawl_service: CrawlService = Depends(),
) -> CrawlResponse:
    try:
        result = await crawl_service.crawl_url(str(request.url))
        return result
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from None
