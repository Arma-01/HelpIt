"""
Attendance Processing Service.
Orchestrates the image validation, vision extraction, normalization, and structured output.
"""

from typing import List, Optional
from app.core.logging import logger
from app.core.exceptions import (
    NoAttendanceDetectedError,
    MalformedAIResponseError,
    AttendanceException,
)
from app.schemas.attendance import (
    AttendanceItem,
    AttendanceSummary,
    AttendanceProcessResponse,
    AttendanceStatus,
)
from app.services.image_validator import ImageValidator
from app.services.vision.factory import get_vision_provider
from app.services.vision.base import VisionProvider


class AttendanceService:
    """Core service for validating attendance sheets and extracting structured records."""

    def __init__(self, vision_provider: Optional[VisionProvider] = None):
        self._provider = vision_provider

    @property
    def provider(self) -> VisionProvider:
        if self._provider is None:
            self._provider = get_vision_provider()
        return self._provider

    @provider.setter
    def provider(self, val: Optional[VisionProvider]):
        self._provider = val

    @provider.deleter
    def provider(self):
        self._provider = None

    def process_image(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "",
    ) -> AttendanceProcessResponse:
        """
        Executes the end-to-end attendance extraction pipeline:
        1. Validates image payload and MIME integrity
        2. Passes verified image to active VisionProvider
        3. Normalizes and validates each row
        4. Calculates summary statistics
        5. Returns structured AttendanceProcessResponse
        """
        logger.info(f"Starting attendance processing pipeline for {filename}")

        # Step 1: Validate Image
        pil_image = ImageValidator.validate(file_bytes, filename, content_type)

        # Step 2: OCR / Vision Extraction
        try:
            raw_items = self.provider.extract_attendance(pil_image, file_bytes, filename)
        except AttendanceException:
            raise
        except Exception as e:
            logger.error(f"Unexpected vision extraction failure: {str(e)}", exc_info=True)
            raise MalformedAIResponseError("Failed to interpret AI vision extraction results.")

        # Step 3: Handle No Attendance Detected
        if not raw_items or len(raw_items) == 0:
            logger.warning(f"No attendance rows detected in {filename}")
            raise NoAttendanceDetectedError("No attendance information could be detected.")

        # Step 4: Validate and Normalize Structured Records
        validated_items: List[AttendanceItem] = []
        for raw in raw_items:
            try:
                # Ensure status is strictly one of PRESENT, ABSENT, LATE, UNKNOWN
                if isinstance(raw.status, str):
                    clean_status = AttendanceStatus.from_str(raw.status)
                else:
                    clean_status = raw.status

                # Ensure confidence is clamped between 0.0 and 1.0
                clamped_conf = min(max(float(raw.confidence), 0.0), 1.0)

                # Preserve raw attendance mark (e.g. '17', 'A', 'P')
                raw_mark = getattr(raw, "raw_attendance_mark", None)
                if raw_mark is not None:
                    raw_mark = str(raw_mark).strip()

                # Preserve raw student ID if extracted
                raw_student_id = getattr(raw, "raw_student_id", None)
                if raw_student_id is not None:
                    raw_student_id = str(raw_student_id).strip()

                item = AttendanceItem(
                    raw_name=raw.raw_name.strip() if raw.raw_name else None,
                    raw_identifier=raw.raw_identifier.strip() if raw.raw_identifier else None,
                    raw_student_id=raw_student_id,
                    raw_attendance_mark=raw_mark,
                    status=clean_status,
                    confidence=clamped_conf,
                )
                validated_items.append(item)
            except Exception as val_err:
                logger.warning(f"Discarding malformed attendance item {raw}: {val_err}")

        if not validated_items:
            raise NoAttendanceDetectedError("No valid attendance information could be detected.")

        # Step 5: Compute Attendance Summary
        summary = AttendanceSummary.compute(validated_items)

        logger.info(
            f"Processing completed for {filename}: {summary.total_detected} total "
            f"({summary.present} present, {summary.absent} absent)"
        )

        return AttendanceProcessResponse(
            success=True,
            attendance=validated_items,
            records=validated_items,
            summary=summary,
        )


attendance_service = AttendanceService()
