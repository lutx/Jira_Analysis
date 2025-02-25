from typing import Optional, Dict, Any
from werkzeug.exceptions import HTTPException

class BaseAppException(Exception):
    """Base exception for application."""
    def __init__(self, message=None, code=None):
        super().__init__(message)
        self.message = message or "An error occurred"
        self.code = code or 500

    def to_dict(self):
        return {
            'error': self.__class__.__name__.lower(),
            'message': self.message,
            'code': self.code
        }

class AppException(BaseAppException):
    """Generic application exception."""
    pass

class AppError(HTTPException):
    """Base exception class for application."""
    code = 500  # Default HTTP status code
    
    def __init__(self, message: str, details: dict = None, code: int = None):
        super().__init__(description=message)
        self.message = message
        self.details = details or {}
        if code is not None:
            self.code = code

    def __str__(self):
        return f"{self.message} (details: {self.details})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            'error': True,
            'message': self.message,
            'details': self.details,
            'error_type': self.__class__.__name__,
            'code': self.code
        }

class ValidationError(BaseAppException):
    """Validation related errors."""
    def __init__(self, message=None):
        super().__init__(message or "Validation failed", 400)

class ExportError(AppError):
    """Raised when export operation fails."""
    code = 500

class DatabaseError(BaseAppException):
    """Database related errors."""
    def __init__(self, message=None):
        super().__init__(message or "Database error occurred", 500)

class JiraError(AppError):
    """Raised when JIRA operation fails."""
    code = 502

class IntegrationError(AppError):
    """Raised when external integration fails."""
    code = 502

class ResourceNotFoundError(BaseAppException):
    """Resource not found errors."""
    def __init__(self, message=None):
        super().__init__(message or "Resource not found", 404)

class ResourceConflictError(AppError):
    """Raised when resource operation causes conflict."""
    code = 409

class BusinessLogicError(AppError):
    """Raised when business logic validation fails."""
    code = 422

class AuthenticationError(BaseAppException):
    """Authentication related errors."""
    def __init__(self, message=None):
        super().__init__(message or "Authentication failed", 401)

class AuthorizationError(BaseAppException):
    """Authorization related errors."""
    def __init__(self, message=None):
        super().__init__(message or "Access denied", 403)

class ConfigurationError(AppException):
    """Raised when there's a configuration error"""
    def __init__(self, message: str):
        super().__init__(message, code=500)

def handle_app_error(error: AppError) -> Dict[str, Any]:
    """Convert application error to dictionary response."""
    if isinstance(error, AppError):
        return error.to_dict()
    return {
        'error': True,
        'message': str(error),
        'error_type': error.__class__.__name__,
        'code': getattr(error, 'code', 500)
    }

def handle_exception(error: Exception) -> Dict[str, Any]:
    """Convert generic exception to dictionary response."""
    return {
        'error': True,
        'message': str(error),
        'error_type': error.__class__.__name__,
        'code': 500
    } 