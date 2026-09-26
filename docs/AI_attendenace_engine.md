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

PRESENT
ABSENT
LATE
UNKNOWN

## Rules

If attendance mark cannot be confidently detected:

status = UNKNOWN

Do not guess.

## Confidence

0.90 - 1.00 = HIGH

0.70 - 0.89 = MEDIUM

Below 0.70 = LOW

LOW confidence requires teacher review.

## Important

AI must never invent a student.

AI must never silently convert UNKNOWN to ABSENT.