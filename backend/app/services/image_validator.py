"""
Image validation service.
Validates file size, MIME type, and image data integrity using PIL.
"""

import io
from PIL import Image, UnidentifiedImageError
from app.config import settings
from app.core.exceptions import InvalidImageError, FileTooLargeError
from app.core.logging import logger


class ImageValidator:
    """Validates image uploads before passing them to the AI pipeline."""

    @staticmethod
    def validate(file_bytes: bytes, filename: str, content_type: str = "") -> Image.Image:
        """
        Validates an uploaded image file:
        1. Checks non-empty
        2. Checks file size against MAX_FILE_SIZE_BYTES
        3. Verifies image integrity using PIL
        4. Validates MIME/format
        
        Returns the opened PIL Image if valid, or raises an AttendanceException.
        """
        logger.info(f"Validating upload: {filename} ({len(file_bytes)} bytes, content-type: {content_type})")

        # 1. Non-empty check
        if not file_bytes or len(file_bytes) == 0:
            logger.warning(f"Validation failed: Empty file payload for {filename}")
            raise InvalidImageError("Uploaded file is empty.")

        # 2. Size check
        if len(file_bytes) > settings.MAX_FILE_SIZE_BYTES:
            logger.warning(
                f"Validation failed: File size {len(file_bytes)} bytes exceeds limit {settings.MAX_FILE_SIZE_BYTES}"
            )
            raise FileTooLargeError(
                f"Image is too large. Maximum size is {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
            )

        # 3. Content-Type check (if provided by client)
        clean_content_type = (content_type or "").lower().split(";")[0].strip()
        if clean_content_type and clean_content_type not in settings.ALLOWED_CONTENT_TYPES:
            # Also allow generic stream if extension matches
            valid_extensions = (".jpg", ".jpeg", ".png", ".webp")
            if not any(filename.lower().endswith(ext) for ext in valid_extensions):
                logger.warning(f"Validation failed: Unsupported content-type {clean_content_type} for {filename}")
                raise InvalidImageError("Please upload a valid attendance image (JPG, PNG, or WebP).")

        # 4. Image integrity & decoding check using PIL
        try:
            image_stream = io.BytesIO(file_bytes)
            img = Image.open(image_stream)
            img.verify()  # Verifies file header and integrity
            
            # Reopen because verify() closes the stream state
            image_stream.seek(0)
            img = Image.open(image_stream)
            
            # Format verification
            fmt = (img.format or "").upper()
            if fmt not in ("JPEG", "JPG", "PNG", "WEBP"):
                logger.warning(f"Validation failed: Disallowed image format {fmt} for {filename}")
                raise InvalidImageError(f"Unsupported image format: {fmt}. Use JPEG, PNG, or WebP.")

            # Sanity check dimensions
            width, height = img.size
            if width < 50 or height < 50:
                logger.warning(f"Validation failed: Image dimensions too small ({width}x{height})")
                raise InvalidImageError("Image dimensions are too small to detect attendance.")

            logger.info(f"Image validation passed: {filename} ({fmt}, {width}x{height})")
            return img

        except UnidentifiedImageError:
            logger.warning(f"Validation failed: Unidentified image format for {filename}")
            raise InvalidImageError("Please upload a valid attendance image.")
        except Exception as e:
            if isinstance(e, (InvalidImageError, FileTooLargeError)):
                raise
            logger.warning(f"Validation failed with error: {str(e)}")
            raise InvalidImageError("Invalid image file or corrupted data.")
