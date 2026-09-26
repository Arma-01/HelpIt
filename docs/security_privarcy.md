# Security and Privacy

## Sensitive Data

Student names
Student IDs
Attendance records
Institution information

## Requirements

- HTTPS in production
- Authentication
- Authorization
- Institution-level data isolation
- No plaintext passwords
- No ERP credentials stored directly
- Minimal data collection
- Secure API communication
- Audit logs

## Image Policy

Attendance images should not be permanently stored unless
required by the institution.

If temporary storage is required:

- Encrypt storage
- Define retention period
- Delete automatically

## ERP

Do not bypass:

- Login
- CAPTCHA
- MFA
- Authorization
- Access controls

ERP automation must operate only with authorized access.