"""
Mock / Synthetic Vision Provider.
Used for deterministic testing, unit tests, and instant demos.
"""

from typing import List
from PIL import Image
from app.schemas.attendance import AttendanceItem, AttendanceStatus
from app.services.vision.base import VisionProvider


class MockVisionProvider(VisionProvider):
    """Deterministic mock provider returning synthetic classroom attendance data."""

    def __init__(self, default_items: List[AttendanceItem] = None):
        if default_items is not None:
            self._default_items = default_items
        else:
            self._default_items = [
                AttendanceItem(raw_identifier="001", raw_name="Aarav Sharma", status=AttendanceStatus.PRESENT, confidence=0.98),
                AttendanceItem(raw_identifier="002", raw_name="Rahul Kumar", status=AttendanceStatus.PRESENT, confidence=0.96),
                AttendanceItem(raw_identifier="003", raw_name="Priya Singh", status=AttendanceStatus.ABSENT, confidence=0.94),
                AttendanceItem(raw_identifier="004", raw_name="Ankit Sharma", status=AttendanceStatus.LATE, confidence=0.89),
                AttendanceItem(raw_identifier="005", raw_name="Sneha Patel", status=AttendanceStatus.PRESENT, confidence=0.97),
                AttendanceItem(raw_identifier="006", raw_name="Vikram Rao", status=AttendanceStatus.PRESENT, confidence=0.95),
                AttendanceItem(raw_identifier="007", raw_name="Neha Gupta", status=AttendanceStatus.ABSENT, confidence=0.92),
                AttendanceItem(raw_identifier="008", raw_name="Rohan Verma", status=AttendanceStatus.PRESENT, confidence=0.98),
                AttendanceItem(raw_identifier="009", raw_name="Ananya Mishra", status=AttendanceStatus.PRESENT, confidence=0.96),
                AttendanceItem(raw_identifier="010", raw_name="Aditya Joshi", status=AttendanceStatus.LATE, confidence=0.88),
            ]

    def extract_attendance(
        self,
        image: Image.Image,
        image_bytes: bytes,
        filename: str,
    ) -> List[AttendanceItem]:
        # Return a copy of default items
        return [item.model_copy() for item in self._default_items]
