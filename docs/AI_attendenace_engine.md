# AI Attendance Engine

## Input

Attendance image.

## Output

Structured JSON.

Example:

{
  "students": [
    {
      "identifier": "23",
      "status": "absent",
      "confidence": 0.97
    }
  ]
}

## Processing Pipeline

Image
 ↓
Preprocessing
 ↓
OCR / Vision
 ↓
Table detection
 ↓
Student row extraction
 ↓
Attendance mark detection
 ↓
Structured output
 ↓
Validation

## Supported Statuses

The attendance system strictly supports ONLY TWO attendance statuses:
- PRESENT
- ABSENT

LATE and UNKNOWN have been completely removed from backend models, API responses, and UI.

## Rules

If an attendance mark cannot be confidently detected:

- The system assigns a best-effort status with LOW confidence (< 0.65).
- Low confidence triggers teacher review (NEEDS_REVIEW) rather than inventing a third status.
- Do not guess or silently reverse status.

## Confidence

0.90 - 1.00 = HIGH

0.70 - 0.89 = MEDIUM

Below 0.70 = LOW

LOW confidence marks (< 0.65) trigger teacher review.

## Important

AI must never invent a student.

Missing students must never be automatically marked ABSENT.