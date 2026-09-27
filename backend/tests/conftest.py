"""
Pytest configuration and shared test fixtures for AI Attendance Assistant.
"""

import io
import pytest
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def valid_demo_image_bytes() -> bytes:
    """Creates an in-memory attendance register image with printed table."""
    width, height = 800, 500
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((30, 20), "DAILY ATTENDANCE SHEET", fill=(0, 0, 0))

    # Header
    draw.text((40, 80), "ROLL", fill=(0, 0, 0))
    draw.text((150, 80), "NAME", fill=(0, 0, 0))
    draw.text((450, 80), "STATUS", fill=(0, 0, 0))

    # Rows
    rows = [
        ("001", "Aarav Sharma", "Present"),
        ("002", "Rahul Kumar", "Present"),
        ("003", "Priya Singh", "Absent"),
        ("004", "Ankit Sharma", "Absent"),
    ]

    for i, (roll, name, status) in enumerate(rows):
        y = 130 + i * 50
        draw.text((40, y), roll, fill=(0, 0, 0))
        draw.text((150, y), name, fill=(0, 0, 0))
        draw.text((450, y), status, fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def blank_image_bytes() -> bytes:
    """Creates a blank white image with no attendance text."""
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def corrupted_image_bytes() -> bytes:
    """Invalid image file bytes."""
    return b"NOT_A_VALID_IMAGE_HEADER_BYTES_JUST_PLAIN_TEXT"
