"""
Centralized Attendance Normalization Engine.
Strictly normalizes physical sheet attendance marks into application statuses:
PRESENT or ABSENT.

Supports:
- Standard marks: P, Present, Pres, Attended, Yes, Y, 1, ✓, etc. -> PRESENT
- Absence marks: A, Absent, Abs, Leave, No, N, 0, -, X, ✗, etc. -> ABSENT
- Continuous numeric attendance counts: Any positive integer (e.g. 1, 2, 3, 12, 17, 18, 103) -> PRESENT
- Sequence-independent: counts do not need to start at 1 and do not need to be strictly contiguous.
- Column-aware validation: roll numbers or IDs must not be treated as attendance.
- Never invents a third status (LATE, UNKNOWN, etc. remain completely forbidden).
- Ambiguous marks return low confidence (< 0.65) to trigger teacher review.
"""

import re
from typing import Tuple, Optional, Any
from app.schemas.attendance import AttendanceStatus


# Standard present tokens (case-insensitive)
STANDARD_PRESENT_TOKENS = {
    "P", "PRESENT", "PRES", "PR", "ATTENDED", "YES", "Y", "TRUE", "V", "✓", "✔", "\\/"
}

# Standard absent tokens (case-insensitive)
STANDARD_ABSENT_TOKENS = {
    "A", "ABSENT", "ABS", "AB", "LEAVE", "NO", "N", "FALSE", "X", "✗", "✘", "-"
}


def is_valid_positive_number(val_str: str) -> bool:
    """
    Checks if a string represents a valid positive integer attendance count.
    Supports integers such as '1', '2', '17', '103'.
    Rejects negative numbers, zero, or non-numeric strings.
    """
    clean = val_str.strip()
    if clean.isdigit():
        num = int(clean)
        return num > 0
    return False


def normalize_attendance(
    raw_mark: Any,
    is_in_attendance_column: bool = True,
) -> Tuple[AttendanceStatus, float, str]:
    """
    Converts physical attendance marks into normalized AttendanceStatus and confidence.
    
    Returns:
        (status: AttendanceStatus, confidence: float, raw_mark_str: str)

    Rules:
    1. If mark indicates absence ('A', 'ABSENT', 'ABS', 'LEAVE', '0', 'X', '-'):
       -> ABSENT (high confidence 0.95 - 0.99)
    2. If mark indicates standard presence ('P', 'PRESENT', 'YES', '✓', '1'):
       -> PRESENT (high confidence 0.95 - 0.99)
    3. If mark is a valid positive integer in the attendance column (e.g. '2', '3', '17', '103'):
       -> PRESENT (high confidence 0.96 - 0.98)
       Numeric counts represent cumulative present days in continuous attendance registers.
    4. Characters like '0' in attendance context indicate absent / 0 attendance count -> ABSENT.
    5. Ambiguous marks that cannot safely be categorized:
       -> ABSENT with LOW confidence (0.45), triggering teacher review (NEEDS_REVIEW)
       rather than inventing a third status.
    """
    if raw_mark is None:
        return AttendanceStatus.ABSENT, 0.40, ""

    raw_str = str(raw_mark).strip()
    if not raw_str:
        return AttendanceStatus.ABSENT, 0.40, ""

    # Upper case stripped string
    upper = raw_str.upper()

    # 1. Standard Absence check
    if upper in STANDARD_ABSENT_TOKENS or upper == "0":
        return AttendanceStatus.ABSENT, 0.98, raw_str

    # Clean alphanumeric / symbols for standard alphabetic presence
    clean_alpha = re.sub(r"[^A-Za-z✓✔✗✘]", "", upper)
    if clean_alpha in STANDARD_ABSENT_TOKENS:
        return AttendanceStatus.ABSENT, 0.96, raw_str

    # 2. Standard Presence check
    if upper in STANDARD_PRESENT_TOKENS:
        return AttendanceStatus.PRESENT, 0.98, raw_str

    if clean_alpha in STANDARD_PRESENT_TOKENS:
        return AttendanceStatus.PRESENT, 0.96, raw_str

    # 3. Numeric Attendance Count check (Continuous attendance system)
    # When located in the attendance column, positive integer numbers denote PRESENT.
    if is_in_attendance_column and is_valid_positive_number(raw_str):
        return AttendanceStatus.PRESENT, 0.97, raw_str

    # Check for number with trailing dot or punctuation (e.g. '17.' or '#17')
    m_num = re.match(r"^[#]?(\d+)[.]?$", raw_str)
    if is_in_attendance_column and m_num:
        val = int(m_num.group(1))
        if val > 0:
            return AttendanceStatus.PRESENT, 0.95, m_num.group(1)
        elif val == 0:
            return AttendanceStatus.ABSENT, 0.95, "0"

    # 4. OCR Ambiguity handling with table context
    # If in attendance column, handle common OCR handwritten confusions only with high care:
    # e.g. OCR might read 'I' or 'l' or '|' for '1'
    if is_in_attendance_column and upper in ("I", "L", "|", "/"):
        # Could be tick or number 1, but ambiguous: mark PRESENT with moderate-low confidence to trigger review
        return AttendanceStatus.PRESENT, 0.60, raw_str

    # OCR might read 'O' or 'D' for '0' (absent)
    if is_in_attendance_column and upper in ("O", "D"):
        return AttendanceStatus.ABSENT, 0.55, raw_str

    # 5. Unrecognized / Ambiguous mark
    # Default to ABSENT with low confidence so it triggers teacher review (NEEDS_REVIEW)
    # Never invent a third attendance status.
    return AttendanceStatus.ABSENT, 0.45, raw_str
