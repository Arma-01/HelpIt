"""
Unit and integration tests for Phase 2: Student Matching, Confidence & Exception Engine.
Validates all deterministic matching priorities, ambiguous states, duplicates, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.attendance import AttendanceItem, AttendanceStatus
from app.schemas.student import (
    StudentInfo,
    MatchAttendanceRequest,
    MatchMethod,
    ResolutionState,
)
from app.services.matching_service import StudentMatchingService, matching_service


@pytest.fixture
def mock_erp_roster() -> list[StudentInfo]:
    """Standard 60-student demo roster based on Mock ERP data."""
    students = [
        StudentInfo(student_id="STU001", roll_number="001", name="Aarav Sharma"),
        StudentInfo(student_id="STU002", roll_number="002", name="Aarav Verma"),
        StudentInfo(student_id="STU003", roll_number="003", name="Rahul Kumar"),
        StudentInfo(student_id="STU004", roll_number="004", name="Rahul Singh"),
        StudentInfo(student_id="STU005", roll_number="005", name="Priya Singh"),
        StudentInfo(student_id="STU006", roll_number="006", name="Priya Sharma"),
        StudentInfo(student_id="STU007", roll_number="007", name="Ankit Kumar"),
        StudentInfo(student_id="STU008", roll_number="008", name="Ankit Sharma"),
        StudentInfo(student_id="STU009", roll_number="009", name="Aman Kumar"),
        StudentInfo(student_id="STU010", roll_number="010", name="Aman Sharma"),
        StudentInfo(student_id="STU011", roll_number="011", name="Sneha Patel"),
        StudentInfo(student_id="STU012", roll_number="012", name="Sneha Gupta"),
        StudentInfo(student_id="STU013", roll_number="013", name="Rohan Verma"),
        StudentInfo(student_id="STU014", roll_number="014", name="Rohan Sharma"),
        StudentInfo(student_id="STU015", roll_number="015", name="Neha Gupta"),
        StudentInfo(student_id="STU016", roll_number="016", name="Neha Sharma"),
    ]
    # Add rest to total 60 students for realistic tests
    for i in range(17, 61):
        num_str = f"{i:03d}"
        students.append(
            StudentInfo(
                student_id=f"STU{num_str}",
                roll_number=num_str,
                name=f"Student {num_str}",
            )
        )
    return students


class TestStudentMatchingEngine:
    """Test suite covering the core matching logic, priority order, and exception rules."""

    def test_1_student_id_matching(self, mock_erp_roster):
        """Test 1: Student ID Match (STU001) should match reliably with 1.0 confidence."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(
                raw_name="Aarav Sharma",
                raw_identifier="STU001",
                status=AttendanceStatus.PRESENT,
                confidence=0.98,
            )
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        assert response.summary.matched == 1
        assert response.summary.needs_review == 0
        assert response.summary.unmatched == 0

        res = response.results[0]
        assert res.resolution == ResolutionState.MATCHED
        assert res.matched_student_id == "STU001"
        assert res.matched_name == "Aarav Sharma"
        assert res.match_method == MatchMethod.STUDENT_ID
        assert res.match_confidence == 1.00
        assert res.ai_confidence == 0.98

    def test_2_roll_number_matching(self, mock_erp_roster):
        """Test 2: Roll Number Match (e.g. '002' or 'Roll 002') when ID is absent."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(
                raw_name=None,
                raw_identifier="Roll 002",
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            )
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        assert response.summary.matched == 1
        res = response.results[0]
        assert res.resolution == ResolutionState.MATCHED
        assert res.matched_student_id == "STU002"
        assert res.matched_roll_number == "002"
        assert res.matched_name == "Aarav Verma"
        assert res.match_method == MatchMethod.ROLL_NUMBER
        assert res.match_confidence == 0.98

    def test_3_exact_name_matching(self, mock_erp_roster):
        """Test 3: Exact Name Match when no identifier is present and name is unique."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(
                raw_name="Priya Singh",
                raw_identifier=None,
                status=AttendanceStatus.ABSENT,
                confidence=0.94,
            )
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        assert response.summary.matched == 1
        res = response.results[0]
        assert res.resolution == ResolutionState.MATCHED
        assert res.matched_student_id == "STU005"
        assert res.matched_name == "Priya Singh"
        assert res.match_method == MatchMethod.EXACT_NAME
        assert res.match_confidence == 0.95

    def test_4_duplicate_erp_names_ambiguity(self):
        """Test 4: Ambiguous Match when multiple ERP students have the exact same name."""
        service = StudentMatchingService()
        erp_students = [
            StudentInfo(student_id="STU021", roll_number="021", name="Rahul Kumar"),
            StudentInfo(student_id="STU043", roll_number="043", name="Rahul Kumar"),
        ]
        ai_records = [
            AttendanceItem(
                raw_name="Rahul Kumar",
                raw_identifier=None,
                status=AttendanceStatus.PRESENT,
                confidence=0.91,
            )
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=erp_students, ai_records=ai_records)
        )

        assert response.summary.matched == 0
        assert response.summary.needs_review == 1

        res = response.results[0]
        assert res.resolution == ResolutionState.NEEDS_REVIEW
        assert res.match_method == MatchMethod.EXACT_NAME
        assert len(res.candidates) == 2
        candidate_ids = {c.student_id for c in res.candidates}
        assert candidate_ids == {"STU021", "STU043"}

    def test_5_fuzzy_typo_matching(self, mock_erp_roster):
        """Test 5: Typo in name (Rahul Kumr -> Rahul Kumar) matches via fuzzy matching."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(
                raw_name="Rahul Kumr",
                raw_identifier=None,
                status=AttendanceStatus.PRESENT,
                confidence=0.90,
            )
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        res = response.results[0]
        assert res.match_method == MatchMethod.FUZZY_NAME
        # Rahul Kumr should identify Rahul Kumar as the top candidate
        assert res.matched_name == "Rahul Kumar" or (res.candidates and res.candidates[0].name == "Rahul Kumar")
        assert res.resolution in (ResolutionState.MATCHED, ResolutionState.NEEDS_REVIEW)
        assert res.match_confidence > 0.0

    def test_6_unknown_student_unmatched(self, mock_erp_roster):
        """Test 6: Student not present in ERP roster returns UNMATCHED with null student ID."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(
                raw_name="Suresh Patel",
                raw_identifier=None,
                status=AttendanceStatus.PRESENT,
                confidence=0.88,
            )
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        assert response.summary.matched == 0
        assert response.summary.unmatched == 1
        res = response.results[0]
        assert res.resolution == ResolutionState.UNMATCHED
        assert res.matched_student_id is None
        assert res.match_confidence == 0.0

    def test_7_missing_ai_records_not_marked_absent(self, mock_erp_roster):
        """
        Test 7: Missing ERP students are placed into erp_students_not_detected.
        CRITICAL: Never automatically marked as ABSENT!
        """
        service = StudentMatchingService()
        # ERP has 60 students; AI detects only 58 (excluding STU015 and STU016)
        ai_records = [
            AttendanceItem(
                raw_name=s.name,
                raw_identifier=s.student_id,
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            )
            for s in mock_erp_roster
            if s.student_id not in ("STU015", "STU016")
        ]

        assert len(ai_records) == 58

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        assert response.summary.total_ai_records == 58
        assert response.summary.matched == 58
        assert response.summary.missing_erp_students_count == 2

        missing_ids = [s.student_id for s in response.erp_students_not_detected]
        assert "STU015" in missing_ids
        assert "STU016" in missing_ids

        # Ensure no status was modified or auto-converted to ABSENT
        for student in response.erp_students_not_detected:
            assert student.status != "ABSENT"

    def test_8_duplicate_ai_record_detected(self, mock_erp_roster):
        """Test 8: Duplicate AI detection for same student creates DUPLICATE_DETECTED exception."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(
                raw_name="Aarav Sharma",
                raw_identifier="STU001",
                status=AttendanceStatus.PRESENT,
                confidence=0.96,
            ),
            AttendanceItem(
                raw_name="Aarav Sharma",
                raw_identifier="STU001",
                status=AttendanceStatus.PRESENT,
                confidence=0.92,
            ),
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        assert response.summary.matched == 1
        assert response.summary.needs_review == 1
        assert response.summary.duplicates == 1

        first_res = response.results[0]
        second_res = response.results[1]

        assert first_res.resolution == ResolutionState.MATCHED
        assert not first_res.is_duplicate

        assert second_res.resolution == ResolutionState.NEEDS_REVIEW
        assert second_res.is_duplicate is True
        assert "Duplicate AI record" in (second_res.review_reason or "")

        dup_exceptions = [e for e in response.exceptions if e.type == "DUPLICATE_DETECTED"]
        assert len(dup_exceptions) >= 1

    def test_9_name_normalization(self, mock_erp_roster):
        """Test 9: Case and whitespace normalization matches successfully."""
        service = StudentMatchingService()
        test_cases = [
            "  aarav sharma  ",
            "AARAV SHARMA",
            "Aarav    Sharma",
            "aarav   sharma.",
        ]

        for raw in test_cases:
            ai_records = [
                AttendanceItem(
                    raw_name=raw,
                    raw_identifier=None,
                    status=AttendanceStatus.PRESENT,
                    confidence=0.90,
                )
            ]
            response = service.match_attendance(
                MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
            )
            assert response.summary.matched == 1
            res = response.results[0]
            assert res.matched_student_id == "STU001"
            assert res.match_method in (MatchMethod.EXACT_NAME, MatchMethod.NORMALIZED_NAME)

    def test_10_identifier_priority_over_conflicting_name(self, mock_erp_roster):
        """Test 10: Unique identifier takes priority over any name discrepancy."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(
                raw_name="Completely Wrong Name",
                raw_identifier="STU001",
                status=AttendanceStatus.PRESENT,
                confidence=0.95,
            )
        ]

        response = service.match_attendance(
            MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        )

        assert response.summary.matched == 1
        res = response.results[0]
        assert res.matched_student_id == "STU001"
        assert res.matched_name == "Aarav Sharma"
        assert res.match_method == MatchMethod.STUDENT_ID
        assert res.match_confidence == 1.00

    def test_11_deterministic_output(self, mock_erp_roster):
        """Test 11: Engine produces identical output across multiple runs with same input."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Aarav Sharma", raw_identifier="STU001", status=AttendanceStatus.PRESENT, confidence=0.9),
            AttendanceItem(raw_name="Rahul Kumr", raw_identifier=None, status=AttendanceStatus.PRESENT, confidence=0.85),
            AttendanceItem(raw_name="Unknown Person", raw_identifier=None, status=AttendanceStatus.ABSENT, confidence=0.8),
        ]

        req = MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records)
        run1 = service.match_attendance(req).model_dump()
        run2 = service.match_attendance(req).model_dump()

        assert run1 == run2


class TestMatchingApiEndpoint:
    """Test suite for POST /api/v1/attendance/match."""

    def test_post_match_endpoint_success(self, client: TestClient, mock_erp_roster):
        payload = {
            "erp_students": [s.model_dump() for s in mock_erp_roster[:5]],
            "ai_records": [
                {
                    "raw_name": "Aarav Sharma",
                    "raw_identifier": "STU001",
                    "status": "PRESENT",
                    "confidence": 0.98,
                },
                {
                    "raw_name": "Unknown",
                    "raw_identifier": None,
                    "status": "ABSENT",
                    "confidence": 0.90,
                },
            ],
        }

        response = client.post("/api/v1/attendance/match", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["summary"]["total_ai_records"] == 2
        assert data["summary"]["matched"] == 1
        assert data["summary"]["unmatched"] == 1
        assert len(data["results"]) == 2
        assert len(data["erp_students_not_detected"]) == 4  # 5 ERP students minus 1 matched


class TestPhase21PhysicalSheetStatusIntegrity:
    """
    Test suite for Phase 2.1:
    Verifies that attendance status strictly reflects the physical sheet mark,
    is never altered by student matching, supports only PRESENT/ABSENT,
    preserves row alignment, and safely handles low-confidence / conflicting cases.
    """

    def test_p21_1_present_mark_preserved(self, mock_erp_roster):
        """Test 1: Physical sheet PRESENT mark yields PRESENT."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Aarav Sharma", raw_identifier="001", status=AttendanceStatus.PRESENT, confidence=0.98)
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        assert res.results[0].status == AttendanceStatus.PRESENT
        assert res.results[0].resolution == ResolutionState.MATCHED

    def test_p21_2_absent_mark_preserved(self, mock_erp_roster):
        """Test 2: Physical sheet ABSENT mark yields ABSENT."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Rahul Kumar", raw_identifier="003", status=AttendanceStatus.ABSENT, confidence=0.95)
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        assert res.results[0].status == AttendanceStatus.ABSENT
        assert res.results[0].resolution == ResolutionState.MATCHED

    def test_p21_3_mixed_class_sequence_preserved(self, mock_erp_roster):
        """Test 3: Mixed class sequence (P, A, P, A) strictly matches input order."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Aarav Sharma", raw_identifier="001", status=AttendanceStatus.PRESENT, confidence=0.95),
            AttendanceItem(raw_name="Aarav Verma", raw_identifier="002", status=AttendanceStatus.ABSENT, confidence=0.95),
            AttendanceItem(raw_name="Rahul Kumar", raw_identifier="003", status=AttendanceStatus.PRESENT, confidence=0.95),
            AttendanceItem(raw_name="Rahul Singh", raw_identifier="004", status=AttendanceStatus.ABSENT, confidence=0.95),
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        statuses = [r.status for r in res.results]
        assert statuses == [
            AttendanceStatus.PRESENT,
            AttendanceStatus.ABSENT,
            AttendanceStatus.PRESENT,
            AttendanceStatus.ABSENT,
        ]

    def test_p21_4_adjacent_rows_no_status_inversion(self, mock_erp_roster):
        """Test 4: Adjacent rows Student A (P) and Student B (A) never invert statuses."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Priya Singh", raw_identifier="005", status=AttendanceStatus.PRESENT, confidence=0.94),
            AttendanceItem(raw_name="Priya Sharma", raw_identifier="006", status=AttendanceStatus.ABSENT, confidence=0.94),
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        assert res.results[0].matched_student_id == "STU005"
        assert res.results[0].status == AttendanceStatus.PRESENT
        assert res.results[1].matched_student_id == "STU006"
        assert res.results[1].status == AttendanceStatus.ABSENT

    def test_p21_5_similar_names_retain_own_row_status(self, mock_erp_roster):
        """Test 5: Students with similar names (Aman Kumar vs Aman Sharma) retain their own row status."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Aman Kumar", raw_identifier="009", status=AttendanceStatus.PRESENT, confidence=0.92),
            AttendanceItem(raw_name="Aman Sharma", raw_identifier="010", status=AttendanceStatus.ABSENT, confidence=0.92),
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        aman_k = next(r for r in res.results if r.matched_student_id == "STU009")
        aman_s = next(r for r in res.results if r.matched_student_id == "STU010")
        assert aman_k.status == AttendanceStatus.PRESENT
        assert aman_s.status == AttendanceStatus.ABSENT

    def test_p21_6_roll_number_matching_preserves_status(self, mock_erp_roster):
        """Test 6: Matching by roll number does NOT alter detected attendance status."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name=None, raw_identifier="007", status=AttendanceStatus.ABSENT, confidence=0.96)
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        assert res.results[0].matched_student_id == "STU007"
        assert res.results[0].status == AttendanceStatus.ABSENT
        assert res.results[0].match_method == MatchMethod.ROLL_NUMBER

    def test_p21_7_low_confidence_mark_triggers_review(self, mock_erp_roster):
        """Test 7: Unclear mark with low AI confidence (0.45) triggers review without inventing 3rd status."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Aarav Sharma", raw_identifier="STU001", status=AttendanceStatus.ABSENT, confidence=0.45)
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        # Status remains ABSENT (strictly in vocabulary)
        assert res.results[0].status == AttendanceStatus.ABSENT
        # But resolution is forced to NEEDS_REVIEW
        assert res.results[0].resolution == ResolutionState.NEEDS_REVIEW
        assert "Unclear physical attendance mark" in res.results[0].review_reason
        unclear_exc = [e for e in res.exceptions if e.type == "UNCLEAR_ATTENDANCE_MARK"]
        assert len(unclear_exc) == 1

    def test_p21_8_missing_student_never_marked_absent(self, mock_erp_roster):
        """Test 8: Missing ERP student is never automatically marked absent."""
        service = StudentMatchingService()
        # Only 1 student detected out of 60
        ai_records = [
            AttendanceItem(raw_name="Aarav Sharma", raw_identifier="STU001", status=AttendanceStatus.PRESENT, confidence=0.98)
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        assert len(res.erp_students_not_detected) == 59
        for stu in res.erp_students_not_detected:
            # None of the missing students are marked ABSENT
            assert stu.status != "ABSENT"

    def test_p21_9_conflicting_duplicate_detected(self, mock_erp_roster):
        """Test 9: Conflicting duplicate records (PRESENT vs ABSENT) trigger review."""
        service = StudentMatchingService()
        ai_records = [
            AttendanceItem(raw_name="Aarav Sharma", raw_identifier="STU001", status=AttendanceStatus.PRESENT, confidence=0.95),
            AttendanceItem(raw_name="Aarav Sharma", raw_identifier="STU001", status=AttendanceStatus.ABSENT, confidence=0.95),
        ]
        res = service.match_attendance(MatchAttendanceRequest(erp_students=mock_erp_roster, ai_records=ai_records))
        assert res.results[1].is_duplicate is True
        assert res.results[1].resolution == ResolutionState.NEEDS_REVIEW
        assert "Conflicting attendance records detected" in res.results[1].review_reason
        conflict_exc = [e for e in res.exceptions if e.type == "CONFLICTING_ATTENDANCE_DETECTED"]
        assert len(conflict_exc) == 1

