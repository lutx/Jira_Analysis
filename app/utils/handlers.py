from typing import Any, Optional
from logging import Handler, LogRecord

class DefaultHandler(Handler):
    def __init__(self):
        super().__init__()
        
    def emit(self, record: LogRecord) -> None:
        pass

default_handler = DefaultHandler() 