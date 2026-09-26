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

- UNKNOWN never becomes ABSENT automatically
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