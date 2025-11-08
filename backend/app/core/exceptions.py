"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Base exception class for application-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


# Authentication and Authorization Exceptions
class AuthenticationError(BaseAppException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(BaseAppException):
    """Raised when user lacks required permissions."""
    pass


class InsufficientPermissionError(AuthorizationError):
    """Raised when user doesn't have sufficient permissions."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""
    pass


# User-related Exceptions
class UserNotFoundError(BaseAppException):
    """Raised when user is not found."""
    pass


class UserAlreadyExistsError(BaseAppException):
    """Raised when trying to create a user that already exists."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""
    pass


# Class-related Exceptions
class ClassNotFoundError(BaseAppException):
    """Raised when class is not found."""
    pass


class ClassAlreadyExistsError(BaseAppException):
    """Raised when trying to create a class that already exists."""
    pass


class DuplicateClassCodeError(BaseAppException):
    """Raised when class code already exists."""
    pass


class StudentAlreadyInClassError(BaseAppException):
    """Raised when student is already enrolled in the class."""
    pass


class StudentNotInClassError(BaseAppException):
    """Raised when student is not enrolled in the class."""
    pass


class InvalidClassCodeError(BaseAppException):
    """Raised when class code is invalid or expired."""
    pass


# Assignment-related Exceptions
class AssignmentNotFoundError(BaseAppException):
    """Raised when assignment is not found."""
    pass


class SubmissionNotFoundError(BaseAppException):
    """Raised when submission is not found."""
    pass


class DuplicateSubmissionError(BaseAppException):
    """Raised when student tries to submit multiple times."""
    pass


# File-related Exceptions
class FileNotFoundError(BaseAppException):
    """Raised when file is not found."""
    pass


class FileUploadError(BaseAppException):
    """Raised when file upload fails."""
    pass


class InvalidFileTypeError(BaseAppException):
    """Raised when file type is not allowed."""
    pass


class FileSizeExceededError(BaseAppException):
    """Raised when file size exceeds limit."""
    pass


# AI Service Exceptions
class AIServiceError(BaseAppException):
    """Raised when AI service encounters an error."""
    pass


class GradingError(BaseAppException):
    """Raised when grading operation fails."""
    pass


class GradingTaskNotFoundError(BaseAppException):
    """Raised when grading task is not found."""
    pass


class GradingTaskFailedError(BaseAppException):
    """Raised when grading task fails."""
    pass


# General Exceptions
class NotFoundError(BaseAppException):
    """Raised when a resource is not found."""
    pass


# Validation Exceptions
class ValidationError(BaseAppException):
    """Raised when data validation fails."""
    pass


class DatabaseError(BaseAppException):
    """Raised when database operation fails."""
    pass


class ExternalServiceError(BaseAppException):
    """Raised when external service call fails."""
    pass


# Rate Limiting Exceptions
class RateLimitExceededError(BaseAppException):
    """Raised when rate limit is exceeded."""
    pass


# Cache Exceptions
class CacheError(BaseAppException):
    """Raised when cache operation fails."""
    pass