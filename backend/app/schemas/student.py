"""
Student and Matching Schemas for AI Attendance Assistant - Phase 2.
Defines data structures for ERP students, matching criteria, resolutions, and exceptions.
"""

from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.attendance import AttendanceItem, AttendanceStatus


class MatchMethod(str, Enum):
    STUDENT_ID = "STUDENT_ID"
    ROLL_NUMBER = "ROLL_NUMBER"
    ENROLLMENT_NUMBER = "ENROLLMENT_NUMBER"
    EXACT_NAME = "EXACT_NAME"
    NORMALIZED_NAME = "NORMALIZED_NAME"
    FUZZY_NAME = "FUZZY_NAME"
    NONE = "NONE"


class ResolutionState(str, Enum):
    MATCHED = "MATCHED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNMATCHED = "UNMATCHED"


class StudentInfo(BaseModel):
    """
    Representation of a student record from the ERP.
    Supports both snake_case and camelCase field aliases for seamless integration.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    student_id: str = Field(..., alias="studentId", description="Unique student identifier (e.g. STU001)")
    roll_number: Optional[str] = Field(default=None, alias="rollNumber", description="Roll number (e.g. 001)")
    name: str = Field(..., description="Full student name (e.g. Aarav Sharma)")
    enrollment_number: Optional[str] = Field(default=None, alias="enrollmentNumber", description="Official enrollment number if available")
    email: Optional[str] = Field(default=None, description="Student email address")
    gender: Optional[str] = Field(default=None, description="Gender")
    status: Optional[str] = Field(default=None, description="Current ERP attendance status")
    remarks: Optional[str] = Field(default=None, description="Remarks")


class MatchCandidate(BaseModel):
    """Candidate student for ambiguous or fuzzy matches requiring review."""
    student_id: str
    roll_number: Optional[str] = None
    name: str
    similarity: Optional[float] = None
    reason: Optional[str] = None


class MatchingResultItem(BaseModel):
    """
    Structured outcome of matching an individual AI attendance record to an ERP student.
    Maintains complete separation between AI confidence and Match confidence.
    """
    raw_name: Optional[str] = Field(default=None, description="Extracted raw student name from AI")
    raw_identifier: Optional[str] = Field(default=None, description="Extracted roll number or student ID from AI")
    raw_student_id: Optional[str] = Field(default=None, description="Extracted raw student ID from AI")
    raw_attendance_mark: Optional[str] = Field(default=None, description="Extracted raw attendance mark from AI (e.g. '17', 'A', 'P')")
    status: AttendanceStatus = Field(description="Strict attendance status: PRESENT or ABSENT")

    # Separate Confidences
    ai_confidence: float = Field(..., description="Vision/OCR interpretation confidence score (0.0 to 1.0)")
    match_confidence: float = Field(..., description="Student matching confidence score (0.0 to 1.0)")

    # ERP Matched Record Details
    matched_student_id: Optional[str] = Field(default=None, description="Matched ERP Student ID or null")
    matched_roll_number: Optional[str] = Field(default=None, description="Matched ERP Roll Number or null")
    matched_name: Optional[str] = Field(default=None, description="Matched ERP Student Name or null")

    match_method: MatchMethod = Field(default=MatchMethod.NONE, description="Method utilized to determine match")
    resolution: ResolutionState = Field(..., description="MATCHED, NEEDS_REVIEW, or UNMATCHED")

    review_reason: Optional[str] = Field(default=None, description="Explanation for NEEDS_REVIEW or UNMATCHED")
    candidates: List[MatchCandidate] = Field(default_factory=list, description="Candidate students when resolution is NEEDS_REVIEW")
    is_duplicate: bool = Field(default=False, description="Flagged true if this student ID appeared multiple times in AI records")


class MatchingSummary(BaseModel):
    """Overall tally and breakdown of the matching operation."""
    total_ai_records: int = Field(default=0, ge=0)
    matched: int = Field(default=0, ge=0)
    needs_review: int = Field(default=0, ge=0)
    unmatched: int = Field(default=0, ge=0)
    duplicates: int = Field(default=0, ge=0)
    total_erp_students: int = Field(default=0, ge=0)
    missing_erp_students_count: int = Field(default=0, ge=0)


class MatchAttendanceRequest(BaseModel):
    """Request payload containing ERP students and AI detected attendance."""
    model_config = ConfigDict(populate_by_name=True)

    erp_students: List[StudentInfo] = Field(..., description="List of student records currently in ERP class")
    ai_records: List[AttendanceItem] = Field(..., description="Structured AI attendance detection records from Phase 1")


class MatchingExceptionItem(BaseModel):
    """Record describing an exception encountered during matching."""
    type: str = Field(..., description="Exception category: DUPLICATE_DETECTED, AMBIGUOUS_MATCH, UNMATCHED_STUDENT, MISSING_ERP_STUDENT")
    student_id: Optional[str] = None
    name: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


class MatchAttendanceResponse(BaseModel):
    """Complete response returned by POST /api/v1/attendance/match."""
    success: bool = True
    results: List[MatchingResultItem] = Field(default_factory=list)
    summary: MatchingSummary
    erp_students_not_detected: List[StudentInfo] = Field(
        default_factory=list,
        description="ERP students not present in AI detection results (NOT automatically marked absent)"
    )
    exceptions: List[MatchingExceptionItem] = Field(default_factory=list)
