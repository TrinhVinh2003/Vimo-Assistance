from typing import List, Optional

from pydantic import BaseModel


class CrawlResponse(BaseModel):
    """The response model for the crawl service."""

    title: str
    description: Optional[str] = None
    media_files: List[str] = []
    price: Optional[str] = None
    currency: Optional[str] = None
