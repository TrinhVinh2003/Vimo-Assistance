import re
from urllib.parse import urlparse

from app.schemas.crawl_schema import CrawlResponse


class BaseParser:
    @staticmethod
    def convert_to_absolute_url(relative_url: str, base_url: str) -> str:
        if relative_url.startswith("/"):
            base_url_parsed = "{0.scheme}://{0.netloc}".format(urlparse(base_url))
            return base_url_parsed + relative_url
        return relative_url

    @staticmethod
    def parse_generic(soup, url: str) -> CrawlResponse:  # noqa: ANN001
        # Extract title
        title = ""
        title_tag = soup.find("h1") or soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()

        # Extract description
        description = ""
        desc_meta = soup.find("meta", {"name": "description"}) or soup.find(
            "meta",
            {"property": "og:description"},
        )
        if desc_meta:
            description = desc_meta.get("content", "").strip()
        else:
            # Try to get first paragraph
            first_p = soup.find("p")
            if first_p:
                description = first_p.get_text().strip()

        # Try to find price (common patterns)
        price = None
        price_patterns = [
            soup.find(
                "span",
                class_=lambda c: c and ("price" in c.lower() or "cost" in c.lower()),
            ),
            soup.find(
                "div",
                class_=lambda c: c and ("price" in c.lower() or "cost" in c.lower()),
            ),
            soup.find(
                "p",
                class_=lambda c: c and ("price" in c.lower() or "cost" in c.lower()),
            ),
        ]

        for pattern in price_patterns:
            if pattern:
                price_text = pattern.get_text().strip()
                # Try to extract numeric price with currency symbol
                price_match = re.search(r"[\$\€\£\¥]?\s*[0-9,.]+", price_text)
                if price_match:
                    price = price_match.group(0)
                    break

        # Extract media files
        media_files = []

        # Find images
        images = soup.find_all("img")
        for img in images:
            src = img.get("src", "") or img.get("data-src", "")
            if src and (src.startswith(("http://", "https://", "/"))):
                if src.startswith("/"):
                    src = BaseParser.convert_to_absolute_url(src, url)
                media_files.append(src)

        # Find videos
        videos = soup.find_all("video")
        for video in videos:
            src = video.get("src", "")
            if src and (src.startswith(("http://", "https://", "/"))):
                if src.startswith("/"):
                    src = BaseParser.convert_to_absolute_url(src, url)
                media_files.append(src)

        # Find video iframes (YouTube, etc)
        iframes = soup.find_all("iframe")
        for iframe in iframes:
            src = iframe.get("src", "")
            if src and (src.startswith(("http://", "https://", "/"))):
                if src.startswith("/"):
                    src = BaseParser.convert_to_absolute_url(src, url)
                media_files.append(src)

        # Try to determine currency
        currency = None
        if price:
            if "$" in price:
                currency = "USD"
            elif "€" in price:
                currency = "EUR"
            elif "£" in price:
                currency = "GBP"
            elif "¥" in price:
                currency = "JPY"
            elif "đ" in price.lower() or "vnd" in price.lower():
                currency = "VND"

        return CrawlResponse(
            title=title,
            description=description,
            media_files=media_files,
            price=price,
            currency=currency,
        )
