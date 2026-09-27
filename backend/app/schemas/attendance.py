"""
Attendance schemas for AI Attendance Assistant.
Defines structured requests, responses, and strict PRESENT/ABSENT status enum.
"""

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class AttendanceStatus(str, Enum):
    """
    Strict attendance status vocabulary.
    Only TWO statuses are supported in the entire system: PRESENT and ABSENT.
    LATE and UNKNOWN have been completely removed.
    """
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"

    @classmethod
    def from_str(cls, val: Any) -> "AttendanceStatus":
        """
        Normalize physical sheet mark or string to strictly PRESENT or ABSENT.
        Raises ValueError if unrecognized, so the pipeline can safely handle it
        via error / low-confidence review mechanisms.
        """
        if isinstance(val, cls):
            return val
        if hasattr(val, "value"):
            val = val.value
        if not val:
            raise ValueError("Attendance mark value cannot be empty.")
        clean = str(val).strip().upper()

        # Present indicators: P, PRESENT, PRES, ATTENDED, YES, Y, 1, checkmark ✓, tick
        if clean in ("P", "PRESENT", "PRES", "ATTENDED", "Y", "YES", "1", "TRUE", "V", "✓") or clean.endswith(".PRESENT"):
            return cls.PRESENT

        # Absent indicators: A, ABSENT, ABS, LEAVE, NO, N, 0, FALSE, cross ✗, X
        if clean in ("A", "ABSENT", "ABS", "LEAVE", "N", "NO", "0", "FALSE", "X", "✗", "-") or clean.endswith(".ABSENT"):
            return cls.ABSENT

        # Numeric attendance format: Any positive integer denotes PRESENT
        if clean.isdigit() and int(clean) > 0:
            return cls.PRESENT

        raise ValueError(f"Unsupported attendance status mark: '{val}'. Allowed statuses are PRESENT and ABSENT.")


class AttendanceItem(BaseModel):
    raw_name: Optional[str] = Field(default=None, description="Extracted raw student name")
    raw_identifier: Optional[str] = Field(default=None, description="Extracted roll number or student ID")
    raw_student_id: Optional[str] = Field(default=None, description="Extracted raw student ID if separate column")
    raw_attendance_mark: Optional[str] = Field(default=None, description="Original raw mark from attendance sheet (e.g. '17', 'A', 'P')")
    status: AttendanceStatus = Field(description="Strict attendance status: PRESENT or ABSENT")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(float(v), 2)

    @property
    def ai_confidence(self) -> float:
        return self.confidence


class AttendanceSummary(BaseModel):
    """Attendance tally supporting only PRESENT and ABSENT."""
    total_detected: int = Field(default=0, ge=0)
    present: int = Field(default=0, ge=0)
    absent: int = Field(default=0, ge=0)

    @classmethod
    def compute(cls, items: List[AttendanceItem]) -> "AttendanceSummary":
        present = sum(1 for it in items if it.status == AttendanceStatus.PRESENT)
        absent = sum(1 for it in items if it.status == AttendanceStatus.ABSENT)
        return cls(
            total_detected=len(items),
            present=present,
            absent=absent,
        )


class AttendanceProcessResponse(BaseModel):
    success: bool = True
    attendance: List[AttendanceItem] = Field(default_factory=list)
    records: List[AttendanceItem] = Field(default_factory=list, description="Schema-compliant alias for attendance records")
    summary: AttendanceSummary


class ApiErrorDetail(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiErrorDetail
