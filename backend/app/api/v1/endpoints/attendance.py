"""
Attendance image processing and student matching endpoints.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.logging import logger
from app.core.exceptions import AttendanceException
from app.schemas.attendance import (
    AttendanceProcessResponse,
    ApiErrorResponse,
    ApiErrorDetail,
)
from app.schemas.student import (
    MatchAttendanceRequest,
    MatchAttendanceResponse,
)
from app.services.attendance_service import attendance_service
from app.services.matching_service import matching_service

router = APIRouter()


@router.post(
    "/process",
    response_model=AttendanceProcessResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid image file"},
        413: {"model": ApiErrorResponse, "description": "File too large"},
        422: {"model": ApiErrorResponse, "description": "No attendance detected"},
        500: {"model": ApiErrorResponse, "description": "OCR / Vision processing error"},
    },
    summary="Process Attendance Image",
    description="Upload an attendance register/sheet image to extract structured attendance records.",
)
async def process_attendance_image(
    file: UploadFile = File(..., description="Attendance register image (JPG, PNG, or WebP)"),
):
    logger.info(f"POST /api/v1/attendance/process received file: {file.filename} ({file.content_type})")

    try:
        # Read uploaded image bytes directly in memory (no permanent disk storage)
        file_bytes = await file.read()
        
        result = attendance_service.process_image(
            file_bytes=file_bytes,
            filename=file.filename or "unknown.jpg",
            content_type=file.content_type or "",
        )
        return result

    except AttendanceException as exc:
        logger.warning(f"Attendance processing exception [{exc.code}]: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": {"code": exc.code, "message": exc.message}},
        )
    except Exception as exc:
        logger.error(f"Unexpected error processing attendance image: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred while processing the image.",
                },
            },
        )
    finally:
        await file.close()


@router.post(
    "/match",
    response_model=MatchAttendanceResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid matching request payload"},
        500: {"model": ApiErrorResponse, "description": "Internal matching engine error"},
    },
    summary="Match AI Attendance with ERP Students",
    description="Deterministically match AI-extracted attendance records with the active ERP classroom student roster.",
)
async def match_attendance(request: MatchAttendanceRequest):
    logger.info(
        f"POST /api/v1/attendance/match received {len(request.ai_records)} AI records, "
        f"{len(request.erp_students)} ERP students"
    )

    try:
        response = matching_service.match_attendance(request)
        return response
    except Exception as exc:
        logger.error(f"Unexpected error during student matching: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "MATCHING_ERROR",
                    "message": "An unexpected error occurred during student matching.",
                },
            },
        )
