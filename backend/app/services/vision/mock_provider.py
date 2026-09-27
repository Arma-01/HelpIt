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
                AttendanceItem(raw_identifier="001", raw_name="Aarav Sharma", raw_attendance_mark="17", status=AttendanceStatus.PRESENT, confidence=0.98),
                AttendanceItem(raw_identifier="002", raw_name="Rahul Kumar", raw_attendance_mark="A", status=AttendanceStatus.ABSENT, confidence=0.96),
                AttendanceItem(raw_identifier="003", raw_name="Priya Singh", raw_attendance_mark="18", status=AttendanceStatus.PRESENT, confidence=0.94),
                AttendanceItem(raw_identifier="004", raw_name="Ankit Sharma", raw_attendance_mark="A", status=AttendanceStatus.ABSENT, confidence=0.91),
                AttendanceItem(raw_identifier="005", raw_name="Sneha Patel", raw_attendance_mark="19", status=AttendanceStatus.PRESENT, confidence=0.97),
                AttendanceItem(raw_identifier="006", raw_name="Vikram Rao", raw_attendance_mark="20", status=AttendanceStatus.PRESENT, confidence=0.95),
                AttendanceItem(raw_identifier="007", raw_name="Neha Gupta", raw_attendance_mark="A", status=AttendanceStatus.ABSENT, confidence=0.92),
                AttendanceItem(raw_identifier="008", raw_name="Rohan Verma", raw_attendance_mark="21", status=AttendanceStatus.PRESENT, confidence=0.98),
                AttendanceItem(raw_identifier="009", raw_name="Ananya Mishra", raw_attendance_mark="22", status=AttendanceStatus.PRESENT, confidence=0.96),
                AttendanceItem(raw_identifier="010", raw_name="Aditya Joshi", raw_attendance_mark="A", status=AttendanceStatus.ABSENT, confidence=0.90),
            ]

    def extract_attendance(
        self,
        image: Image.Image,
        image_bytes: bytes,
        filename: str,
    ) -> List[AttendanceItem]:
        # Return a copy of default items
        return [item.model_copy() for item in self._default_items]
