from app.schemas.crawl_schema import CrawlResponse
from app.services.parsers.base_parser import BaseParser


class AmazonParser(BaseParser):
    @staticmethod
    def parse(soup, url: str):
        # Extract title
        title = ""
        title_tag = soup.find("span", {"id": "productTitle"}) or soup.find(
            "meta",
            {"property": "og:title"},
        )
        if title_tag:
            if hasattr(title_tag, "get_text"):
                title = title_tag.get_text().strip()
            else:
                title = title_tag.get("content", "").strip()

        # Extract description
        description = ""
        desc_div = soup.find("div", {"id": "productDescription"})
        if desc_div:
            description = desc_div.get_text().strip()
        else:
            desc_meta = soup.find("meta", {"name": "description"})
            if desc_meta:
                description = desc_meta.get("content", "").strip()

        # Extract price
        price = None
        price_tag = soup.find("span", {"id": "priceblock_ourprice"}) or soup.find(
            "span",
            class_="a-offscreen",
        )
        if price_tag:
            price = price_tag.get_text().strip()

        # Extract media files
        media_files = []

        # Find main product image
        main_img = soup.find("img", {"id": "landingImage"})
        if main_img:
            src = main_img.get("src", "") or main_img.get("data-old-hires", "")
            if src and src.startswith(("http://", "https://")):
                media_files.append(src)

        # Find thumbnail images
        thumbnails = soup.find_all("img", class_="imageThumbnail")
        for img in thumbnails:
            src = img.get("src", "")
            if src and src.startswith(("http://", "https://")):
                media_files.append(src)

        # Determine currency
        currency = "USD"  # Default for Amazon.com
        if "amazon.co.uk" in url:
            currency = "GBP"
        elif (
            "amazon.de" in url
            or "amazon.fr" in url
            or "amazon.it" in url
            or "amazon.es" in url
        ):
            currency = "EUR"

        return CrawlResponse(
            title=title,
            description=description,
            media_files=media_files,
            price=price,
            currency=currency,
        )
