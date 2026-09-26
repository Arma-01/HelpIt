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
            assert item["status"] in ["PRESENT", "ABSENT", "LATE", "UNKNOWN"]
            assert 0.0 <= item["confidence"] <= 1.0
            assert "raw_name" in item
            assert "raw_identifier" in item

        # Validate summary
        summary = data["summary"]
        assert summary["total_detected"] == len(data["attendance"])
        assert summary["total_detected"] == (
            summary["present"] + summary["absent"] + summary["late"] + summary["unknown"]
        )

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

    def test_6_unknown_status_preservation(self):
        """Test 6: Safety rule - UNKNOWN must NEVER be converted to ABSENT."""
        # 1. Direct from_str normalization check
        assert AttendanceStatus.from_str("UNKNOWN") == AttendanceStatus.UNKNOWN
        assert AttendanceStatus.from_str("?") == AttendanceStatus.UNKNOWN
        assert AttendanceStatus.from_str("ambiguous") == AttendanceStatus.UNKNOWN
        assert AttendanceStatus.from_str("unclear") == AttendanceStatus.UNKNOWN
        assert AttendanceStatus.from_str("") == AttendanceStatus.UNKNOWN
        assert AttendanceStatus.from_str(None) == AttendanceStatus.UNKNOWN

        # 2. Pipeline processing check with an uncertain row
        service = AttendanceService()
        mock_provider = MagicMock()
        mock_provider.extract_attendance.return_value = [
            AttendanceItem(raw_identifier="021", raw_name="John Doe", status=AttendanceStatus.UNKNOWN, confidence=0.45)
        ]
        service._provider = mock_provider

        # Create dummy valid image bytes
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(buf, format="JPEG")
        
        result = service.process_image(buf.getvalue(), "test.jpg", "image/jpeg")
        assert result.attendance[0].status == AttendanceStatus.UNKNOWN
        assert result.attendance[0].status != AttendanceStatus.ABSENT
        assert result.summary.unknown == 1
        assert result.summary.absent == 0
