import logging


logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    def __init__(self, message, status_code=503):
        self.message = message
        self.status_code = status_code
        super().__init__(message)