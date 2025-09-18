import re
from urllib.parse import unquote, urlparse

from app.schemas.crawl_schema import CrawlResponse
from app.services.parsers.base_parser import BaseParser


class ShopeeParser(BaseParser):
    @staticmethod
    def parse(soup, url: str):
        # Shopee uses a lot of JavaScript, so basic scraping might be limited
        title = ""

        # Method 1: Try to find title in meta tags (most reliable for Shopee)
        meta_title_tags = [
            soup.find("meta", {"property": "og:title"}),
            soup.find("meta", {"name": "title"}),
            soup.find("meta", {"property": "twitter:title"}),
        ]

        for tag in meta_title_tags:
            if tag and tag.get("content"):
                title = tag.get("content", "").strip()
                if title:
                    break

        # Description - Enhanced methods for Shopee
        description = ""

        # Method 1: Look for the product description section with class "I_DV_3"
        # (from provided HTML)
        product_desc_section = soup.find("section", class_="I_DV_3")
        if product_desc_section:
            # Find the paragraph with class "QN2lPu" that contains the description
            desc_paragraph = product_desc_section.find("p", class_="QN2lPu")
            if desc_paragraph:
                description = desc_paragraph.get_text().strip()

        # Method 2: If not found, try to find description in meta tags
        if not description:
            meta_desc_tags = [
                soup.find("meta", {"property": "og:description"}),
                soup.find("meta", {"name": "description"}),
                soup.find("meta", {"property": "twitter:description"}),
            ]

            for tag in meta_desc_tags:
                if tag and tag.get("content"):
                    description = tag.get("content", "").strip()
                    if description:
                        break

        # Method 3: Look for specific product description sections with updated class
        if (
            not description or len(description) < 50
        ):  # If description is too short, try to find a better one
            desc_selectors = [
                soup.find("div", class_="_1MqFJA"),  # Product description class
                soup.find("div", class_="hrLIVO"),  # Another description class
                soup.find("div", class_="_2jrvqA"),  # New description class
                soup.find(
                    "div",
                    class_="Gf4Ro0",
                ),  # New description container class from provided HTML
                soup.find(
                    "div",
                    class_="e8lZp3",
                ),  # Another description container class from provided HTML
                soup.find("div", class_="product-detail"),
                soup.find("div", class_="product-detail__wrapper"),
                soup.find("div", class_="_2u0jt9"),  # Another description container
                soup.find("div", class_="_3yZnxJ"),  # Product details section
                soup.find(
                    "div",
                    class_=lambda c: c
                    and ("product-detail" in c.lower() or "description" in c.lower()),
                ),
            ]

            for selector in desc_selectors:
                if selector:
                    desc_text = selector.get_text().strip()
                    if desc_text and len(desc_text) > len(description):
                        description = desc_text

        # Method 4: Look for sections with specific headings like "MÔ TẢ SẢN PHẨM"
        if not description or len(description) < 50:
            product_desc_headings = [
                "MÔ TẢ SẢN PHẨM",
                "CHI TIẾT SẢN PHẨM",
                "THÔNG TIN SẢN PHẨM",
                "Mô tả sản phẩm",
                "Chi tiết sản phẩm",
            ]

            for heading_text in product_desc_headings:
                # Look for elements containing this heading text
                heading_elements = soup.find_all(text=lambda t: t and heading_text in t)  # noqa: B023, E501

                for element in heading_elements:
                    parent = element.parent
                    if parent:
                        # Try to get the next sibling or parent's next sibling
                        next_elem = parent.find_next_sibling()
                        if next_elem:
                            desc_text = next_elem.get_text().strip()
                            if desc_text and len(desc_text) > len(description):
                                description = desc_text
                                break

                        # If no suitable next sibling, try to get all text after this
                        # heading within the same container
                        container = parent.parent
                        if container:
                            # Get all text nodes after this heading
                            found_heading = False
                            desc_parts = []

                            for child in container.children:
                                if found_heading:
                                    if hasattr(child, "get_text"):
                                        desc_parts.append(child.get_text().strip())
                                    elif isinstance(child, str) and child.strip():
                                        desc_parts.append(child.strip())
                                elif child == parent or (
                                    hasattr(child, "find")
                                    and child.find(
                                        text=lambda t: t and heading_text in t,  # noqa: B023, E501
                                    )
                                ):
                                    found_heading = True

                            if desc_parts:
                                combined_desc = " ".join(desc_parts)
                                if len(combined_desc) > len(description):
                                    description = combined_desc
                                    break

        # Method 5: Look for h2 with class "WjNdTR" (MÔ TẢ SẢN PHẨM heading) and extract
        # content from its parent section
        if not description or len(description) < 50:
            desc_heading = soup.find("h2", class_="WjNdTR")
            if desc_heading and "MÔ TẢ SẢN PHẨM" in desc_heading.get_text():
                parent_section = desc_heading.parent
                if parent_section:
                    # Get all paragraphs in this section
                    paragraphs = parent_section.find_all("p")
                    if paragraphs:
                        desc_text = " ".join([p.get_text().strip() for p in paragraphs])
                        if len(desc_text) > len(description):
                            description = desc_text

        # Media files - Improved methods based on the provided HTML structure
        media_files = []

        # Method 1: Extract from the product image section with class "_OguPS"
        product_image_section = soup.find("section", class_="_OguPS")
        if product_image_section:
            # Find all picture elements within the section
            pictures = product_image_section.find_all("picture", class_="UkIsx8")
            for picture in pictures:
                # Try to get the image from source element first (higher quality)
                source = picture.find("source")
                if source and source.get("srcset"):
                    srcset = source.get("srcset")
                    # Extract the first URL from srcset (before the space)
                    src_match = re.search(r"(https?://[^\s]+)", srcset)
                    if src_match:
                        img_url = src_match.group(1)
                        if img_url and img_url not in media_files:
                            media_files.append(img_url)
                            continue

                # If no source or failed to extract, try the img element
                img = picture.find("img")
                if img:
                    src = img.get("src", "") or img.get("data-src", "")
                    if (
                        src
                        and src.startswith(("http://", "https://"))
                        and src not in media_files
                    ):
                        media_files.append(src)

        # Method 2: Look for thumbnails in the product gallery
        thumbnails_div = soup.find("div", class_="airUhU")
        if thumbnails_div:
            thumbnails = thumbnails_div.find_all("img", class_="raRnQV")
            for img in thumbnails:
                src = img.get("src", "") or img.get("data-src", "")
                if (
                    src
                    and src.startswith(("http://", "https://"))
                    and src not in media_files
                ):
                    # Get the high-resolution version by removing resize parameters
                    high_res_src = re.sub(r"@resize_w\d+_nl.*$", "", src)
                    if high_res_src and high_res_src not in media_files:
                        media_files.append(high_res_src)

        # Method 3: Try to get product images from meta tags
        if not media_files:
            meta_image_tags = [
                soup.find("meta", {"property": "og:image"}),
                soup.find("meta", {"property": "og:image:secure_url"}),
                soup.find("meta", {"property": "twitter:image"}),
                soup.find("meta", {"name": "thumbnail"}),
            ]

            for tag in meta_image_tags:
                if tag and tag.get("content"):
                    img_url = tag.get("content", "")
                    if (
                        img_url
                        and img_url.startswith(("http://", "https://"))
                        and img_url not in media_files
                    ):
                        media_files.append(img_url)

        # Method 4: Look for product images in specific elements with updated class name
        if not media_files:
            image_classes = [
                "_7DTxhh",  # Product image class
                "_396cs4",  # Thumbnail class
                "shopee-image__content",
                "shopee-image-manager__content",
                "product-image",
                "gallery-preview__image",
                "_1XC0Rp",  # Another image container class
                "uXN1L5",  # New image class from provided HTML
                "PhxDN7",  # Another image class from provided HTML
            ]

            for class_name in image_classes:
                images = soup.find_all("img", class_=class_name)
                for img in images:
                    src = img.get("src", "") or img.get("data-src", "")
                    if (
                        src
                        and src.startswith(("http://", "https://"))
                        and src not in media_files
                    ):
                        media_files.append(src)

        # Price extraction (keeping the existing implementation with some additions)
        price = None
        price_selectors = [
            soup.find("div", class_="_3n5NQx"),
            soup.find("div", class_="pqTWkA"),
            soup.find("div", class_="Ybrg9j"),
            soup.find("div", class_="_2v0Hgx"),  # Another price class
            soup.find(
                "div",
                class_=lambda c: c and ("price" in c.lower() or "cost" in c.lower()),
            ),
        ]

        for selector in price_selectors:
            if selector:
                price_text = selector.get_text().strip()
                price_match = re.search(r"₫\s*[\d,.]+|[\d,.]+\s*₫", price_text)
                if price_match:
                    price = price_match.group(0).strip()
                    break

        # If we still don't have a title, use the URL as a fallback
        if not title:
            path = urlparse(url).path
            if path:
                path_parts = path.split("/")
                if len(path_parts) > 1:
                    for part in reversed(path_parts):
                        if part and part not in ["-i", "product"]:
                            title = unquote(part).replace("-", " ").replace("_", " ")
                            title = " ".join(
                                word.capitalize() for word in title.split()
                            )
                            break

        return CrawlResponse(
            title=title or "Sản phẩm Shopee",
            description=description,
            media_files=media_files,
            price=price,
            currency="VND",
        )
