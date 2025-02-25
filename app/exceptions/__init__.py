"""Custom exceptions package."""

# Base Exceptions
class BaseAppException(Exception):
    """Base exception class for application."""
    def __init__(self, message="An error occurred", status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def to_dict(self):
        """Convert exception to dictionary."""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'status_code': self.status_code
        }

class AppException(BaseAppException):
    """General application exception."""
    def __init__(self, message="Application error occurred", status_code=500):
        super().__init__(message, status_code)

class AppError(AppException):
    """Alias for AppException for backward compatibility."""
    pass

# Authentication & Authorization Exceptions
class AuthenticationError(BaseAppException):
    """Exception raised for authentication errors."""
    def __init__(self, message="Authentication failed", status_code=401):
        super().__init__(message, status_code)

class AuthorizationError(BaseAppException):
    """Exception raised for authorization errors."""
    def __init__(self, message="Authorization failed", status_code=403):
        super().__init__(message, status_code)

# Data & Validation Exceptions
class ValidationError(BaseAppException):
    """Exception raised for validation errors."""
    def __init__(self, message="Validation error", status_code=400):
        super().__init__(message, status_code)

class DatabaseError(BaseAppException):
    """Exception raised for database errors."""
    def __init__(self, message="Database error", status_code=500):
        super().__init__(message, status_code)

# Business Logic Exceptions
class BusinessLogicError(BaseAppException):
    """Exception raised for business logic errors."""
    def __init__(self, message="Business logic error", status_code=422):
        super().__init__(message, status_code)

# Resource Exceptions
class ResourceNotFoundError(BaseAppException):
    """Exception raised when a resource is not found."""
    def __init__(self, message="Resource not found", status_code=404):
        super().__init__(message, status_code)

# Service Exceptions
class ServiceError(BaseAppException):
    """Exception raised for service-level errors."""
    def __init__(self, message="Service error", status_code=500):
        super().__init__(message, status_code)

# JIRA Related Exceptions
class JiraError(BaseAppException):
    """Base exception for JIRA-related errors."""
    def __init__(self, message="JIRA error", status_code=500):
        super().__init__(message, status_code)

class JiraValidationError(JiraError):
    """Exception raised for JIRA validation errors."""
    pass

class JiraConnectionError(JiraError):
    """Exception raised for JIRA connection errors."""
    pass

class JiraConfigurationError(JiraError):
    """Exception raised for JIRA configuration errors."""
    pass

class SyncError(BaseAppException):
    """Exception raised for synchronization errors."""
    def __init__(self, message="Synchronization error", status_code=500):
        super().__init__(message, status_code)

# Report & Export Exceptions
class ReportError(BaseAppException):
    """Exception raised for report generation errors."""
    def __init__(self, message="Report generation error", status_code=500):
        super().__init__(message, status_code)

class ExportError(BaseAppException):
    """Exception raised for export-related errors."""
    def __init__(self, message="Export operation failed", status_code=500):
        super().__init__(message, status_code)

class WorklogError(BaseAppException):
    """Exception raised for worklog-related errors."""
    def __init__(self, message="Worklog error", status_code=500):
        super().__init__(message, status_code)

# General Application Exceptions
class ConfigurationError(BaseAppException):
    """Exception raised for configuration errors."""
    def __init__(self, message="Configuration error", status_code=500):
        super().__init__(message, status_code)

# Export all exceptions
__all__ = [
    'BaseAppException',
    'AppException',
    'AppError',
    'ValidationError',
    'DatabaseError',
    'AuthenticationError',
    'AuthorizationError',
    'ResourceNotFoundError',
    'ConfigurationError',
    'ServiceError',
    'JiraError',
    'ReportError',
    'WorklogError',
    'SyncError',
    'ExportError',
    'BusinessLogicError',
    'JiraValidationError',
    'JiraConnectionError',
    'JiraConfigurationError'
] 