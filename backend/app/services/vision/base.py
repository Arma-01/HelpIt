"""
Abstract base class for vision / OCR providers.
Allows swapping AI providers (EasyOCR, Tesseract, Gemini, Cloud Vision, etc.)
without changing the rest of the application.
"""

from abc import ABC, abstractmethod
from typing import List
from PIL import Image
from app.schemas.attendance import AttendanceItem


class VisionProvider(ABC):
    """Abstract interface for all attendance vision providers."""

    @abstractmethod
    def extract_attendance(
        self,
        image: Image.Image,
        image_bytes: bytes,
        filename: str,
    ) -> List[AttendanceItem]:
        """
        Extract structured attendance items from an image.
        
        Args:
            image: PIL Image instance (already validated)
            image_bytes: Raw bytes of the image file
            filename: Original uploaded filename
            
        Returns:
            List of AttendanceItem instances
        """
        pass
