"""
FastAPI Application Entry Point for AI Attendance Assistant.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.core.logging import logger
from app.core.exceptions import AttendanceException
from app.api.v1.router import api_router

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"=== {settings.PROJECT_NAME} v{settings.VERSION} Starting ===")
    logger.info(f"Active Vision Provider: {settings.VISION_PROVIDER}")
    logger.info(f"API Base URL: {settings.API_V1_STR}")
    yield
    logger.info("=== Application Shutdown ===")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for AI Attendance Assistant - Phase 1 Image Processing Pipeline",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration for Chrome Extension and Local Development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Attendance Exception Handler
@app.exception_handler(AttendanceException)
async def attendance_exception_handler(request: Request, exc: AttendanceException):
    logger.warning(f"Handled AttendanceException [{exc.code}]: {exc.message} on {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)



@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
    }
