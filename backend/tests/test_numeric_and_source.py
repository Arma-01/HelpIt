"""
Phase 2.2 Test Suite: Numeric Attendance & Real Uploaded-List Source of Truth
Validates:
1. Numeric continuous attendance sequences (1, 2, 3, 4...) -> PRESENT
2. Numeric sequences with absences (1, 2, A, 3, 4, A, 5)
3. Numeric counts starting at arbitrary values (17, 18, A, 19, 20)
4. Column separation: Roll numbers vs Attendance count marks
5. Uploaded sheet as sole source of truth (does not fabricate or replace with mock ERP students)
6. Uploaded student not in ERP -> UNMATCHED
7. Missing uploaded student -> reported in exceptions, NEVER auto-marked absent
8. Duplicate / conflicting records -> NEEDS_REVIEW / DUPLICATE_DETECTED
9. End-to-end real image extraction, normalization, and ERP matching
10. API endpoint validation preserving raw_attendance_mark
"""

import io
import pytest
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.attendance import AttendanceItem, AttendanceStatus, AttendanceProcessResponse
from app.schemas.student import (
    StudentInfo,
    MatchAttendanceRequest,
    MatchMethod,
    ResolutionState,
)
from app.services.attendance_normalization import normalize_attendance
from app.services.matching_service import StudentMatchingService
from app.services.vision.easyocr_provider import EasyOCRVisionProvider


@pytest.fixture
def sample_erp_roster() -> list[StudentInfo]:
    """Sample classroom ERP roster."""
    return [
        StudentInfo(student_id="STU001", roll_number="001", name="Aarav Sharma"),
        StudentInfo(student_id="STU002", roll_number="002", name="Rahul Kumar"),
        StudentInfo(student_id="STU003", roll_number="003", name="Priya Singh"),
        StudentInfo(student_id="STU004", roll_number="004", name="Diya Patel"),
        StudentInfo(student_id="STU005", roll_number="005", name="Sneha Rao"),
        StudentInfo(student_id="STU006", roll_number="006", name="Kabir Singh"),
        StudentInfo(student_id="STU007", roll_number="007", name="Mira Nair"),
        StudentInfo(student_id="STU025", roll_number="025", name="Vikram Aditya"),
    ]


class TestNumericAttendanceNormalization:
    """Tests for Phase 2.2 Numeric Attendance Counting Support."""

    def test_1_numeric_continuous_attendance(self):
        """
        Test 1: Continuous attendance counts (1, 2, 3, 4) in attendance column.
        All must be interpreted as PRESENT with preserved raw_attendance_mark.
        """
        marks = ["1", "2", "3", "4"]
        for mark in marks:
            status, conf, raw = normalize_attendance(mark, is_in_attendance_column=True)
            assert status == AttendanceStatus.PRESENT, f"Mark '{mark}' should be PRESENT"
            assert conf >= 0.85, f"Numeric count '{mark}' should have high confidence"
            assert raw == mark, f"Raw mark should be preserved as '{mark}', got '{raw}'"

    def test_2_numeric_with_absent(self):
        """
        Test 2: Numeric attendance with absent marks (1, 2, A, 3, 4, A, 5).
        Positive integers -> PRESENT; 'A' / 'ABSENT' -> ABSENT.
        """
        sequence = [
            ("1", AttendanceStatus.PRESENT),
            ("2", AttendanceStatus.PRESENT),
            ("A", AttendanceStatus.ABSENT),
            ("3", AttendanceStatus.PRESENT),
            ("4", AttendanceStatus.PRESENT),
            ("A", AttendanceStatus.ABSENT),
            ("5", AttendanceStatus.PRESENT),
        ]
        for mark, expected_status in sequence:
            status, conf, raw = normalize_attendance(mark, is_in_attendance_column=True)
            assert status == expected_status, f"Mark '{mark}' expected {expected_status}, got {status}"
            assert conf >= 0.85
            assert raw == mark

    def test_3_numeric_non_one_start(self):
        """
        Test 3: Numeric counts that do NOT start at 1 (17, 18, A, 19, 20).
        Arbitrary starting count must be accepted as PRESENT.
        """
        sequence = [
            ("17", AttendanceStatus.PRESENT),
            ("18", AttendanceStatus.PRESENT),
            ("A", AttendanceStatus.ABSENT),
            ("19", AttendanceStatus.PRESENT),
            ("20", AttendanceStatus.PRESENT),
        ]
        for mark, expected_status in sequence:
            status, conf, raw = normalize_attendance(mark, is_in_attendance_column=True)
            assert status == expected_status
            assert raw == mark

    def test_4_roll_vs_attendance_separation(self):
        """
        Test 4: Roll Number vs Attendance Separation.
        When Roll = 17 and Attendance count = 22:
        Roll must not be confused with attendance, and count 22 must not be treated as roll.
        """
        # Inside attendance column: 22 is an attendance mark -> PRESENT
        att_status, att_conf, att_raw = normalize_attendance("22", is_in_attendance_column=True)
        assert att_status == AttendanceStatus.PRESENT
        assert att_raw == "22"

        # Outside attendance column: numeric without column context is not interpreted as attendance
        non_col_status, non_col_conf, _ = normalize_attendance("17", is_in_attendance_column=False)
        assert non_col_conf < 0.65, "Numeric outside attendance column should not have high attendance confidence"


class TestUploadedSourceOfTruth:
    """Tests guaranteeing that the uploaded sheet is the sole source of truth."""

    def test_5_uploaded_sheet_differs_from_mock_erp(self, sample_erp_roster):
        """
        Test 5: Uploaded sheet contains a different set of students than ERP.
        The matching service must only produce results for the students in the uploaded items.
        It must NEVER fabricate or replace items with students from the ERP.
        """
        # Uploaded list only has 2 students
        uploaded_items = [
            AttendanceItem(
                raw_identifier="001",
                raw_name="Aarav Sharma",
                raw_attendance_mark="1",
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            ),
            AttendanceItem(
                raw_identifier="003",
                raw_name="Priya Singh",
                raw_attendance_mark="2",
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            ),
        ]

        service = StudentMatchingService()
        result = service.match_attendance(
            MatchAttendanceRequest(erp_students=sample_erp_roster, ai_records=uploaded_items)
        )

        # Result count must exactly match the uploaded count (2), not the ERP count (8)
        assert len(result.results) == 2, "Matching results must reflect uploaded items only"
        assert result.summary.total_ai_records == 2
        assert result.summary.matched == 2

        matched_names = {r.matched_name for r in result.results}
        assert matched_names == {"Aarav Sharma", "Priya Singh"}

    def test_6_uploaded_student_not_in_erp(self, sample_erp_roster):
        """
        Test 6: Student on uploaded sheet ("Rohan Mehta", roll 18) does not exist in ERP.
        System must mark as UNMATCHED and NEVER force a false match to an unrelated student.
        """
        uploaded_items = [
            AttendanceItem(
                raw_identifier="018",
                raw_name="Rohan Mehta",
                raw_attendance_mark="18",
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            )
        ]

        service = StudentMatchingService()
        result = service.match_attendance(
            MatchAttendanceRequest(erp_students=sample_erp_roster, ai_records=uploaded_items)
        )

        assert len(result.results) == 1
        item = result.results[0]
        assert item.resolution == ResolutionState.UNMATCHED
        assert item.matched_student_id is None
        assert item.raw_attendance_mark == "18"
        assert item.status == AttendanceStatus.PRESENT
        assert result.summary.unmatched == 1

    def test_7_missing_uploaded_student(self, sample_erp_roster):
        """
        Test 7: ERP student STU025 (Vikram Aditya) is NOT in the uploaded sheet.
        System must list student in exceptions / erp_students_not_detected,
        and MUST NEVER automatically mark the student as ABSENT in results.
        """
        uploaded_items = [
            AttendanceItem(
                raw_identifier="001",
                raw_name="Aarav Sharma",
                raw_attendance_mark="1",
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            )
        ]

        service = StudentMatchingService()
        result = service.match_attendance(
            MatchAttendanceRequest(erp_students=sample_erp_roster, ai_records=uploaded_items)
        )

        # Vikram Aditya should be in erp_students_not_detected
        missing_ids = [s.student_id for s in result.erp_students_not_detected]
        assert "STU025" in missing_ids

        # Results must NOT contain Vikram Aditya
        result_stu_ids = [r.matched_student_id for r in result.results if r.matched_student_id]
        assert "STU025" not in result_stu_ids

        # Exception must be logged
        missing_exceptions = [e for e in result.exceptions if e.type == "MISSING_ERP_STUDENT"]
        assert any("Vikram Aditya" in e.message for e in missing_exceptions)

    def test_8_duplicate_attendance_record(self, sample_erp_roster):
        """
        Test 8: Conflicting duplicate records in uploaded sheet for same student.
        Both records must be flagged with NEEDS_REVIEW and DUPLICATE_DETECTED.
        """
        uploaded_items = [
            AttendanceItem(
                raw_identifier="001",
                raw_name="Aarav Sharma",
                raw_attendance_mark="17",
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            ),
            AttendanceItem(
                raw_identifier="001",
                raw_name="Aarav Sharma",
                raw_attendance_mark="A",
                status=AttendanceStatus.ABSENT,
                confidence=0.95,
            ),
        ]

        service = StudentMatchingService()
        result = service.match_attendance(
            MatchAttendanceRequest(erp_students=sample_erp_roster, ai_records=uploaded_items)
        )

        assert len(result.results) == 2
        resolutions = [r.resolution for r in result.results]
        assert ResolutionState.NEEDS_REVIEW in resolutions
        assert any(r.is_duplicate for r in result.results)

        dup_exceptions = [e for e in result.exceptions if "CONFLICTING" in e.type or "DUPLICATE" in e.type]
        assert len(dup_exceptions) >= 1
        assert "Aarav Sharma" in dup_exceptions[0].message


class TestEndToEndPipeline:
    """End-to-end tests validating OCR extraction through ERP matching."""

    def test_9_e2e_real_image_pipeline(self, sample_erp_roster):
        """
        Test 9: End-to-end test with synthetic attendance register image.
        Renders 5 students with continuous and absent marks, extracts via EasyOCR,
        normalizes marks, and matches against ERP roster.
        """
        width, height = 900, 600
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        try:
            font_header = ImageFont.truetype("arial.ttf", 20)
            font_body = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font_header = ImageFont.load_default()
            font_body = ImageFont.load_default()

        # Header
        draw.text((40, 92), "ROLL NO", fill=(15, 23, 42), font=font_header)
        draw.text((250, 92), "STUDENT NAME", fill=(15, 23, 42), font=font_header)
        draw.text((600, 92), "ATTENDANCE", fill=(15, 23, 42), font=font_header)

        # Rows
        sheet_data = [
            ("001", "Aarav Sharma", "17"),
            ("002", "Rahul Kumar", "A"),
            ("003", "Priya Singh", "18"),
            ("004", "Diya Patel", "19"),
            ("005", "Sneha Rao", "A"),
        ]

        for i, (roll, name, mark) in enumerate(sheet_data):
            y = 135 + i * 55
            draw.text((40, y + 14), roll, fill=(51, 65, 85), font=font_body)
            draw.text((250, y + 14), name, fill=(15, 23, 42), font=font_body)
            draw.text((600, y + 14), mark, fill=(15, 23, 42), font=font_body)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        # 1. OCR Extraction
        provider = EasyOCRVisionProvider()
        extracted_items = provider.extract_attendance(img, image_bytes, "register_test.png")

        assert len(extracted_items) == 5, f"Expected 5 items extracted, got {len(extracted_items)}"

        # Check raw marks and statuses
        expected_statuses = {
            "Aarav Sharma": (AttendanceStatus.PRESENT, "17"),
            "Rahul Kumar": (AttendanceStatus.ABSENT, "A"),
            "Priya Singh": (AttendanceStatus.PRESENT, "18"),
            "Diya Patel": (AttendanceStatus.PRESENT, "19"),
            "Sneha Rao": (AttendanceStatus.ABSENT, "A"),
        }

        for item in extracted_items:
            assert item.raw_name in expected_statuses
            exp_status, exp_mark = expected_statuses[item.raw_name]
            assert item.status == exp_status
            assert item.raw_attendance_mark == exp_mark

        # 2. ERP Matching
        service = StudentMatchingService()
        matching_result = service.match_attendance(
            MatchAttendanceRequest(erp_students=sample_erp_roster, ai_records=extracted_items)
        )

        assert matching_result.summary.total_ai_records == 5
        assert matching_result.summary.unmatched == 0
        assert matching_result.summary.matched + matching_result.summary.needs_review == 5

        # Verify all matched items preserve raw_attendance_mark
        for m_item in matching_result.results:
            assert m_item.raw_attendance_mark is not None
            assert m_item.matched_name in expected_statuses

    def test_10_api_match_attendance_preserves_raw_mark(self, sample_erp_roster):
        """
        Test 10: API Endpoint POST /api/v1/attendance/match.
        Verifies that the API response includes raw_attendance_mark for all items.
        """
        client = TestClient(app)
        payload = {
            "erp_students": [s.model_dump() for s in sample_erp_roster],
            "ai_records": [
                {
                    "raw_identifier": "001",
                    "raw_name": "Aarav Sharma",
                    "raw_attendance_mark": "1",
                    "status": "PRESENT",
                    "confidence": 0.95,
                },
                {
                    "raw_identifier": "002",
                    "raw_name": "Rahul Kumar",
                    "raw_attendance_mark": "A",
                    "status": "ABSENT",
                    "confidence": 0.90,
                },
            ],
        }

        response = client.post("/api/v1/attendance/match", json=payload)
        assert response.status_code == 200
        data = response.json()

        results = data["results"]
        assert len(results) == 2
        assert results[0]["raw_attendance_mark"] == "1"
        assert results[0]["status"] == "PRESENT"
        assert results[1]["raw_attendance_mark"] == "A"
        assert results[1]["status"] == "ABSENT"
