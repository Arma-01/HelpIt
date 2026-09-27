# AI Attendance Assistant — Backend API

FastAPI backend providing the Phase 1 image processing pipeline for attendance sheet extraction.

## Features

- **FastAPI Endpoint**: `POST /api/v1/attendance/process` (multipart/form-data)
- **Image Validation**: Checks file format (JPEG, PNG, WebP), file size limits (default: 10MB), and header integrity.
- **Pluggable Vision Engine**:
  - `EasyOCRVisionProvider`: Local neural text detection & recognition with 2D tabular clustering and confidence calculation.
  - `MockVisionProvider`: Deterministic synthetic provider for instant testing/demos.
  - `HybridVisionProvider`: Production default combining local neural OCR with robust fallback handling.
- **Strict Attendance Normalization**:
  - Standardizes strictly to: `PRESENT` and `ABSENT` (LATE and UNKNOWN completely removed).
  - Unclear or low-confidence marks trigger review without inventing a third status.
- **Privacy-Conscious**: In-memory stream processing without permanent image retention or sensitive data logging.

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

### 3. Run Automated Tests

```bash
pytest tests -v
```
