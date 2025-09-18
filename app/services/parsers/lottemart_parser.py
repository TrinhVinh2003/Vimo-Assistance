import re

from app.schemas.crawl_schema import CrawlResponse
from app.services.parsers.base_parser import BaseParser


class LotteMartParser(BaseParser):
    @staticmethod
    def parse(soup, url: str):
        # Extract title - Lotte Mart typically has product titles in h1 with class page-title
        title = ""

        # Directly target the h1 with class page-title
        product_title = soup.select_one("h1.page-title")
        if product_title:
            title = product_title.get_text().strip()

        # If not found or title is empty, try other selectors
        if not title or title == "LOTTE Mart":
            # Try to find the product title in the page-title-wrapper
            page_title_wrapper = soup.find("div", class_="page-title-wrapper")
            if page_title_wrapper:
                h1_tag = page_title_wrapper.find("h1")
                if h1_tag:
                    title = h1_tag.get_text().strip()

        # If still not found, try other common title locations
        if not title or title == "LOTTE Mart":
            # Try to find any h1 that contains the product name
            all_h1s = soup.find_all("h1")
            for h1 in all_h1s:
                h1_text = h1.get_text().strip()
                if h1_text and h1_text != "LOTTE Mart" and len(h1_text) > 5:
                    title = h1_text
                    break

        # If still not found, try meta tags
        if not title or title == "LOTTE Mart":
            meta_title = soup.find("meta", {"property": "og:title"})
            if meta_title and meta_title.get("content"):
                title = meta_title.get("content").strip()

        # Extract description
        description = ""

        # First try to get the product description from the "Đặc điểm sản phẩm" section
        dac_diem_section = None
        for heading in soup.find_all(["h2", "h3", "h4"]):
            if "Đặc điểm sản phẩm" in heading.get_text().strip():
                dac_diem_section = heading
                break

        if dac_diem_section:
            # Get the first paragraph after this heading
            next_elem = dac_diem_section.find_next("p")
            if next_elem:
                description = next_elem.get_text().strip()

        # If not found, try to get description from the list items under "Mô tả ngắn"
        if not description or description == "Xem thêm":
            mo_ta_ngan_heading = None
            for heading in soup.find_all(["h3", "h4"]):
                if "Mô tả ngắn" in heading.get_text().strip():
                    mo_ta_ngan_heading = heading
                    break

            if mo_ta_ngan_heading:
                # Look for list items after the heading
                list_items = []
                next_elem = mo_ta_ngan_heading.find_next()

                # Find the first ul/ol after the heading
                while next_elem and next_elem.name not in ["ul", "ol"]:
                    next_elem = next_elem.find_next()

                # If we found a list, get all its items
                if next_elem and next_elem.name in ["ul", "ol"]:
                    list_items = next_elem.find_all("li")
                    if list_items:
                        description = " ".join(
                            [li.get_text().strip() for li in list_items],
                        )

        # If still not found, try to get from the product details section
        if not description or description == "Xem thêm":
            product_details = soup.find("div", class_="product attribute description")
            if product_details:
                paragraphs = product_details.find_all("p")
                if paragraphs:
                    description = " ".join(
                        [p.get_text().strip() for p in paragraphs[:2]],
                    )

        # Extract price
        price = None

        # Look for special price (discounted price)
        special_price_elem = soup.select_one("span.special-price span.price")
        if special_price_elem:
            price = special_price_elem.get_text().strip()

        # If no special price, look for regular price
        if not price:
            regular_price_elem = soup.select_one(
                "span.regular-price span.price, span.price",
            )
            if regular_price_elem:
                price = regular_price_elem.get_text().strip()

        # If still not found, try to find any element with price and ₫ symbol
        if not price:
            for elem in soup.find_all(text=re.compile(r"[\d,.]+\s*₫")):
                price_match = re.search(r"[\d,.]+\s*₫", elem)
                if price_match:
                    price = price_match.group(0).strip()
                    break

        # Extract media files
        media_files = []

        # Method 1: Find product images in the fotorama gallery
        fotorama = soup.find("div", class_="fotorama")
        if fotorama:
            # Look for images in the gallery
            gallery_imgs = fotorama.find_all("img")
            for img in gallery_imgs:
                src = (
                    img.get("src", "")
                    or img.get("data-src", "")
                    or img.get("data-lazy", "")
                )
                if src and (src.startswith(("http://", "https://", "/"))):
                    if src.startswith("/"):
                        src = BaseParser.convert_to_absolute_url(src, url)
                    if src not in media_files:
                        media_files.append(src)

        # Method 2: Look for thumbnails
        thumbnails = soup.select("img.product-image-photo, img.thumbnail")
        for img in thumbnails:
            src = img.get("src", "") or img.get("data-src", "")
            if src and (src.startswith(("http://", "https://", "/"))):
                if src.startswith("/"):
                    src = BaseParser.convert_to_absolute_url(src, url)
                if src not in media_files:
                    media_files.append(src)

        # Method 3: Look for images in the product media section
        product_media = soup.find("div", class_="product media")
        if product_media:
            imgs = product_media.find_all("img")
            for img in imgs:
                src = img.get("src", "") or img.get("data-src", "")
                if src and (src.startswith(("http://", "https://", "/"))):
                    if src.startswith("/"):
                        src = BaseParser.convert_to_absolute_url(src, url)
                    if src not in media_files:
                        media_files.append(src)

        # Method 4: Look for any image that might be a product image
        if not media_files:
            all_images = soup.find_all("img")
            for img in all_images:
                src = img.get("src", "") or img.get("data-src", "")
                if src and (src.startswith(("http://", "https://", "/"))):  # noqa: SIM102, E501
                    # Filter for likely product images
                    if (
                        "product" in src.lower()
                        or "catalog" in src.lower()
                        or "/media/" in src.lower()
                        or ".webp" in src.lower()
                        or ".jpg" in src.lower()
                    ):
                        if src.startswith("/"):
                            src = BaseParser.convert_to_absolute_url(src, url)
                        if src not in media_files:
                            media_files.append(src)

        # Method 5: Look for meta tags with image information
        if not media_files:
            og_image = soup.find("meta", {"property": "og:image"})
            if og_image:
                src = og_image.get("content", "")
                if src and (src.startswith(("http://", "https://", "/"))):
                    if src.startswith("/"):
                        src = BaseParser.convert_to_absolute_url(src, url)
                    if src not in media_files:
                        media_files.append(src)

        # Currency is VND for Lotte Mart Vietnam
        currency = "VND"

        return CrawlResponse(
            title=title,
            description=description,
            media_files=media_files,
            price=price,
            currency=currency,
        )
