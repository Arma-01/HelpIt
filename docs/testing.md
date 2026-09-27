# Testing Strategy

## Unit Tests

Test:

- Student matching
- Name normalization
- Confidence calculation
- Attendance parsing

## Extension Tests

Test:

- ERP detection
- Student extraction
- Attendance field detection
- Attendance modification

## AI Tests

Test:

- Clear printed sheet
- Poor image
- Rotated image
- Handwritten marks
- Missing students
- Duplicate students
- Unclear attendance marks

## Safety Tests

Verify:

- Only PRESENT and ABSENT statuses are supported (no LATE or UNKNOWN)
- Low-confidence or unclear marks trigger review instead of inventing statuses
- Missing ERP students are never automatically marked ABSENT
- Wrong student cannot be silently selected
- Final ERP submit is never automatically triggered

## End-to-End Test

Image
 ↓
AI
 ↓
Student matching
 ↓
Teacher review
 ↓
ERP modification