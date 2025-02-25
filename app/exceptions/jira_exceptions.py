from app.exceptions import BaseAppException

class JiraConfigError(BaseAppException):
    """Base exception for JIRA configuration errors."""
    def __init__(self, message="JIRA configuration error", status_code=400):
        super().__init__(message, status_code)

class JiraConnectionError(JiraConfigError):
    """Exception raised when connection to JIRA fails."""
    def __init__(self, message="Failed to connect to JIRA"):
        super().__init__(message, status_code=503)

class JiraAuthenticationError(JiraConfigError):
    """Exception raised when JIRA authentication fails."""
    def __init__(self, message="JIRA authentication failed"):
        super().__init__(message, status_code=401)

class JiraValidationError(JiraConfigError):
    """Exception raised when JIRA configuration validation fails."""
    def __init__(self, message="Invalid JIRA configuration"):
        super().__init__(message, status_code=400) 