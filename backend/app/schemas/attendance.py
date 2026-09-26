"""
Attendance schemas for AI Attendance Assistant.
Defines structured requests, responses, and status enums.
"""

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, val: Any) -> "AttendanceStatus":
        """Normalize any string/enum to one of the 4 strict attendance statuses."""
        if isinstance(val, cls):
            return val
        if hasattr(val, "value"):
            val = val.value
        if not val:
            return cls.UNKNOWN
        clean = str(val).strip().upper()
        if clean in ("P", "PRESENT", "PRES", "ATTENDED") or clean.endswith(".PRESENT"):
            return cls.PRESENT
        if clean in ("A", "ABSENT", "ABS", "LEAVE") or clean.endswith(".ABSENT"):
            return cls.ABSENT
        if clean in ("L", "LATE", "TARDY") or clean.endswith(".LATE"):
            return cls.LATE
        return cls.UNKNOWN


class AttendanceItem(BaseModel):
    raw_name: Optional[str] = Field(default=None, description="Extracted raw student name")
    raw_identifier: Optional[str] = Field(default=None, description="Extracted roll number or student ID")
    status: AttendanceStatus = Field(description="Strict attendance status: PRESENT, ABSENT, LATE, or UNKNOWN")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(float(v), 2)


class AttendanceSummary(BaseModel):
    total_detected: int = Field(default=0, ge=0)
    present: int = Field(default=0, ge=0)
    absent: int = Field(default=0, ge=0)
    late: int = Field(default=0, ge=0)
    unknown: int = Field(default=0, ge=0)

    @classmethod
    def compute(cls, items: List[AttendanceItem]) -> "AttendanceSummary":
        present = sum(1 for it in items if it.status == AttendanceStatus.PRESENT)
        absent = sum(1 for it in items if it.status == AttendanceStatus.ABSENT)
        late = sum(1 for it in items if it.status == AttendanceStatus.LATE)
        unknown = sum(1 for it in items if it.status == AttendanceStatus.UNKNOWN)
        return cls(
            total_detected=len(items),
            present=present,
            absent=absent,
            late=late,
            unknown=unknown,
        )


class AttendanceProcessResponse(BaseModel):
    success: bool = True
    attendance: List[AttendanceItem] = Field(default_factory=list)
    summary: AttendanceSummary


class ApiErrorDetail(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiErrorDetail
