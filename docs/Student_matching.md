# Student Matching Engine

## Matching Priority

1. Student ID
2. Roll number
3. Enrollment number
4. Exact name
5. Normalized name
6. Fuzzy name

## Example

AI:

Roll = 23
Name = "Arman S"

ERP:

Roll = 23
Name = "Syed Sadiq Arman"

Result:

MATCH

Confidence = HIGH

## Never

Never match two students solely because their names
are similar when a unique identifier is available.

## Ambiguous Match

If two possible students exist:

status = NEEDS_REVIEW

Never automatically choose.