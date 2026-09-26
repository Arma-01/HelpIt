# System Architecture

## Components

### Browser Extension

Responsible for:

- Popup UI
- ERP page detection
- DOM reading
- ERP field manipulation
- Communication with backend

### Backend

Responsible for:

- Authentication
- Image processing
- AI processing
- Attendance extraction
- Student matching
- Confidence calculation
- API endpoints

### Database

Responsible for:

- Institutions
- Students
- Teachers
- Attendance sessions
- Processing logs

### AI Layer

Responsible for:

- OCR
- Table understanding
- Attendance status detection
- Structured extraction

## Architecture

Browser Extension
        |
        | HTTPS
        v
FastAPI Backend
        |
        +---- AI/Vision
        |
        +---- Matching Engine
        |
        +---- Database

Browser Extension
        |
        v
Existing ERP DOM