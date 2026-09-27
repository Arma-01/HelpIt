"""
Attendance Table OCR & Vision Extraction Service.
Implements the 8-stage image extraction pipeline:
Uploaded Image
↓
Detect Attendance Table
↓
Detect Columns
↓
Detect Physical Rows
↓
Read Cells Using OCR/Vision
↓
Reconstruct Student Records
↓
Normalize Attendance
↓
Validate Records
↓
Match Against ERP (in Matching Service)
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.core.logging import logger
from app.schemas.attendance import AttendanceItem, AttendanceStatus
from app.services.attendance_normalization import normalize_attendance


class ColumnType(str, Enum):
    ROLL_NO = "ROLL_NO"
    STUDENT_ID = "STUDENT_ID"
    NAME = "NAME"
    ATTENDANCE = "ATTENDANCE"


@dataclass
class TableRegion:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    header_min_y: Optional[float] = None
    header_max_y: Optional[float] = None


@dataclass
class TableColumn:
    col_type: ColumnType
    min_x: float
    max_x: float
    cx: float
    header_text: str = ""


@dataclass
class PhysicalRow:
    row_index: int
    cy: float
    min_y: float
    max_y: float
    boxes: List[Dict[str, Any]] = field(default_factory=list)


# Keywords used to detect page metadata outside the attendance table
PAGE_METADATA_REGEX = re.compile(
    r"^(page\s*(no\.?|\d+)?|pg\s*(no\.?|\d+)?|date\s*[:.-]?.*|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|class\s*[:.-]?.*|subject\s*[:.-]?.*|sem(ester)?\s*[:.-]?.*|sec(tion)?\s*[:.-]?.*|lecture\s*[:.-]?.*|teacher(\s*sig(nature)?)?.*|sign(ature)?.*|total\s*(present|absent)?.*)$",
    re.IGNORECASE,
)

BANNER_KEYWORDS = {
    "register", "daily", "semester", "attendance register",
    "department", "college", "school", "institution", "academic", "university", "faculty"
}

# Table header keywords by column type
HEADER_KEYWORDS_MAP = {
    ColumnType.ROLL_NO: [
        "roll no", "roll number", "rollno", "roll", "r.no", "sr.no", "sr no", "s.no", "no."
    ],
    ColumnType.STUDENT_ID: [
        "student id", "stu id", "stuid", "student_id", "enrollment no", "enrollment", "id", "adm no", "reg no"
    ],
    ColumnType.NAME: [
        "student name", "name of student", "student", "name", "full name"
    ],
    ColumnType.ATTENDANCE: [
        "attendance", "attendance status", "status", "presence", "att.", "att", "mark", "present/absent", "p/a"
    ],
}


class AttendanceTableExtractor:
    """
    Core extraction engine that converts raw OCR bounding boxes into structured student attendance records.
    Strictly detects table bounds, isolates columns, groups boxes by physical row, and validates records.
    """

    def extract_from_boxes(
        self,
        boxes: List[Dict[str, Any]],
        img_width: float,
        img_height: float,
    ) -> List[AttendanceItem]:
        """
        Executes the full pipeline on OCR bounding boxes.
        Returns validated, normalized AttendanceItem records.
        """
        logger.info(f"[OCR Pipeline] Starting table extraction on {len(boxes)} raw OCR boxes ({img_width}x{img_height})")

        if not boxes:
            logger.warning("[OCR Pipeline] No OCR boxes provided.")
            return []

        # 1. Log Raw OCR Results (Rule 15)
        logger.info(f"[Raw OCR Results] Total detected boxes: {len(boxes)}")
        for b in boxes:
            logger.debug(f"  OCR Box: text='{b['text']}', conf={b['conf']:.2f}, bbox=[{b['min_x']:.1f}, {b['min_y']:.1f}, {b['max_x']:.1f}, {b['max_y']:.1f}]")

        # 2. Detect Attendance Table Region (Rule 5 & 6)
        table_region, header_boxes = self._detect_table_region(boxes, img_width, img_height)
        logger.info(
            f"[Detected Table Region] x=[{table_region.min_x:.1f}, {table_region.max_x:.1f}], "
            f"y=[{table_region.min_y:.1f}, {table_region.max_y:.1f}], "
            f"header_y=[{table_region.header_min_y}, {table_region.header_max_y}]"
        )

        # 3. Detect Table Columns (Rule 7)
        columns = self._detect_columns(boxes, header_boxes, table_region, img_width)
        col_desc = ", ".join(f"{c.col_type.value}: [{c.min_x:.1f}-{c.max_x:.1f}]" for c in columns)
        logger.info(f"[Detected Columns] ({len(columns)} columns) {col_desc}")

        # Filter candidate data boxes strictly inside table body (excluding headers and page metadata)
        table_data_boxes = self._filter_boxes_in_table(boxes, table_region)
        logger.info(f"[Table Body] Filtered {len(table_data_boxes)} data boxes inside table body")

        # 4. Group OCR results by PHYSICAL ROW (Rule 8)
        physical_rows = self._detect_physical_rows(table_data_boxes, columns, table_region)
        logger.info(f"[Detected Physical Rows] Grouped into {len(physical_rows)} physical rows")

        # 5. Read Cells & Reconstruct Student Records (Rule 8, 11, 12)
        raw_records = self._read_cells_and_reconstruct(physical_rows, columns)
        logger.info(f"[Grouped Rows] Reconstructed {len(raw_records)} candidate row records")
        for idx, rec in enumerate(raw_records):
            logger.info(
                f"  Row {idx + 1}: Roll='{rec.get('raw_identifier')}', "
                f"StudentID='{rec.get('raw_student_id')}', "
                f"Name='{rec.get('raw_name')}', "
                f"Mark='{rec.get('raw_attendance_mark')}'"
            )

        # 6. Normalize Attendance (Rule 9 & 10)
        normalized_items = self._normalize_records(raw_records)
        logger.info(f"[Normalized Records] {len(normalized_items)} records normalized")

        # 7. Validate Records BEFORE Matching (Rule 14)
        validated_items = [item for item in normalized_items if self._validate_student_record(item)]
        logger.info(f"[Records Sent to Matching] {len(validated_items)} valid records sent to matching engine")

        for idx, item in enumerate(validated_items):
            logger.info(
                f"  Record {idx + 1}: Identifier='{item.raw_identifier}', "
                f"StudentID='{item.raw_student_id}', "
                f"Name='{item.raw_name}', "
                f"Mark='{item.raw_attendance_mark}', "
                f"Status='{item.status.value}', "
                f"Conf={item.confidence:.2f}"
            )

        return validated_items

    def _detect_table_region(
        self,
        boxes: List[Dict[str, Any]],
        img_width: float,
        img_height: float,
    ) -> Tuple[TableRegion, List[Dict[str, Any]]]:
        """
        Detects the boundaries of the attendance table.
        Ignores everything outside the table: Page No., Date., page headers, notebook borders, etc.
        """
        # Step A: Identify header candidate boxes
        header_candidates = []
        for b in boxes:
            t = b["text"].strip().lower()
            # Exclude known page metadata or document banner words
            if PAGE_METADATA_REGEX.match(t) or any(w in t for w in BANNER_KEYWORDS):
                continue

            for col_type, kw_list in HEADER_KEYWORDS_MAP.items():
                if any(kw == t or kw in t.split() or t.startswith(kw) for kw in kw_list):
                    header_candidates.append((col_type, b))
                    break

        # Step B: Find horizontal band containing at least 2 distinct column headers
        best_band_boxes: List[Dict[str, Any]] = []
        best_band_types = set()
        best_header_y_min = None
        best_header_y_max = None

        if header_candidates:
            # Sort candidates by vertical position
            header_candidates.sort(key=lambda x: x[1]["cy"])

            # Check clusters of header candidates within vertical distance
            for i, (ctype_i, box_i) in enumerate(header_candidates):
                current_band = [box_i]
                current_types = {ctype_i}
                for j, (ctype_j, box_j) in enumerate(header_candidates):
                    if i == j:
                        continue
                    if abs(box_i["cy"] - box_j["cy"]) <= max(box_i["h"], box_j["h"], 30.0):
                        current_band.append(box_j)
                        current_types.add(ctype_j)

                if len(current_types) > len(best_band_types) or (
                    len(current_types) == len(best_band_types) and len(current_band) > len(best_band_boxes)
                ):
                    best_band_types = current_types
                    best_band_boxes = current_band

        # If a valid header row is found with >= 2 distinct header types
        if len(best_band_types) >= 2:
            best_header_y_min = min(b["min_y"] for b in best_band_boxes)
            best_header_y_max = max(b["max_y"] for b in best_band_boxes)
            data_top_y = best_header_y_max + 2.0
            header_boxes = best_band_boxes
        else:
            # Fallback: Look for student row anchors (numeric rolls or student IDs on the left)
            anchor_boxes = [
                b for b in boxes
                if re.match(r"^(00\d|\d{1,3}|STU\d+)$", b["text"].strip(), re.IGNORECASE)
                and b["min_x"] < img_width * 0.40
                and not PAGE_METADATA_REGEX.match(b["text"].strip())
            ]
            if anchor_boxes:
                anchor_boxes.sort(key=lambda b: b["cy"])
                data_top_y = min(b["min_y"] for b in anchor_boxes) - 5.0
            else:
                data_top_y = 0.0
            header_boxes = []

        # Find table bottom boundary (filter out bottom signatures, totals, notes)
        footer_keywords = ["teacher signature", "signature", "sign", "total present", "total absent", "total:"]
        bottom_y = img_height
        for b in boxes:
            t = b["text"].strip().lower()
            if b["cy"] > data_top_y and any(fk in t for fk in footer_keywords):
                if b["min_y"] < bottom_y:
                    bottom_y = b["min_y"] - 5.0

        # Calculate horizontal bounds from relevant table elements
        relevant_boxes = [b for b in boxes if data_top_y - 30 <= b["cy"] <= bottom_y]
        if relevant_boxes:
            min_x = max(min(b["min_x"] for b in relevant_boxes) - 25.0, 0.0)
            max_x = min(max(b["max_x"] for b in relevant_boxes) + 25.0, img_width)
        else:
            min_x = 0.0
            max_x = img_width

        region = TableRegion(
            min_x=min_x,
            max_x=max_x,
            min_y=data_top_y,
            max_y=bottom_y,
            header_min_y=best_header_y_min,
            header_max_y=best_header_y_max,
        )
        return region, header_boxes

    def _detect_columns(
        self,
        boxes: List[Dict[str, Any]],
        header_boxes: List[Dict[str, Any]],
        table_region: TableRegion,
        img_width: float,
    ) -> List[TableColumn]:
        """
        Detects table columns using both OCR header text and physical positions.
        Expected columns: Roll No, Student ID, Student Name, Attendance.
        """
        detected_cols: List[TableColumn] = []

        # Case 1: Build columns from detected header boxes
        if header_boxes:
            # Sort header boxes horizontally
            sorted_headers = sorted(header_boxes, key=lambda b: b["min_x"])
            classified: List[Tuple[ColumnType, Dict[str, Any]]] = []

            for b in sorted_headers:
                t = b["text"].strip().lower()
                for ctype, kw_list in HEADER_KEYWORDS_MAP.items():
                    if any(kw == t or kw in t.split() or t.startswith(kw) for kw in kw_list):
                        classified.append((ctype, b))
                        break

            # Deduplicate by column type (keeping leftmost or widest)
            unique_cols: Dict[ColumnType, Dict[str, Any]] = {}
            for ctype, b in classified:
                if ctype not in unique_cols:
                    unique_cols[ctype] = b

            ordered_types = sorted(unique_cols.keys(), key=lambda ct: unique_cols[ct]["cx"])

            # Build TableColumn instances with boundaries
            for i, ctype in enumerate(ordered_types):
                b = unique_cols[ctype]
                cx = b["cx"]

                # Left boundary
                if i == 0:
                    x_start = 0.0
                else:
                    prev_b = unique_cols[ordered_types[i - 1]]
                    x_start = (prev_b["max_x"] + b["min_x"]) / 2.0

                # Right boundary
                if i == len(ordered_types) - 1:
                    x_end = img_width
                else:
                    next_b = unique_cols[ordered_types[i + 1]]
                    x_end = (b["max_x"] + next_b["min_x"]) / 2.0

                detected_cols.append(TableColumn(
                    col_type=ctype,
                    min_x=x_start,
                    max_x=x_end,
                    cx=cx,
                    header_text=b["text"],
                ))

        # Check if Student ID column is present; if not, check data rows to see if STUxxx exists between Roll and Name
        has_id_col = any(c.col_type == ColumnType.STUDENT_ID for c in detected_cols)
        has_roll_col = any(c.col_type == ColumnType.ROLL_NO for c in detected_cols)
        has_name_col = any(c.col_type == ColumnType.NAME for c in detected_cols)

        if not has_id_col and has_roll_col and has_name_col:
            roll_col = next(c for c in detected_cols if c.col_type == ColumnType.ROLL_NO)
            name_col = next(c for c in detected_cols if c.col_type == ColumnType.NAME)

            # Check if there are boxes matching STUxxx or similar between roll and name
            stu_id_boxes = [
                b for b in boxes
                if table_region.min_y <= b["cy"] <= table_region.max_y
                and re.match(r"^STU\d+$", b["text"].strip(), re.IGNORECASE)
            ]
            if stu_id_boxes:
                # Insert Student ID column between Roll and Name
                id_cx = sum(b["cx"] for b in stu_id_boxes) / len(stu_id_boxes)
                id_min_x = min(b["min_x"] for b in stu_id_boxes) - 15.0
                id_max_x = max(b["max_x"] for b in stu_id_boxes) + 15.0

                # Adjust roll_col and name_col boundaries
                roll_col.max_x = id_min_x
                name_col.min_x = id_max_x

                new_id_col = TableColumn(
                    col_type=ColumnType.STUDENT_ID,
                    min_x=id_min_x,
                    max_x=id_max_x,
                    cx=id_cx,
                    header_text="Student ID",
                )
                detected_cols.append(new_id_col)
                detected_cols.sort(key=lambda c: c.min_x)

        # Fallback if no columns could be detected from headers
        if not detected_cols:
            logger.info("[Column Detection] Using geometric fallback columns")
            detected_cols = [
                TableColumn(ColumnType.ROLL_NO, 0.0, img_width * 0.20, img_width * 0.10, "Roll No"),
                TableColumn(ColumnType.STUDENT_ID, img_width * 0.20, img_width * 0.40, img_width * 0.30, "Student ID"),
                TableColumn(ColumnType.NAME, img_width * 0.40, img_width * 0.75, img_width * 0.575, "Student Name"),
                TableColumn(ColumnType.ATTENDANCE, img_width * 0.75, img_width, img_width * 0.875, "Attendance"),
            ]

        return detected_cols

    def _filter_boxes_in_table(
        self,
        boxes: List[Dict[str, Any]],
        table_region: TableRegion,
    ) -> List[Dict[str, Any]]:
        """
        Filters boxes that belong strictly inside the table body region.
        Excludes page headers, Page No., Date., notebook margins, ruled lines, and noise.
        """
        table_boxes = []
        for b in boxes:
            t = b["text"].strip()
            # 1. Reject if vertically above table data region (e.g. Page No, Date, Header row)
            if b["cy"] < table_region.min_y:
                continue

            # 2. Reject if below table bottom
            if b["cy"] > table_region.max_y:
                continue

            # 3. Reject if outside horizontal table bounds
            if b["cx"] < table_region.min_x - 10.0 or b["cx"] > table_region.max_x + 10.0:
                continue

            # 4. Reject obvious page metadata / banner text
            if PAGE_METADATA_REGEX.match(t) or any(w in t.lower() for w in BANNER_KEYWORDS):
                continue

            # 5. Reject notebook ruled line noise (e.g. "_" or "-" or "|" spanning long or very low height)
            if t in ("_", "-", "--", "---", "|", "—", "=") and b["w"] > 50:
                continue
            if b["h"] < 5.0:
                continue

            table_boxes.append(b)

        return table_boxes

    def _detect_physical_rows(
        self,
        data_boxes: List[Dict[str, Any]],
        columns: List[TableColumn],
        table_region: TableRegion,
    ) -> List[PhysicalRow]:
        """
        Groups OCR results by PHYSICAL ROW.
        001 | STU001 | Aarav S. | Present MUST become ONE student record.
        """
        if not data_boxes:
            return []

        # Sort all data boxes vertically by cy
        sorted_boxes = sorted(data_boxes, key=lambda b: b["cy"])

        # Identify Row Anchors: Boxes in the Roll No column (or Student ID column)
        roll_col = next((c for c in columns if c.col_type == ColumnType.ROLL_NO), None)
        id_col = next((c for c in columns if c.col_type == ColumnType.STUDENT_ID), None)

        anchor_boxes = []
        for b in sorted_boxes:
            clean = b["text"].strip()
            is_roll_cand = (
                roll_col is not None
                and roll_col.min_x - 10 <= b["cx"] <= roll_col.max_x + 10
                and re.match(r"^(\d{1,4}|STU\d+|#\d+|[A-Z]{1,3}\d{1,4})$", clean, re.IGNORECASE)
            )
            is_id_cand = (
                not is_roll_cand
                and id_col is not None
                and id_col.min_x - 10 <= b["cx"] <= id_col.max_x + 10
                and re.match(r"^(STU\d+|[A-Z]{2,4}\d{2,4})$", clean, re.IGNORECASE)
            )
            if is_roll_cand or is_id_cand:
                anchor_boxes.append(b)

        # Remove duplicate anchors in virtually the same row (e.g. Roll 001 and STU001 on the same row)
        unique_anchors: List[Dict[str, Any]] = []
        for ab in anchor_boxes:
            if not unique_anchors or abs(ab["cy"] - unique_anchors[-1]["cy"]) > 16.0:
                unique_anchors.append(ab)

        # If clean row anchors exist (e.g. 5 roll numbers for 5 students)
        if len(unique_anchors) >= 2:
            unique_anchors.sort(key=lambda b: b["cy"])
            row_bands: List[Tuple[float, float, float]] = []  # (y_start, y_end, cy)

            for i in range(len(unique_anchors)):
                cy_i = unique_anchors[i]["cy"]
                # Top boundary of row band
                if i == 0:
                    y_start = cy_i - (unique_anchors[1]["cy"] - cy_i) / 2.0
                else:
                    y_start = (unique_anchors[i - 1]["cy"] + cy_i) / 2.0

                # Bottom boundary of row band
                if i == len(unique_anchors) - 1:
                    y_end = cy_i + (cy_i - unique_anchors[i - 1]["cy"]) / 2.0
                else:
                    y_end = (cy_i + unique_anchors[i + 1]["cy"]) / 2.0

                row_bands.append((y_start, y_end, cy_i))

            # Assign each data box to its corresponding row band
            physical_rows: List[PhysicalRow] = [
                PhysicalRow(row_index=i + 1, cy=band[2], min_y=band[0], max_y=band[1])
                for i, band in enumerate(row_bands)
            ]

            for b in sorted_boxes:
                # Find best matching row band
                best_row = None
                for pr in physical_rows:
                    if pr.min_y <= b["cy"] <= pr.max_y:
                        best_row = pr
                        break

                if best_row is None:
                    # Find closest row band by cy distance
                    closest = min(physical_rows, key=lambda pr: abs(b["cy"] - pr.cy))
                    if abs(b["cy"] - closest.cy) <= (closest.max_y - closest.min_y) * 0.90:
                        best_row = closest

                if best_row is not None:
                    best_row.boxes.append(b)

            # Sort boxes in each row horizontally by min_x
            for pr in physical_rows:
                pr.boxes.sort(key=lambda b: b["min_x"])

            # Filter out empty rows
            return [pr for pr in physical_rows if len(pr.boxes) > 0]

        # Fallback: Multi-column vertical clustering
        heights = [b["h"] for b in sorted_boxes]
        median_h = float(np.median(heights)) if heights else 18.0
        max_cy_diff = min(max(median_h * 0.70, 12.0), 22.0)

        clustered_rows: List[List[Dict[str, Any]]] = []
        for box in sorted_boxes:
            best_row = None
            min_dist = float("inf")

            for r in clustered_rows:
                row_cy = sum(b["cy"] for b in r) / len(r)
                dist = abs(box["cy"] - row_cy)
                if dist <= max_cy_diff:
                    # Column collision check: If row already has a box in substantially the same X region
                    has_x_collision = any(
                        max(b["min_x"], box["min_x"]) < min(b["max_x"], box["max_x"]) - 8.0
                        for b in r
                    )
                    if not has_x_collision and dist < min_dist:
                        min_dist = dist
                        best_row = r

            if best_row is not None:
                best_row.append(box)
            else:
                clustered_rows.append([box])

        # Convert to PhysicalRow objects
        physical_rows = []
        for idx, r in enumerate(clustered_rows):
            r.sort(key=lambda b: b["min_x"])
            avg_cy = sum(b["cy"] for b in r) / len(r)
            min_y = min(b["min_y"] for b in r)
            max_y = max(b["max_y"] for b in r)
            physical_rows.append(PhysicalRow(row_index=idx + 1, cy=avg_cy, min_y=min_y, max_y=max_y, boxes=r))

        physical_rows.sort(key=lambda pr: pr.cy)
        return physical_rows

    def _read_cells_and_reconstruct(
        self,
        physical_rows: List[PhysicalRow],
        columns: List[TableColumn],
    ) -> List[Dict[str, Any]]:
        """
        Reads cells in each physical row according to column layout and reconstructs student records.
        Preserves raw values: raw_identifier, raw_student_id, raw_name, raw_attendance_mark.
        """
        records: List[Dict[str, Any]] = []

        roll_col = next((c for c in columns if c.col_type == ColumnType.ROLL_NO), None)
        id_col = next((c for c in columns if c.col_type == ColumnType.STUDENT_ID), None)
        name_col = next((c for c in columns if c.col_type == ColumnType.NAME), None)
        att_col = next((c for c in columns if c.col_type == ColumnType.ATTENDANCE), None)

        for pr in physical_rows:
            roll_boxes = []
            id_boxes = []
            name_boxes = []
            att_boxes = []

            for b in pr.boxes:
                cx = b["cx"]
                # Determine which column the box belongs to
                assigned = False

                if att_col and att_col.min_x <= cx <= att_col.max_x:
                    att_boxes.append(b)
                    assigned = True
                elif roll_col and roll_col.min_x <= cx <= roll_col.max_x:
                    roll_boxes.append(b)
                    assigned = True
                elif id_col and id_col.min_x <= cx <= id_col.max_x:
                    id_boxes.append(b)
                    assigned = True
                elif name_col and name_col.min_x <= cx <= name_col.max_x:
                    name_boxes.append(b)
                    assigned = True

                # Fallback assignment by nearest column
                if not assigned:
                    nearest_col = min(columns, key=lambda c: abs(cx - c.cx))
                    if nearest_col.col_type == ColumnType.ATTENDANCE:
                        att_boxes.append(b)
                    elif nearest_col.col_type == ColumnType.ROLL_NO:
                        roll_boxes.append(b)
                    elif nearest_col.col_type == ColumnType.STUDENT_ID:
                        id_boxes.append(b)
                    else:
                        name_boxes.append(b)

            # Extract raw values
            raw_id = " ".join(b["text"].strip() for b in roll_boxes).strip() if roll_boxes else None
            raw_stu_id = " ".join(b["text"].strip() for b in id_boxes).strip() if id_boxes else None
            raw_name = " ".join(b["text"].strip() for b in name_boxes).strip() if name_boxes else None
            raw_mark = " ".join(b["text"].strip() for b in att_boxes).strip() if att_boxes else None

            # Clean OCR artifacts in roll number (e.g. '0uz' -> '002', '0u4' -> '004')
            if raw_id:
                m_fuzzy = re.match(r"^0[oOuU](\d)$", raw_id)
                if m_fuzzy:
                    raw_id = f"00{m_fuzzy.group(1)}"
                m_fuzzy2 = re.match(r"^0[oOuU](\d{2})$", raw_id)
                if m_fuzzy2:
                    raw_id = f"0{m_fuzzy2.group(1)}"

            # Cross-column extraction: Check if Student ID was placed in Name or Roll
            if not raw_stu_id and raw_name:
                m_id = re.search(r"\b(STU\d+|[A-Z]{2,4}\d{2,5})\b", raw_name, re.IGNORECASE)
                if m_id:
                    raw_stu_id = m_id.group(1).upper()
                    raw_name = (raw_name[:m_id.start()] + raw_name[m_id.end():]).strip(" |,-")

            if not raw_stu_id and raw_id:
                m_id = re.match(r"^(STU\d+|[A-Z]{2,4}\d{2,5})$", raw_id, re.IGNORECASE)
                if m_id:
                    raw_stu_id = m_id.group(1).upper()

            # If roll column contained combined roll + student id (e.g. "001 STU001")
            if raw_id:
                m_combined = re.match(r"^(\d{1,4})\s+(STU\d+|[A-Z]{2,4}\d{2,5})$", raw_id, re.IGNORECASE)
                if m_combined:
                    raw_id = m_combined.group(1)
                    raw_stu_id = m_combined.group(2).upper()

            # Clean OCR artifacts in student ID (e.g. 'STUOO1' -> 'STU001', 'STUO03' -> 'STU003')
            if raw_stu_id:
                m_stu = re.match(r"^([A-Za-z]+)(.*)$", raw_stu_id)
                if m_stu:
                    prefix = m_stu.group(1).upper()
                    rest = m_stu.group(2)
                    while len(prefix) > 3 and prefix.endswith("O"):
                        prefix = prefix[:-1]
                        rest = "0" + rest
                    rest_clean = re.sub(r"[oO]", "0", rest)
                    raw_stu_id = f"{prefix}{rest_clean}"

            # Clean OCR artifacts in student name (e.g. 'Rahul $.' -> 'Rahul S.')
            if raw_name:
                raw_name = re.sub(r"\$(\.|\b)", r"S\1", raw_name)

            # Calculate box confidences
            row_confs = [b["conf"] for b in pr.boxes]
            avg_conf = sum(row_confs) / len(row_confs) if row_confs else 0.85

            records.append({
                "raw_identifier": raw_id,
                "raw_student_id": raw_stu_id,
                "raw_name": raw_name,
                "raw_attendance_mark": raw_mark,
                "row_confidence": avg_conf,
                "boxes": pr.boxes,
            })

        return records

    def _normalize_records(
        self,
        raw_records: List[Dict[str, Any]],
    ) -> List[AttendanceItem]:
        """
        Normalizes raw records into AttendanceItem schemas.
        Applies Rule 9 (attendance comes strictly from attendance column, numeric marks = PRESENT)
        and Rule 10 (NEVER convert OCR garbage into ABSENT).
        """
        items: List[AttendanceItem] = []

        for rec in raw_records:
            raw_mark = rec.get("raw_attendance_mark")
            raw_name = rec.get("raw_name")
            raw_id = rec.get("raw_identifier")
            raw_stu_id = rec.get("raw_student_id")
            row_conf = rec.get("row_confidence", 0.85)

            # Check if this row has student identity
            has_identity = bool(raw_id or raw_stu_id or (raw_name and len(raw_name) >= 2))

            # Rule 9: Attendance comes strictly from the Attendance column
            if raw_mark is not None and str(raw_mark).strip():
                status, norm_conf, clean_mark = normalize_attendance(raw_mark, is_in_attendance_column=True)
                overall_conf = round(min(max(norm_conf * 0.75 + row_conf * 0.25, 0.40), 0.99), 2)
            else:
                # Row has no attendance mark
                if has_identity:
                    # Valid student row without mark -> low confidence ABSENT to trigger teacher review (Rule 13)
                    status = AttendanceStatus.ABSENT
                    overall_conf = 0.45
                    clean_mark = None
                else:
                    # Garbage row without identity and without mark -> skip
                    continue

            # Fallback identifier if only student_id is available
            effective_identifier = raw_id or raw_stu_id

            items.append(AttendanceItem(
                raw_name=raw_name,
                raw_identifier=effective_identifier,
                raw_student_id=raw_stu_id,
                raw_attendance_mark=clean_mark if raw_mark else None,
                status=status,
                confidence=overall_conf,
            ))

        return items

    def _validate_student_record(self, item: AttendanceItem) -> bool:
        """
        Rule 14: Validation BEFORE matching.
        Rejects records that are obviously:
        - page metadata (Page No., Date.)
        - table headers (Roll No, Student ID, Student Name, Attendance)
        - random OCR fragments or notebook lines
        - unrelated text
        """
        name = (item.raw_name or "").strip()
        ident = (item.raw_identifier or "").strip()
        stu_id = (item.raw_student_id or "").strip()

        # Reject if all identity fields are empty
        if not name and not ident and not stu_id:
            logger.debug(f"[Validation Reject] Discarded empty row: {item}")
            return False

        # Reject obvious page metadata in raw_name
        if name and PAGE_METADATA_REGEX.match(name):
            logger.info(f"[Validation Reject] Discarded page metadata record: raw_name='{name}'")
            return False

        # Reject table headers in raw_name
        lower_name = name.lower()
        for kw_list in HEADER_KEYWORDS_MAP.values():
            if lower_name in kw_list or any(lower_name == kw for kw in kw_list):
                logger.info(f"[Validation Reject] Discarded table header record: raw_name='{name}'")
                return False

        # Reject table headers in raw_identifier
        lower_id = ident.lower()
        if lower_id in ("roll", "rollno", "roll no", "sr", "s.no", "no", "page", "date", "id"):
            logger.info(f"[Validation Reject] Discarded header identifier: raw_identifier='{ident}'")
            return False

        # Reject random fragments: single punctuation or noise without identifier
        if not ident and not stu_id:
            if len(name) <= 1 or name in (".", ",", "-", "|", "/", "\\", ":", ";", "_"):
                logger.debug(f"[Validation Reject] Discarded fragment: raw_name='{name}'")
                return False

        # Record is valid!
        return True


ocr_extractor = AttendanceTableExtractor()
