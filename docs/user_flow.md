# User Flow

## Main Flow

Teacher opens supported ERP.

↓

Extension detects attendance page.

↓

Extension shows "AI Attendance Assistant".

↓

Teacher clicks "Scan Attendance".

↓

Teacher uploads image.

↓

Image is sent to backend.

↓

AI extracts attendance.

↓

System matches students.

↓

System calculates confidence.

↓

Extension displays results.

↓

Teacher reviews uncertain results.

↓

Teacher clicks "Apply Attendance".

↓

Extension updates ERP fields.

↓

Teacher reviews ERP.

↓

Teacher manually clicks ERP Submit.

↓

Attendance completed.

## Error Flow

If ERP is unsupported:

Show:
"This ERP is not currently supported."

If image cannot be processed:

Show:
"We couldn't read this attendance sheet."

If student cannot be matched:

Show:
"Student could not be matched."

If confidence is low:

Require manual confirmation.