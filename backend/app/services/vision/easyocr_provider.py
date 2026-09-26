"""
EasyOCR-based Vision Provider.
Extracts tabular attendance data using local deep learning OCR models.
"""

import re
import numpy as np
from typing import List, Dict, Any, Optional
from PIL import Image
from app.config import settings
from app.core.logging import logger
from app.core.exceptions import OCRFailureError
from app.schemas.attendance import AttendanceItem, AttendanceStatus
from app.services.vision.base import VisionProvider

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
    """Vision provider utilizing EasyOCR for neural character recognition and row layout analysis."""

    def __init__(self):
        self._header_keywords = {
            "roll", "no", "number", "name", "student", "status", "attendance",
            "present", "absent", "sr", "s.no", "id"
        }
        self._banner_keywords = {
            "register", "daily", "class", "semester", "attendance register",
            "department", "college", "school", "institution", "academic"
        }

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

            # Run OCR: returns list of (bbox, text, confidence)
            raw_results = reader.readtext(img_np)
            logger.info(f"[EasyOCR] Detected {len(raw_results)} text boxes")

            if not raw_results:
                return []

            # 1. Parse text boxes into items with centroids and bounding geometry
            boxes = self._parse_bounding_boxes(raw_results)

            # 2. Cluster boxes into horizontal lines / rows
            rows = self._cluster_rows(boxes)
            logger.info(f"[EasyOCR] Grouped text into {len(rows)} potential table rows")

            # 3. Extract attendance items from clustered rows
            attendance_items = self._extract_items_from_rows(rows)
            logger.info(f"[EasyOCR] Extracted {len(attendance_items)} attendance records")

            return attendance_items

        except Exception as e:
            logger.error(f"[EasyOCR] Processing failed on {filename}: {str(e)}", exc_info=True)
            raise OCRFailureError(f"EasyOCR failed to process image: {str(e)}")

    def _parse_bounding_boxes(self, raw_results) -> List[Dict[str, Any]]:
        boxes = []
        for bbox, text, conf in raw_results:
            text_str = str(text).strip()
            if not text_str or conf < 0.20:
                continue

            # bbox format: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            h = max(max_y - min_y, 8.0)

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
            })
        return boxes

    def _cluster_rows(self, boxes: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not boxes:
            return []

        # Sort all boxes vertically by cy
        sorted_boxes = sorted(boxes, key=lambda b: b["cy"])

        rows: List[List[Dict[str, Any]]] = []

        for box in sorted_boxes:
            # Check if this box overlaps vertically with any existing row
            placed = False
            for row in rows:
                # Row vertical span
                row_min_y = min(b["min_y"] for b in row)
                row_max_y = max(b["max_y"] for b in row)
                row_cy = sum(b["cy"] for b in row) / len(row)
                row_h = max(b["h"] for b in row)

                # Overlap condition:
                # 1. Centroid distance within reasonable row threshold (e.g. 24px or 0.8 * max height)
                # OR 2. Interval overlap
                overlap_min = max(row_min_y, box["min_y"])
                overlap_max = min(row_max_y, box["max_y"])
                vertical_overlap = max(0, overlap_max - overlap_min)

                if (
                    abs(box["cy"] - row_cy) <= max(row_h * 0.85, 22.0)
                    or vertical_overlap >= min(box["h"], row_h) * 0.35
                ):
                    row.append(box)
                    placed = True
                    break

            if not placed:
                rows.append([box])

        # Sort each row horizontally by min_x
        for row in rows:
            row.sort(key=lambda b: b["min_x"])

        # Sort rows top-to-bottom by average cy
        rows.sort(key=lambda row: sum(b["cy"] for b in row) / len(row))

        return rows

    def _extract_items_from_rows(self, rows: List[List[Dict[str, Any]]]) -> List[AttendanceItem]:
        items: List[AttendanceItem] = []

        for row in rows:
            row_text_joined = " ".join(b["text"].lower() for b in row)
            words = set(re.findall(r"\b[a-z\.]+\b", row_text_joined))

            # Filter out document banner / title lines
            if any(banner_kw in row_text_joined for banner_kw in self._banner_keywords):
                # Unless it's a table header with status/roll/name
                if not ("roll" in words or "status" in words):
                    logger.debug(f"[EasyOCR] Skipping banner/title row: {row_text_joined}")
                    continue

            # Filter out table header row (e.g. "Roll No | Student Name | Status")
            header_matches = words.intersection(self._header_keywords)
            if len(header_matches) >= 2 and ("name" in header_matches or "roll" in header_matches or "status" in header_matches):
                logger.debug(f"[EasyOCR] Skipping detected header row: {row_text_joined}")
                continue

            # Extract identifier, name, and status from the row's tokens
            parsed = self._parse_single_row(row)
            if parsed:
                items.append(parsed)

        return items

    def _parse_single_row(self, row: List[Dict[str, Any]]) -> Optional[AttendanceItem]:
        texts = [b["text"].strip() for b in row]
        confs = [b["conf"] for b in row]

        if not texts:
            return None

        # 1. Detect Status in tokens
        status = AttendanceStatus.UNKNOWN
        status_token_idx = -1
        status_conf = 0.85

        for idx, text in enumerate(texts):
            clean = re.sub(r"[^A-Za-z]", "", text).upper()
            
            # Exact or clean status match
            if clean in ("P", "PRESENT", "PRES"):
                status = AttendanceStatus.PRESENT
                status_token_idx = idx
                status_conf = confs[idx]
                break
            elif clean in ("A", "ABSENT", "ABS"):
                status = AttendanceStatus.ABSENT
                status_token_idx = idx
                status_conf = confs[idx]
                break
            elif clean in ("L", "LATE"):
                status = AttendanceStatus.LATE
                status_token_idx = idx
                status_conf = confs[idx]
                break

        # Check for status appended to another token (e.g. "Rahul Kumar Present")
        if status == AttendanceStatus.UNKNOWN:
            for idx, text in enumerate(texts):
                m = re.search(r"\b(PRESENT|ABSENT|LATE|P|A|L)\b\s*$", text, re.IGNORECASE)
                if m:
                    status = AttendanceStatus.from_str(m.group(1))
                    texts[idx] = text[:m.start()].strip()
                    status_token_idx = idx
                    status_conf = confs[idx]
                    break

        # 2. Detect Roll Number / Identifier
        identifier = None
        ident_idx = -1

        for idx, text in enumerate(texts):
            if idx == status_token_idx:
                continue
            clean = text.strip()

            # Direct match: 001, 12, STU001, CS101, #1
            if re.match(r"^(STU\d+|\d{1,4}|#\d+|[A-Z]{2,4}\d{2,4})$", clean, re.IGNORECASE):
                identifier = clean
                ident_idx = idx
                break

            # Handle OCR misreads like '0u2' -> '002', '0o3' -> '003'
            fuzzy_match = re.match(r"^0[oOuU](\d)$", clean)
            if fuzzy_match:
                identifier = f"00{fuzzy_match.group(1)}"
                ident_idx = idx
                break

            fuzzy_match2 = re.match(r"^0[oOuU](\d{2})$", clean)
            if fuzzy_match2:
                identifier = f"0{fuzzy_match2.group(1)}"
                ident_idx = idx
                break

        # 3. Remaining tokens form the Student Name
        name_tokens = []
        name_confs = []
        for idx, text in enumerate(texts):
            if idx in (status_token_idx, ident_idx):
                continue
            clean = text.strip(" |;,-:")
            # Filter out stray single-character symbols or separators
            if clean and clean not in ("|", "/", "\\", "-", ":"):
                name_tokens.append(clean)
                name_confs.append(confs[idx])

        raw_name = " ".join(name_tokens) if name_tokens else None

        # If identifier was not found, check if raw_name starts with a roll number / ID token
        if raw_name:
            leading_m = re.match(r"^([0-9oOuUzZ#]{2,4})\s+(.+)$", raw_name)
            if not identifier and leading_m:
                cand_id = leading_m.group(1)
                # Clean cand_id (e.g. '0uz' -> '002', '0u4' -> '004')
                cand_id_clean = re.sub(r"[oOuU]", "0", cand_id)
                cand_id_clean = re.sub(r"[zZ]", "2", cand_id_clean)
                if re.match(r"^\d{1,4}$", cand_id_clean):
                    identifier = cand_id_clean
                    raw_name = leading_m.group(2).strip()

        # Filter out rows that are neither a student nor an identifier
        if not raw_name and not identifier:
            return None

        # Ignore if the row is just a date like "2026-09-26"
        if raw_name and re.match(r"^\d{4}-\d{2}-\d{2}$", raw_name):
            return None

        # 4. Confidence calculation:
        # Weighted combination of OCR confidence and status certainty
        token_confs = [c for i, c in enumerate(confs) if i in (status_token_idx, ident_idx)] + name_confs
        avg_ocr_conf = sum(token_confs) / len(token_confs) if token_confs else 0.8
        
        if status == AttendanceStatus.UNKNOWN:
            overall_confidence = min(avg_ocr_conf * 0.7, 0.65)
        else:
            overall_confidence = min(max(avg_ocr_conf * 0.95, 0.70), 0.99)

        return AttendanceItem(
            raw_name=raw_name,
            raw_identifier=identifier,
            status=status,
            confidence=round(overall_confidence, 2),
        )
