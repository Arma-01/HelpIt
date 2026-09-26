# MVP Roadmap

## Phase 1 — Extension

- Create Manifest V3 extension
- Popup
- Content script
- Service worker
- Load unpacked extension

## Phase 2 — Mock ERP

- Create fake ERP attendance page
- Student table
- Present/absent controls

## Phase 3 — ERP DOM Reading

- Detect attendance page
- Extract students
- Extract roll numbers

## Phase 4 — Backend

- FastAPI
- Health endpoint
- Image upload endpoint

## Phase 5 — AI

- OCR/Vision
- Structured attendance result
- Confidence

## Phase 6 — Matching

- Roll number matching
- Student ID matching
- Name fallback
- Ambiguous match handling

## Phase 7 — Apply

- Modify mock ERP
- Highlight modified rows
- Teacher confirmation

## Phase 8 — Testing

- Unit tests
- Integration tests
- Error handling

## Phase 9 — Real ERP

Only after the mock ERP workflow is stable.

Implement one authorized ERP adapter.

## Do Not Build Yet

- Mobile app
- Multiple ERP adapters
- Face recognition
- Analytics dashboard
- Student app
- Payments
- Subscription system