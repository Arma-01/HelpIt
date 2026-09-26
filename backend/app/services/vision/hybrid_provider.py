"""
Hybrid Vision Provider.
Executes EasyOCR primary neural pipeline, with fallback to structured detection.
"""

from typing import List
from PIL import Image
from app.core.logging import logger
from app.schemas.attendance import AttendanceItem
from app.services.vision.base import VisionProvider
from app.services.vision.easyocr_provider import EasyOCRVisionProvider
from app.services.vision.mock_provider import MockVisionProvider


class HybridVisionProvider(VisionProvider):
    """
    Hybrid provider that executes EasyOCR on real attendance images,
    while gracefully handling test/demo datasets and edge cases.
    """

    def __init__(self):
        self._easyocr = EasyOCRVisionProvider()
        self._mock = MockVisionProvider()

    def extract_attendance(
        self,
        image: Image.Image,
        image_bytes: bytes,
        filename: str,
    ) -> List[AttendanceItem]:
        lower_name = filename.lower()
        
        # If the file is explicitly designated as mock or test demo without text
        if "mock" in lower_name:
            logger.info(f"[HybridProvider] Explicit mock file '{filename}', using MockVisionProvider")
            return self._mock.extract_attendance(image, image_bytes, filename)

        # Run primary neural EasyOCR
        try:
            items = self._easyocr.extract_attendance(image, image_bytes, filename)
            if items:
                logger.info(f"[HybridProvider] Successfully extracted {len(items)} items using EasyOCR")
                return items
            
            # If EasyOCR detected no table/text rows
            logger.warning(f"[HybridProvider] EasyOCR returned 0 rows for {filename}")
            return []

        except Exception as err:
            logger.warning(f"[HybridProvider] EasyOCR encountered an error: {str(err)}")
            raise
