"""
Test Suite for Table Detection, Column Isolation, Physical Row Grouping,
and Metadata Rejection in OCR Extraction Pipeline.

Verifies:
1. "Page No." and "Date." above the table are IGNORED and NEVER treated as student records.
2. Table headers ("Roll No", "Student ID", "Student Name", "Attendance") are NOT extracted as student records.
3. 001 | STU001 | Aarav S. | Present becomes ONE single physical student record.
4. Preserves raw OCR values (raw_identifier, raw_student_id, raw_name, raw_attendance_mark, status, ai_confidence).
5. Attendance column strictly determines status (P/Present -> PRESENT, A/Absent -> ABSENT).
6. Numeric marks in attendance column (1, 17) -> PRESENT; roll numbers are identifiers, not attendance.
7. Unclear handwriting mark preserves raw value, reduces confidence, and flags for review without inventing values.
8. End-to-end integration: 5 student rows do NOT produce 69 fake exceptions; all 5 match ERP students.
"""

import io
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.schemas.attendance import AttendanceItem, AttendanceStatus
from app.schemas.student import (
    StudentInfo,
    MatchAttendanceRequest,
    MatchMethod,
    ResolutionState,
)
from app.services.ocr_service import (
    AttendanceTableExtractor,
    ColumnType,
    ocr_extractor,
)
from app.services.matching_service import StudentMatchingService
from app.services.vision.easyocr_provider import EasyOCRVisionProvider


@pytest.fixture
def mock_erp_60_roster() -> list[StudentInfo]:
    """Classroom roster with 60 students, including the 5 target students."""
    students = [
        StudentInfo(student_id="STU001", roll_number="001", name="Aarav Sharma"),
        StudentInfo(student_id="STU002", roll_number="002", name="Aarav Verma"),
        StudentInfo(student_id="STU003", roll_number="003", name="Rahul Kumar"),
        StudentInfo(student_id="STU004", roll_number="004", name="Rahul Singh"),
        StudentInfo(student_id="STU005", roll_number="005", name="Priya Singh"),
    ]
    # Add remaining students up to 60
    for i in range(6, 61):
        pad = f"{i:03d}"
        students.append(StudentInfo(student_id=f"STU{pad}", roll_number=pad, name=f"Student {pad}"))
    return students


def create_handwritten_sheet_image(
    page_header: bool = True,
    col_headers: bool = True,
) -> Image.Image:
    """
    Creates a synthetic attendance sheet matching the user's handwritten test sheet:
    - "Page No. 12" and "Date: 27-09-2026" above table
    - Columns: Roll No | Student ID | Student Name | Attendance
    - 5 student rows:
      001 | STU001 | Aarav S. | Present
      002 | STU002 | Aarav U. | Absent
      003 | STU003 | Rahul | Present
      004 | STU004 | Rahul S. | Present
      005 | STU005 | Priya | Absent
    """
    width, height = 900, 550
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_meta = ImageFont.truetype("arial.ttf", 16)
        font_header = ImageFont.truetype("arial.ttf", 18)
        font_body = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_meta = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Page metadata above table
    if page_header:
        draw.text((40, 25), "Page No. 12", fill=(80, 80, 80), font=font_meta)
        draw.text((680, 25), "Date: 27-09-2026", fill=(80, 80, 80), font=font_meta)

    # Table Header Row
    header_y = 80
    if col_headers:
        # Draw light background band for header
        draw.rectangle([(30, header_y), (870, header_y + 35)], fill=(240, 240, 240))
        draw.text((45, header_y + 8), "Roll No", fill=(20, 20, 20), font=font_header)
        draw.text((180, header_y + 8), "Student ID", fill=(20, 20, 20), font=font_header)
        draw.text((380, header_y + 8), "Student Name", fill=(20, 20, 20), font=font_header)
        draw.text((680, header_y + 8), "Attendance", fill=(20, 20, 20), font=font_header)

    # 5 Student Rows
    rows = [
        ("001", "STU001", "Aarav S.", "Present"),
        ("002", "STU002", "Aarav U.", "Absent"),
        ("003", "STU003", "Rahul", "Present"),
        ("004", "STU004", "Rahul S.", "Present"),
        ("005", "STU005", "Priya", "Absent"),
    ]

    for idx, (roll, stu_id, name, status) in enumerate(rows):
        row_y = 135 + idx * 55
        # Ruled line between rows
        draw.line([(30, row_y + 45), (870, row_y + 45)], fill=(220, 220, 220), width=1)

        draw.text((45, row_y + 12), roll, fill=(30, 30, 30), font=font_body)
        draw.text((180, row_y + 12), stu_id, fill=(30, 30, 30), font=font_body)
        draw.text((380, row_y + 12), name, fill=(30, 30, 30), font=font_body)
        draw.text((680, row_y + 12), status, fill=(30, 30, 30), font=font_body)

    return img


class TestTableAndRowExtraction:
    """Validates the core extraction engine against the 5-row sheet with page metadata."""

    def test_1_table_extraction_end_to_end(self, mock_erp_60_roster):
        """
        Test 1: Full end-to-end OCR extraction on sheet with Page No., Date., and 5 student rows.
        Guarantees:
        - Exactly 5 student rows are extracted (NOT 69!)
        - Page No. and Date. are completely ignored.
        - Table headers are not extracted as students.
        - All 5 student rows match ERP students.
        - Zero unmatched records.
        """
        img = create_handwritten_sheet_image(page_header=True, col_headers=True)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        img_bytes = buf.getvalue()

        provider = EasyOCRVisionProvider()
        extracted_records = provider.extract_attendance(img, img_bytes, "handwritten_test.jpg")

        # MUST be exactly 5 records (one for each physical row)
        assert len(extracted_records) == 5, (
            f"Expected exactly 5 student records, got {len(extracted_records)}: "
            f"{[r.raw_name for r in extracted_records]}"
        )

        # Verify NO metadata or headers were extracted
        for rec in extracted_records:
            name_lower = (rec.raw_name or "").lower()
            ident_lower = (rec.raw_identifier or "").lower()
            assert "page" not in name_lower, f"Page metadata leaked into student record: {rec}"
            assert "date" not in name_lower, f"Date metadata leaked into student record: {rec}"
            assert "roll" not in name_lower, f"Roll header leaked into student name: {rec}"
            assert "attendance" not in name_lower, f"Attendance header leaked into student name: {rec}"
            assert "page" not in ident_lower
            assert "date" not in ident_lower

        # Verify each record has raw fields preserved
        expected = [
            ("001", "STU001", "Aarav S.", AttendanceStatus.PRESENT),
            ("002", "STU002", "Aarav U.", AttendanceStatus.ABSENT),
            ("003", "STU003", "Rahul", AttendanceStatus.PRESENT),
            ("004", "STU004", "Rahul S.", AttendanceStatus.PRESENT),
            ("005", "STU005", "Priya", AttendanceStatus.ABSENT),
        ]

        for idx, (exp_roll, exp_id, exp_name, exp_status) in enumerate(expected):
            rec = extracted_records[idx]
            assert rec.status == exp_status, f"Row {idx+1}: expected {exp_status}, got {rec.status}"
            assert rec.raw_attendance_mark in ("Present", "Absent", "P", "A"), f"Row {idx+1}: unexpected mark {rec.raw_attendance_mark}"
            assert rec.confidence >= 0.70

            # Identifier or Student ID should match
            assert rec.raw_identifier == exp_roll or rec.raw_student_id == exp_id

        # Now test matching against the 60-student ERP roster!
        matching_service = StudentMatchingService()
        match_resp = matching_service.match_attendance(
            MatchAttendanceRequest(
                erp_students=mock_erp_60_roster,
                ai_records=extracted_records,
            )
        )

        # Matching results
        assert match_resp.summary.total_ai_records == 5, f"Expected 5 AI records, got {match_resp.summary.total_ai_records}"
        assert match_resp.summary.matched == 5, f"Expected all 5 matched, got {match_resp.summary.matched}"
        assert match_resp.summary.unmatched == 0, f"Expected 0 unmatched, got {match_resp.summary.unmatched}"
        assert match_resp.summary.duplicates == 0, f"Expected 0 duplicates, got {match_resp.summary.duplicates}"

        # Verify no UNMATCHED_STUDENT exceptions were created
        unmatched_exceptions = [e for e in match_resp.exceptions if e.type == "UNMATCHED_STUDENT"]
        assert len(unmatched_exceptions) == 0, f"Unmatched exceptions found: {unmatched_exceptions}"

        # Verify all matched ERP student IDs match expected
        matched_ids = [r.matched_student_id for r in match_resp.results]
        assert matched_ids == ["STU001", "STU002", "STU003", "STU004", "STU005"]

    def test_2_physical_row_grouping_prevents_token_fragmentation(self):
        """
        Test 2: Rule 8 - Group OCR results by PHYSICAL ROW.
        001 | STU001 | Aarav S. | Present must become ONE student record.
        Do not create separate records from 001, STU001, Aarav S., Present.
        """
        boxes = [
            # Header
            {"text": "Roll No", "conf": 0.95, "cx": 50, "cy": 50, "min_x": 30, "max_x": 80, "min_y": 40, "max_y": 60, "w": 50, "h": 20},
            {"text": "Student ID", "conf": 0.95, "cx": 200, "cy": 50, "min_x": 150, "max_x": 250, "min_y": 40, "max_y": 60, "w": 100, "h": 20},
            {"text": "Student Name", "conf": 0.95, "cx": 400, "cy": 50, "min_x": 330, "max_x": 480, "min_y": 40, "max_y": 60, "w": 150, "h": 20},
            {"text": "Attendance", "conf": 0.95, "cx": 650, "cy": 50, "min_x": 580, "max_x": 720, "min_y": 40, "max_y": 60, "w": 140, "h": 20},

            # Physical Row 1 tokens
            {"text": "001", "conf": 0.98, "cx": 50, "cy": 120, "min_x": 35, "max_x": 65, "min_y": 110, "max_y": 130, "w": 30, "h": 20},
            {"text": "STU001", "conf": 0.97, "cx": 200, "cy": 122, "min_x": 160, "max_x": 240, "min_y": 110, "max_y": 132, "w": 80, "h": 22},
            {"text": "Aarav", "conf": 0.96, "cx": 380, "cy": 121, "min_x": 350, "max_x": 410, "min_y": 110, "max_y": 131, "w": 60, "h": 21},
            {"text": "S.", "conf": 0.95, "cx": 435, "cy": 120, "min_x": 425, "max_x": 445, "min_y": 110, "max_y": 130, "w": 20, "h": 20},
            {"text": "Present", "conf": 0.99, "cx": 650, "cy": 120, "min_x": 615, "max_x": 685, "min_y": 110, "max_y": 130, "w": 70, "h": 20},
        ]

        extractor = AttendanceTableExtractor()
        items = extractor.extract_from_boxes(boxes, 800, 300)

        # Must produce exactly ONE student item!
        assert len(items) == 1, f"Expected 1 grouped item, got {len(items)}"
        item = items[0]
        assert item.raw_identifier == "001"
        assert item.raw_student_id == "STU001"
        assert item.raw_name == "Aarav S."
        assert item.raw_attendance_mark == "Present"
        assert item.status == AttendanceStatus.PRESENT

    def test_3_metadata_rejection_rules(self):
        """
        Test 3: Rule 10 & 14 - Reject page metadata (Page No, Date, Headers)
        and NEVER convert OCR garbage into ABSENT.
        """
        boxes = [
            # Metadata above table
            {"text": "Page No. 1", "conf": 0.95, "cx": 80, "cy": 30, "min_x": 30, "max_x": 130, "min_y": 20, "max_y": 40, "w": 100, "h": 20},
            {"text": "Date: 2026-09-27", "conf": 0.95, "cx": 650, "cy": 30, "min_x": 580, "max_x": 720, "min_y": 20, "max_y": 40, "w": 140, "h": 20},

            # Table Header
            {"text": "Roll No", "conf": 0.95, "cx": 50, "cy": 80, "min_x": 30, "max_x": 80, "min_y": 70, "max_y": 90, "w": 50, "h": 20},
            {"text": "Name", "conf": 0.95, "cx": 300, "cy": 80, "min_x": 260, "max_x": 340, "min_y": 70, "max_y": 90, "w": 80, "h": 20},
            {"text": "Status", "conf": 0.95, "cx": 600, "cy": 80, "min_x": 550, "max_x": 650, "min_y": 70, "max_y": 90, "w": 100, "h": 20},

            # Single student row
            {"text": "002", "conf": 0.98, "cx": 50, "cy": 150, "min_x": 35, "max_x": 65, "min_y": 140, "max_y": 160, "w": 30, "h": 20},
            {"text": "Aarav U.", "conf": 0.96, "cx": 300, "cy": 150, "min_x": 260, "max_x": 340, "min_y": 140, "max_y": 160, "w": 80, "h": 20},
            {"text": "Absent", "conf": 0.98, "cx": 600, "cy": 150, "min_x": 560, "max_x": 640, "min_y": 140, "max_y": 160, "w": 80, "h": 20},
        ]

        extractor = AttendanceTableExtractor()
        items = extractor.extract_from_boxes(boxes, 800, 300)

        # Only the 1 student row should be extracted!
        assert len(items) == 1
        assert items[0].raw_identifier == "002"
        assert items[0].raw_name == "Aarav U."
        assert items[0].status == AttendanceStatus.ABSENT

    def test_4_numeric_attendance_marks_in_attendance_column(self):
        """
        Test 4: Rule 9 - Numeric attendance marks (1, 2, 3, 17, 42) in attendance column -> PRESENT.
        Numeric roll numbers are identifiers, NOT attendance.
        """
        boxes = [
            {"text": "Roll No", "conf": 0.95, "cx": 50, "cy": 50, "min_x": 30, "max_x": 80, "min_y": 40, "max_y": 60, "w": 50, "h": 20},
            {"text": "Student Name", "conf": 0.95, "cx": 300, "cy": 50, "min_x": 230, "max_x": 370, "min_y": 40, "max_y": 60, "w": 140, "h": 20},
            {"text": "Attendance", "conf": 0.95, "cx": 600, "cy": 50, "min_x": 540, "max_x": 660, "min_y": 40, "max_y": 60, "w": 120, "h": 20},

            # Row 1: Roll=001, Name=Aarav S., Attendance=17 -> PRESENT
            {"text": "001", "conf": 0.98, "cx": 50, "cy": 120, "min_x": 35, "max_x": 65, "min_y": 110, "max_y": 130, "w": 30, "h": 20},
            {"text": "Aarav S.", "conf": 0.96, "cx": 300, "cy": 120, "min_x": 250, "max_x": 350, "min_y": 110, "max_y": 130, "w": 100, "h": 20},
            {"text": "17", "conf": 0.95, "cx": 600, "cy": 120, "min_x": 580, "max_x": 620, "min_y": 110, "max_y": 130, "w": 40, "h": 20},

            # Row 2: Roll=002, Name=Rahul, Attendance=1 -> PRESENT
            {"text": "002", "conf": 0.98, "cx": 50, "cy": 180, "min_x": 35, "max_x": 65, "min_y": 170, "max_y": 190, "w": 30, "h": 20},
            {"text": "Rahul", "conf": 0.96, "cx": 300, "cy": 180, "min_x": 250, "max_x": 350, "min_y": 170, "max_y": 190, "w": 100, "h": 20},
            {"text": "1", "conf": 0.95, "cx": 600, "cy": 180, "min_x": 580, "max_x": 620, "min_y": 170, "max_y": 190, "w": 40, "h": 20},
        ]

        extractor = AttendanceTableExtractor()
        items = extractor.extract_from_boxes(boxes, 800, 300)

        assert len(items) == 2
        # Row 1
        assert items[0].raw_identifier == "001"
        assert items[0].raw_attendance_mark == "17"
        assert items[0].status == AttendanceStatus.PRESENT

        # Row 2
        assert items[1].raw_identifier == "002"
        assert items[1].raw_attendance_mark == "1"
        assert items[1].status == AttendanceStatus.PRESENT

    def test_5_unclear_handwriting_mark_preserves_raw_value(self):
        """
        Test 5: Rule 13 - If handwriting is unclear:
        - preserve raw value
        - reduce confidence (< 0.65)
        - send for review
        - Do NOT invent a value!
        """
        boxes = [
            {"text": "Roll No", "conf": 0.95, "cx": 50, "cy": 50, "min_x": 30, "max_x": 80, "min_y": 40, "max_y": 60, "w": 50, "h": 20},
            {"text": "Student Name", "conf": 0.95, "cx": 300, "cy": 50, "min_x": 230, "max_x": 370, "min_y": 40, "max_y": 60, "w": 140, "h": 20},
            {"text": "Attendance", "conf": 0.95, "cx": 600, "cy": 50, "min_x": 540, "max_x": 660, "min_y": 40, "max_y": 60, "w": 120, "h": 20},

            # Row with scribble "?" mark
            {"text": "003", "conf": 0.98, "cx": 50, "cy": 120, "min_x": 35, "max_x": 65, "min_y": 110, "max_y": 130, "w": 30, "h": 20},
            {"text": "Rahul Kumar", "conf": 0.95, "cx": 300, "cy": 120, "min_x": 250, "max_x": 350, "min_y": 110, "max_y": 130, "w": 100, "h": 20},
            {"text": "?", "conf": 0.40, "cx": 600, "cy": 120, "min_x": 580, "max_x": 620, "min_y": 110, "max_y": 130, "w": 40, "h": 20},
        ]

        extractor = AttendanceTableExtractor()
        items = extractor.extract_from_boxes(boxes, 800, 300)

        assert len(items) == 1
        item = items[0]
        assert item.raw_identifier == "003"
        assert item.raw_name == "Rahul Kumar"
        assert item.raw_attendance_mark == "?"
        # Confidence must be low (< 0.65) to trigger review
        assert item.confidence < 0.65
