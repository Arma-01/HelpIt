# API Specification

Base URL:

/api/v1

## POST /attendance/process

Upload attendance image.

Request:

multipart/form-data

Response:

{
    "session_id": "...",
    "results": []
}

## POST /attendance/match

Match AI results with ERP students.

## POST /attendance/validate

Validate results before applying.

## GET /health

Health check.

## Rules

- Use Pydantic models.
- Validate all input.
- Return consistent error responses.
- Never return sensitive information unnecessarily.