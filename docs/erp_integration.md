# ERP Integration Architecture

## Principle

The core AI system must not depend on one specific ERP.

Use an ERP Adapter architecture.

## Standard Internal Interface

The extension should convert ERP data into:

Student {
    id
    rollNumber
    name
    attendanceControl
}

The AI returns:

AttendanceResult {
    studentIdentifier
    status
    confidence
}

## Adapter Concept

ERP Adapter
    |
    +-- detectPage()
    +-- extractStudents()
    +-- applyAttendance()
    +-- validatePage()

## Initial Adapter

MockERPAdapter

## Future Adapters

VMEDULifeAdapter
OtherERPAdapter

## Important

Never assume the DOM structure of every ERP is the same.

Each ERP must have its own adapter.

Do not hard-code ERP-specific selectors into the AI engine.