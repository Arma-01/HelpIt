"""
Generate a realistic synthetic attendance sheet image for testing and demonstration.
Contains clear columns: Roll No | Student Name | Status
"""

import os
from PIL import Image, ImageDraw, ImageFont

def generate_attendance_sheet(output_path: str = "backend/tests/fixtures/attendance_demo.jpg"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    width = 900
    height = 650
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Use default font or truetype if available
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_header = ImageFont.truetype("arial.ttf", 18)
        font_body = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Draw Title Header
    draw.rectangle([(0, 0), (width, 80)], fill=(240, 244, 248))
    draw.text((30, 25), "DAILY CLASS ATTENDANCE REGISTER", fill=(15, 23, 42), font=font_title)
    draw.text((600, 30), "Date: 2026-09-26", fill=(71, 85, 105), font=font_header)

    # Table Header
    start_y = 100
    row_height = 45
    
    col_roll_x = 40
    col_name_x = 200
    col_status_x = 600

    # Header Box
    draw.rectangle([(30, start_y), (width - 30, start_y + row_height)], fill=(226, 232, 240))
    draw.text((col_roll_x, start_y + 12), "ROLL NO", fill=(15, 23, 42), font=font_header)
    draw.text((col_name_x, start_y + 12), "STUDENT NAME", fill=(15, 23, 42), font=font_header)
    draw.text((col_status_x, start_y + 12), "ATTENDANCE STATUS", fill=(15, 23, 42), font=font_header)

    # Student Rows
    students = [
        ("001", "Aarav Sharma", "Present"),
        ("002", "Rahul Kumar", "Present"),
        ("003", "Priya Singh", "Absent"),
        ("004", "Ankit Sharma", "Late"),
        ("005", "Sneha Patel", "Present"),
        ("006", "Vikram Rao", "Present"),
        ("007", "Neha Gupta", "Absent"),
        ("008", "Rohan Verma", "Present"),
        ("009", "Ananya Mishra", "Present"),
        ("010", "Aditya Joshi", "Late"),
    ]

    for idx, (roll, name, status) in enumerate(students):
        y = start_y + (idx + 1) * row_height
        # Alternate row background
        bg_color = (248, 250, 252) if idx % 2 == 1 else (255, 255, 255)
        draw.rectangle([(30, y), (width - 30, y + row_height)], fill=bg_color)
        
        # Grid line
        draw.line([(30, y + row_height), (width - 30, y + row_height)], fill=(226, 232, 240), width=1)

        draw.text((col_roll_x, y + 12), roll, fill=(51, 65, 85), font=font_body)
        draw.text((col_name_x, y + 12), name, fill=(15, 23, 42), font=font_body)

        # Status text color
        if status == "Present":
            status_color = (22, 101, 52)
        elif status == "Absent":
            status_color = (185, 28, 28)
        elif status == "Late":
            status_color = (180, 83, 9)
        else:
            status_color = (71, 85, 105)

        draw.text((col_status_x, y + 12), status, fill=status_color, font=font_body)

    # Outer table border
    draw.rectangle([(30, start_y), (width - 30, start_y + (len(students) + 1) * row_height)], outline=(203, 213, 225), width=2)

    image.save(output_path, "JPEG", quality=95)
    print(f"Generated synthetic test attendance image: {output_path}")

if __name__ == "__main__":
    generate_attendance_sheet()
