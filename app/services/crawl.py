import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.schemas.crawl_schema import CrawlResponse
from app.services.parsers import (
    AmazonParser,
    BaseParser,
    BonbanhParser,
    LotteMartParser,
    ShopeeParser,
)


class CrawlService:
    def __init__(self) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa: E501
        }
        self.logger = logging.getLogger(__name__)

    async def crawl_url(self, url: str) -> CrawlResponse:
        try:
            # Fetch the webpage
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Determine which site we're crawling
            domain = urlparse(url).netloc

            if "shopee" in domain:
                return ShopeeParser.parse(soup, url)
            elif "amazon" in domain:
                return AmazonParser.parse(soup, url)
            elif "lottemart.vn" in domain:
                return LotteMartParser.parse(soup, url)
            elif "bonbanh.com" in domain:
                return BonbanhParser.parse(soup, url)
            else:
                # Generic parser for other sites
                return BaseParser.parse_generic(soup, url)

        except requests.RequestException as e:
            self.logger.error(f"Error fetching URL: {e!s}")
            raise Exception(f"Error fetching URL: {e!s}") from e
        except Exception as e:
            self.logger.error(f"Error processing content: {e!s}")
            raise Exception(f"Error processing content: {e!s}") from e
