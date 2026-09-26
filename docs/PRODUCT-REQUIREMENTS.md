# Product Requirements

## Primary User

Teacher.

## Primary Goal

Reduce the time required to enter attendance into an existing ERP.

## Main User Story

As a teacher, I want to upload my attendance sheet and have the
system identify absent students and prepare the ERP attendance,
so that I don't have to manually enter every student's attendance.

## Functional Requirements

### FR-001 ERP Detection

The extension should determine whether the current page is a
supported attendance page.

### FR-002 Student Extraction

The extension should read the student rows visible on the ERP page.

### FR-003 Image Upload

Teacher can upload an attendance image.

### FR-004 AI Processing

Backend processes the image and returns structured attendance data.

### FR-005 Student Matching

System matches detected students with ERP students.

Priority:

1. Student ID
2. Roll number
3. Enrollment number
4. Exact name
5. Fuzzy name matching

### FR-006 Confidence

Every AI result should have a confidence score.

### FR-007 Review

Teacher must be able to correct AI results.

### FR-008 Apply

Extension applies verified attendance to ERP fields.

### FR-009 Final Submission

Teacher manually submits the ERP attendance.

## Non-functional Requirements

- Fast UI
- Secure communication
- No unnecessary student data storage
- Clear error messages
- No silent attendance changes
- Audit-friendly architecture