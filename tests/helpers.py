"""Small helpers shared by several test files."""
from google.genai import errors

REFUSAL_TEXT = "I couldn't find the answer in the provided documents."


def rate_limit_error():
    return errors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})


def unavailable_error():
    return errors.ServerError(503, {"error": {"message": "busy", "status": "UNAVAILABLE"}})


def bad_request_error():
    return errors.ClientError(400, {"error": {"message": "bad", "status": "INVALID_ARGUMENT"}})
