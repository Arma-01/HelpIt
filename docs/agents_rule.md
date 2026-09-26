# AI Coding Agent Rules

You are the primary coding agent for the AI Attendance Assistant.

## Mission

Build the project according to the documentation in /docs.

## Before Coding

Always read:

1. 00-PROJECT-OVERVIEW.md
2. 01-PRODUCT-REQUIREMENTS.md
3. 03-SYSTEM-ARCHITECTURE.md
4. 14-MVP-ROADMAP.md
5. 15-CODING-STANDARDS.md

Then read any module-specific documentation relevant to the task.

## Development Rules

1. Do not implement features not requested by the current phase.
2. Do not skip the MVP roadmap.
3. Do not replace existing architecture without reason.
4. Do not invent ERP APIs.
5. Do not assume an ERP DOM structure without inspection.
6. Never bypass authentication or security controls.
7. Never automatically submit official attendance.
8. Never silently convert uncertain AI results into ABSENT.
9. Keep AI, matching, and ERP integration modular.
10. Ask for clarification when a requirement is genuinely ambiguous.

## After Implementation

Always:

1. Run tests.
2. Check for console errors.
3. Check backend errors.
4. Verify the affected user flow.
5. Report files changed.
6. Report tests performed.
7. Report remaining issues.

## Phase Discipline

Complete the current MVP phase before implementing future phases.

Do not build:

- mobile app
- payment system
- analytics
- multiple ERP adapters
- unnecessary AI features

unless explicitly requested.