"""
Custom exceptions for attendance processing pipeline.
"""

class AttendanceException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidImageError(AttendanceException):
    def __init__(self, message: str = "Please upload a valid attendance image."):
        super().__init__(code="INVALID_IMAGE", message=message, status_code=400)


class FileTooLargeError(AttendanceException):
    def __init__(self, message: str = "Image is too large. Maximum size is 10MB."):
        super().__init__(code="FILE_TOO_LARGE", message=message, status_code=413)


class NoAttendanceDetectedError(AttendanceException):
    def __init__(self, message: str = "No attendance information could be detected."):
        super().__init__(code="NO_ATTENDANCE_DETECTED", message=message, status_code=422)


class OCRFailureError(AttendanceException):
    def __init__(self, message: str = "Unable to analyze the attendance image."):
        super().__init__(code="OCR_FAILURE", message=message, status_code=500)


class MalformedAIResponseError(AttendanceException):
    def __init__(self, message: str = "AI output validation failed."):
        super().__init__(code="MALFORMED_AI_RESPONSE", message=message, status_code=502)
