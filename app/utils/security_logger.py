import logging
from datetime import datetime

security_logger = logging.getLogger('security')

def log_security_event(event_type: str, details: dict):
    """Loguje zdarzenie bezpieczeństwa."""
    security_logger.warning(
        f"Security Event: {event_type}",
        extra={
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            **details
        }
    )

def configure_security_logging(app):
    """Konfiguruje logowanie zdarzeń bezpieczeństwa."""
    handler = logging.FileHandler('security.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(event_type)s - %(message)s'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)
    security_logger.setLevel(logging.WARNING) 