"""
EasyOCR-based Vision Provider.
Extracts tabular attendance data using neural OCR models and physical table analysis.
Strictly supports ONLY TWO attendance statuses: PRESENT and ABSENT.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import OCRFailureError
from app.schemas.attendance import AttendanceItem
from app.services.vision.base import VisionProvider
from app.services.ocr_service import ocr_extractor

_EASYOCR_READER = None


def get_easyocr_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        import easyocr
        logger.info(f"Initializing EasyOCR reader (GPU={settings.OCR_GPU})...")
        _EASYOCR_READER = easyocr.Reader(["en"], gpu=settings.OCR_GPU)
        logger.info("EasyOCR reader initialized.")
    return _EASYOCR_READER


class EasyOCRVisionProvider(VisionProvider):
    """
    Vision provider utilizing EasyOCR for neural character recognition and row layout analysis.

    Pipeline:
    Uploaded Image
    ↓
    Detect Attendance Table (ignore page headers, Page No., Date., notebook lines, margin text)
    ↓
    Detect Columns (Roll No, Student ID, Student Name, Attendance)
    ↓
    Detect Physical Rows (Group items strictly by physical row)
    ↓
    Read Cells Using OCR/Vision
    ↓
    Reconstruct Student Records (Preserve raw_identifier, raw_student_id, raw_name, raw_attendance_mark)
    ↓
    Normalize Attendance (Strictly PRESENT or ABSENT, numeric marks = PRESENT)
    ↓
    Validate Records (Reject metadata, headers, fragments)
    ↓
    Output Valid Records
    """

    def __init__(self):
        self._extractor = ocr_extractor

    def extract_attendance(
        self,
        image: Image.Image,
        image_bytes: bytes,
        filename: str,
    ) -> List[AttendanceItem]:
        logger.info(f"[EasyOCR] Running OCR on {filename} ({image.size[0]}x{image.size[1]})")

        try:
            reader = get_easyocr_reader()

            # Convert PIL Image to RGB numpy array
            if image.mode != "RGB":
                rgb_img = image.convert("RGB")
            else:
                rgb_img = image
            img_np = np.array(rgb_img)

            # Run OCR with sensitive text thresholds for handwritten sheets
            raw_results = reader.readtext(
                img_np,
                low_text=0.20,
                text_threshold=0.30,
                link_threshold=0.40,
            )
            logger.info(f"[EasyOCR] Detected {len(raw_results)} text boxes")

            if not raw_results:
                return []

            # 1. Parse text boxes into structured items with geometry
            boxes = self._parse_bounding_boxes(raw_results)

            # 2. Run Table Extraction Pipeline
            img_w, img_h = float(image.size[0]), float(image.size[1])
            attendance_items = self._extractor.extract_from_boxes(boxes, img_w, img_h)
            logger.info(f"[EasyOCR] Extracted {len(attendance_items)} valid attendance records")

            return attendance_items

        except Exception as e:
            logger.error(f"[EasyOCR] Processing failed on {filename}: {str(e)}", exc_info=True)
            raise OCRFailureError(f"EasyOCR failed to process image: {str(e)}")

    def _parse_bounding_boxes(self, raw_results) -> List[Dict[str, Any]]:
        """
        Parses raw EasyOCR tuples into geometric dictionaries.
        """
        boxes = []
        for bbox, text, conf in raw_results:
            text_str = str(text).strip()
            if not text_str or conf < 0.15:
                continue

            # bbox format: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            xs = [float(pt[0]) for pt in bbox]
            ys = [float(pt[1]) for pt in bbox]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            h = max(max_y - min_y, 6.0)
            w = max(max_x - min_x, 6.0)

            boxes.append({
                "text": text_str,
                "conf": float(conf),
                "cx": cx,
                "cy": cy,
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
                "h": h,
                "w": w,
            })
        return boxes
