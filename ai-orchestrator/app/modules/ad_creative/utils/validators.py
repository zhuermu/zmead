"""
File validators for creative uploads.

Requirements: 2.2
- Validates file format (JPG/PNG only)
- Validates file size (max 10MB)
- Validates file magic numbers to prevent spoofing
"""

from dataclasses import dataclass
from typing import Literal


class FileValidationError(Exception):
    """Exception raised when file validation fails."""

    def __init__(self, message: str, error_code: str = "FILE_VALIDATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass
class ValidationResult:
    """Result of file validation."""

    is_valid: bool
    error_message: str = ""
    error_code: str | None = None
    detected_type: str | None = None


class FileValidator:
    """Validates uploaded files for format and size.

    Validates:
    - File format (JPG/PNG only)
    - File size (max 10MB)
    - File magic numbers to detect actual file type

    Example:
        validator = FileValidator()
        result = validator.validate(file_data, "image/jpeg", len(file_data))
        if not result.is_valid:
            raise FileValidationError(result.error_message)
    """

    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FORMATS: set[str] = {"image/jpeg", "image/png"}

    # Magic numbers for file type detection
    # JPEG: starts with FF D8 FF
    # PNG: starts with 89 50 4E 47 0D 0A 1A 0A (hex for \x89PNG\r\n\x1a\n)
    MAGIC_NUMBERS: dict[bytes, str] = {
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89PNG\r\n\x1a\n": "image/png",
    }

    # Minimum bytes needed for magic number detection
    MIN_BYTES_FOR_DETECTION: int = 8

    def validate_format(self, file_type: str) -> bool:
        """Validate file format by MIME type.

        Args:
            file_type: MIME type string (e.g., "image/jpeg")

        Returns:
            True if format is allowed (JPG or PNG)
        """
        return file_type.lower() in self.ALLOWED_FORMATS

    def validate_size(self, file_size: int) -> bool:
        """Validate file size is within limit.

        Args:
            file_size: Size in bytes

        Returns:
            True if size is within 10MB limit
        """
        return 0 < file_size <= self.MAX_FILE_SIZE

    def validate_magic_number(self, file_data: bytes) -> str | None:
        """Validate file by checking magic number (file signature).

        This prevents file type spoofing by checking the actual
        file content rather than trusting the declared MIME type.

        Args:
            file_data: File bytes (at least first 8 bytes needed)

        Returns:
            Detected MIME type or None if not recognized
        """
        if len(file_data) < self.MIN_BYTES_FOR_DETECTION:
            return None

        for magic, mime_type in self.MAGIC_NUMBERS.items():
            if file_data.startswith(magic):
                return mime_type
        return None

    def validate(
        self,
        file_data: bytes,
        file_type: str,
        file_size: int,
    ) -> ValidationResult:
        """Perform complete file validation.

        Validates:
        1. File format (MIME type must be JPG or PNG)
        2. File size (must be <= 10MB)
        3. Magic number (actual content must match declared type)

        Args:
            file_data: File bytes
            file_type: Declared MIME type
            file_size: File size in bytes

        Returns:
            ValidationResult with is_valid flag and error details if invalid
        """
        # Validate format
        if not self.validate_format(file_type):
            return ValidationResult(
                is_valid=False,
                error_message=f"不支持的文件格式: {file_type}，仅支持 JPG/PNG",
                error_code="INVALID_FORMAT",
            )

        # Validate size
        if not self.validate_size(file_size):
            size_mb = file_size / (1024 * 1024)
            return ValidationResult(
                is_valid=False,
                error_message=f"文件大小超过限制: {size_mb:.1f}MB，最大 10MB",
                error_code="FILE_TOO_LARGE",
            )

        # Validate magic number
        detected_type = self.validate_magic_number(file_data)
        if detected_type is None:
            return ValidationResult(
                is_valid=False,
                error_message="无效的文件内容，无法识别文件类型",
                error_code="INVALID_CONTENT",
            )

        # Check if detected type matches declared type
        if detected_type != file_type.lower():
            return ValidationResult(
                is_valid=False,
                error_message=f"文件类型不匹配: 声明 {file_type}，实际 {detected_type}",
                error_code="TYPE_MISMATCH",
                detected_type=detected_type,
            )

        return ValidationResult(
            is_valid=True,
            detected_type=detected_type,
        )

    def validate_or_raise(
        self,
        file_data: bytes,
        file_type: str,
        file_size: int,
    ) -> Literal[True]:
        """Validate file and raise exception if invalid.

        Convenience method that raises FileValidationError on failure.

        Args:
            file_data: File bytes
            file_type: Declared MIME type
            file_size: File size in bytes

        Returns:
            True if valid

        Raises:
            FileValidationError: If validation fails
        """
        result = self.validate(file_data, file_type, file_size)
        if not result.is_valid:
            raise FileValidationError(
                message=result.error_message,
                error_code=result.error_code or "FILE_VALIDATION_ERROR",
            )
        return True


class UploadCountValidator:
    """Validates upload count limits.

    Requirements: 2.5
    - Maximum 5 reference images per upload session
    """

    MAX_UPLOAD_COUNT: int = 5

    def validate_count(self, current_count: int, new_count: int = 1) -> ValidationResult:
        """Validate if adding new uploads would exceed limit.

        Args:
            current_count: Current number of uploaded images
            new_count: Number of new images to upload

        Returns:
            ValidationResult with is_valid flag
        """
        total = current_count + new_count
        if total > self.MAX_UPLOAD_COUNT:
            return ValidationResult(
                is_valid=False,
                error_message=f"上传数量超过限制: 最多 {self.MAX_UPLOAD_COUNT} 张，"
                f"当前已有 {current_count} 张",
                error_code="UPLOAD_LIMIT_EXCEEDED",
            )
        return ValidationResult(is_valid=True)

    def validate_count_or_raise(
        self,
        current_count: int,
        new_count: int = 1,
    ) -> Literal[True]:
        """Validate upload count and raise exception if exceeded.

        Args:
            current_count: Current number of uploaded images
            new_count: Number of new images to upload

        Returns:
            True if valid

        Raises:
            FileValidationError: If limit exceeded
        """
        result = self.validate_count(current_count, new_count)
        if not result.is_valid:
            raise FileValidationError(
                message=result.error_message,
                error_code=result.error_code or "UPLOAD_LIMIT_EXCEEDED",
            )
        return True
