import logging
import time


logger = logging.getLogger(__name__)

# Errors that are worth trying again (rate limit / temporarily unavailable).
RETRYABLE_STATUS_CODES = (429, 503)
MAX_RETRIES = 2          # 1 first try + 2 retries = 3 attempts in total
RETRY_BASE_DELAY = 2     # seconds; waits 2s, then 4s


class GeminiServiceError(Exception):
    def __init__(self, message, status_code=503):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def to_service_error(error):
    """Turn any Gemini/library exception into a friendly GeminiServiceError.

    NOTE: the google-genai library stores the HTTP status in `error.code`
    (not `error.status_code`).
    """
    status_code = getattr(error, "code", None)

    if status_code == 429:
        return GeminiServiceError(
            "The AI service rate limit has been reached. Please try again later.",
            status_code=429,
        )

    if status_code == 503:
        return GeminiServiceError(
            "The AI service is temporarily unavailable. Please try again later.",
            status_code=503,
        )

    return GeminiServiceError(
        "The AI service could not process the request. Please try again later.",
        status_code=503,
    )


def call_with_retry(function, *args, **kwargs):
    """Call a Gemini function; retry rate-limit / unavailable errors with back-off."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return function(*args, **kwargs)

        except Exception as error:
            status_code = getattr(error, "code", None)
            can_retry = status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES

            if can_retry:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Gemini error %s - retrying in %ss (attempt %s)",
                    status_code, delay, attempt + 1,
                )
                time.sleep(delay)
                continue

            logger.exception("Gemini call failed")
            raise to_service_error(error)
