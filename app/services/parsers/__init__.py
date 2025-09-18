from app.services.parsers.amazon_parser import AmazonParser
from app.services.parsers.base_parser import BaseParser
from app.services.parsers.bonbanh_parser import BonbanhParser
from app.services.parsers.lottemart_parser import LotteMartParser
from app.services.parsers.shopee_parser import ShopeeParser

__all__ = [
    "BaseParser",
    "ShopeeParser",
    "AmazonParser",
    "LotteMartParser",
    "BonbanhParser",
]
