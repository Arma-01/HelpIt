"""
Vision Provider Factory.
Instantiates and provides the active vision/OCR engine based on configuration.
"""

from app.config import settings
from app.core.logging import logger
from app.services.vision.base import VisionProvider
from app.services.vision.easyocr_provider import EasyOCRVisionProvider
from app.services.vision.mock_provider import MockVisionProvider
from app.services.vision.hybrid_provider import HybridVisionProvider

_CACHED_PROVIDERS = {}


def get_vision_provider(provider_type: str = None) -> VisionProvider:
    """
    Returns an instance of the requested VisionProvider.
    Uses singleton caching for performance.
    """
    target_type = (provider_type or settings.VISION_PROVIDER).lower()

    if target_type not in _CACHED_PROVIDERS:
        if target_type == "easyocr":
            logger.info("Initializing EasyOCRVisionProvider...")
            _CACHED_PROVIDERS[target_type] = EasyOCRVisionProvider()
        elif target_type == "mock":
            logger.info("Initializing MockVisionProvider...")
            _CACHED_PROVIDERS[target_type] = MockVisionProvider()
        else:
            logger.info("Initializing HybridVisionProvider...")
            _CACHED_PROVIDERS[target_type] = HybridVisionProvider()

    return _CACHED_PROVIDERS[target_type]
