# AI Attendance Assistant

## Project Vision

AI Attendance Assistant is a browser extension that helps teachers
transfer attendance from an existing attendance sheet/image into an
existing college/school ERP.

The product does NOT replace the institution's ERP.

The product acts as an AI-powered automation layer on top of the
existing ERP.

## Core Problem

Teachers often take or receive attendance in one format and then
manually enter the same information into an ERP.

This duplicate data entry consumes time and can cause mistakes.

## Core Solution

1. Teacher opens the existing ERP attendance page.
2. Browser extension detects the attendance page.
3. Teacher uploads or captures an attendance sheet/image.
4. AI analyzes the image.
5. AI determines present/absent status.
6. System matches students using roll number/student ID/name.
7. Extension displays the detected results.
8. Teacher reviews uncertain results.
9. Extension applies the attendance to the ERP.
10. Teacher performs the final ERP submission.

## Important Principle

The teacher remains the final authority.

The AI must never silently submit official attendance.

## MVP

The first version will support:

- Chrome browser
- One mock ERP
- Image upload
- Attendance extraction
- Student matching
- Confidence scores
- Teacher review
- Automatic filling of attendance fields
- Manual final submission

## Out of Scope for MVP

- Mobile application
- Multiple ERP integrations
- Facial recognition
- GPS tracking
- Student attendance app
- Automatic final ERP submission
- Bypassing authentication/CAPTCHA
- Scraping protected endpoints
- Autonomous browser actions outside authorized ERP workflows