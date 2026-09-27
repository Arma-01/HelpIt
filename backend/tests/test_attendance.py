"""
Comprehensive test suite for AI Attendance Processing API and Pipeline.
Validates all requirements specified for Phase 1.
"""

import io
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.schemas.attendance import AttendanceStatus, AttendanceItem
from app.services.attendance_service import AttendanceService
from app.core.exceptions import NoAttendanceDetectedError, MalformedAIResponseError


class TestAttendanceEndpoint:
    """End-to-end tests for POST /api/v1/attendance/process endpoint."""

    def test_1_valid_image(self, client: TestClient, valid_demo_image_bytes: bytes):
        """Test 1: Valid image returns 200 OK and structured attendance response."""
        files = {
            "file": ("attendance_mock.jpg", valid_demo_image_bytes, "image/jpeg"),
        }
        response = client.post("/api/v1/attendance/process", files=files)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["success"] is True
        assert "attendance" in data
        assert isinstance(data["attendance"], list)
        assert len(data["attendance"]) > 0

        # Validate item structure
        for item in data["attendance"]:
            assert "status" in item
            assert item["status"] in ["PRESENT", "ABSENT"]
            assert 0.0 <= item["confidence"] <= 1.0
            assert "raw_name" in item
            assert "raw_identifier" in item

        # Validate summary: strictly PRESENT and ABSENT
        summary = data["summary"]
        assert summary["total_detected"] == len(data["attendance"])
        assert summary["total_detected"] == (summary["present"] + summary["absent"])
        assert "late" not in summary
        assert "unknown" not in summary

    def test_2_invalid_file(self, client: TestClient, corrupted_image_bytes: bytes):
        """Test 2: Invalid/corrupt file returns 4xx error with structured code."""
        files = {
            "file": ("fake_image.png", corrupted_image_bytes, "image/png"),
        }
        response = client.post("/api/v1/attendance/process", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_IMAGE"
        assert "valid attendance image" in data["error"]["message"].lower() or "invalid" in data["error"]["message"].lower()

    def test_2b_disallowed_extension(self, client: TestClient):
        """Test 2b: Text file or disallowed MIME returns 400 error."""
        files = {
            "file": ("document.txt", b"Hello World", "text/plain"),
        }
        response = client.post("/api/v1/attendance/process", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_IMAGE"

    def test_3_oversized_file(self, client: TestClient):
        """Test 3: Oversized file returns 413 error."""
        # 11 MB of dummy bytes
        large_bytes = b"0" * (11 * 1024 * 1024)
        files = {
            "file": ("large_image.jpg", large_bytes, "image/jpeg"),
        }
        response = client.post("/api/v1/attendance/process", files=files)
        assert response.status_code == 413
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "FILE_TOO_LARGE"

    def test_4_no_attendance_detected(self, client: TestClient, blank_image_bytes: bytes):
        """Test 4: Blank image with no text returns clear structured error."""
        files = {
            "file": ("blank_sheet.png", blank_image_bytes, "image/png"),
        }
        response = client.post("/api/v1/attendance/process", files=files)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "NO_ATTENDANCE_DETECTED"
        assert "no attendance" in data["error"]["message"].lower()

    def test_5_malformed_ai_output(self, client: TestClient, valid_demo_image_bytes: bytes):
        """Test 5: Backend handles malformed AI exceptions safely."""
        from app.services.attendance_service import attendance_service
        mock_provider = MagicMock()
        mock_provider.extract_attendance.side_effect = Exception("Simulated Vision Model Crash")

        original_provider = attendance_service._provider
        attendance_service.provider = mock_provider
        try:
            files = {
                "file": ("test.jpg", valid_demo_image_bytes, "image/jpeg"),
            }
            response = client.post("/api/v1/attendance/process", files=files)
            assert response.status_code in (500, 502)
            data = response.json()
            assert data["success"] is False
            assert "error" in data
        finally:
            attendance_service.provider = original_provider

    def test_6_strict_present_absent_vocabulary(self):
        """Test 6: Strict PRESENT/ABSENT normalization and rejection of invalid statuses."""
        # Present normalization
        assert AttendanceStatus.from_str("P") == AttendanceStatus.PRESENT
        assert AttendanceStatus.from_str("Present") == AttendanceStatus.PRESENT
        assert AttendanceStatus.from_str("✓") == AttendanceStatus.PRESENT
        assert AttendanceStatus.from_str("v") == AttendanceStatus.PRESENT
        assert AttendanceStatus.from_str("1") == AttendanceStatus.PRESENT

        # Absent normalization
        assert AttendanceStatus.from_str("A") == AttendanceStatus.ABSENT
        assert AttendanceStatus.from_str("Absent") == AttendanceStatus.ABSENT
        assert AttendanceStatus.from_str("✗") == AttendanceStatus.ABSENT
        assert AttendanceStatus.from_str("X") == AttendanceStatus.ABSENT
        assert AttendanceStatus.from_str("0") == AttendanceStatus.ABSENT

        # Unrecognized marks must raise ValueError
        import pytest
        with pytest.raises(ValueError):
            AttendanceStatus.from_str("LATE")
        with pytest.raises(ValueError):
            AttendanceStatus.from_str("UNKNOWN")
        with pytest.raises(ValueError):
            AttendanceStatus.from_str("MAYBE_PRESENT")
