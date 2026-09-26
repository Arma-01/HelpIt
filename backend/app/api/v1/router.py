"""
API v1 Router aggregation.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import attendance, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
