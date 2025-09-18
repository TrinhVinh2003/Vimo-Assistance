import re

from bs4 import BeautifulSoup

from app.schemas.crawl_schema import CrawlResponse


class BonbanhParser:
    @staticmethod
    def parse(soup: BeautifulSoup, url: str) -> CrawlResponse:
        # Extract title
        title_element = soup.select_one("h1")
        raw_title = title_element.text.strip() if title_element else "Unknown Vehicle"

        # Clean up the title by removing extra whitespace and newlines
        raw_title = re.sub(r"\s+", " ", raw_title)

        # Clean up the title by removing the price part
        title = re.sub(r"\s*-\s*\d+\s*Triệu\s*$", "", raw_title)

        # Extract price
        price_match = re.search(r"(\d+)\s*Triệu", raw_title)
        price = price_match.group(1) if price_match else None

        # Extract description
        description_element = soup.select_one(".des_txt")
        description = description_element.text.strip() if description_element else None

        # Extract specifications
        specs = {}
        spec_rows = soup.select(".box_car_detail .row, .box_car_detail .row_last")
        for row in spec_rows:
            label_element = row.select_one(".label label")
            value_element = row.select_one(".txt_input .inp, .inputbox .inp")

            if label_element and value_element:
                key = label_element.text.strip().rstrip(":")
                value = value_element.text.strip()
                specs[key] = value

        # Extract contact information
        contact_info = {}
        contact_element = soup.select_one(".contact-txt")
        if contact_element:
            contact_text = contact_element.get_text(strip=True, separator="\n")

            # Extract name
            name_element = contact_element.select_one(".cname")
            if name_element:
                contact_info["Tên"] = name_element.text.strip()

            # Extract phone
            phone_element = contact_element.select_one(".cphone")
            if phone_element:
                contact_info["Điện thoại"] = phone_element.text.strip()

            # Extract address
            address_text = contact_element.get_text()
            address_match = re.search(r"Địa chỉ:\s*(.*?)(?:\s*$|\s*<br>)", address_text)
            if address_match:
                contact_info["Địa chỉ"] = address_match.group(1).strip()

        # Format description with specs and contact info
        formatted_parts = []

        if description:
            formatted_parts.append(description)

        if specs:
            formatted_specs = "\n".join(
                [f"{key}: {value}" for key, value in specs.items()]
            )
            formatted_parts.append(f"Thông số kỹ thuật:\n{formatted_specs}")

        if contact_info:
            formatted_contact = "\n".join(
                [f"{key}: {value}" for key, value in contact_info.items()]
            )
            formatted_parts.append(f"Liên hệ người bán:\n{formatted_contact}")

        full_description = "\n\n".join(formatted_parts)

        # Extract images
        media_files = []
        image_elements = soup.select("a.highslide")
        for img in image_elements:
            if img.get("href"):
                media_files.append(img["href"])

        return CrawlResponse(
            title=title,
            description=full_description,
            media_files=media_files,
            price=price,
            currency="VND",
        )
