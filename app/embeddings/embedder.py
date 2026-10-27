from google import genai

from app.config import GEMINI_API_KEY
from app.gemini_service import GeminiServiceError,logger


client = genai.Client(api_key=GEMINI_API_KEY)


def create_embeddings(texts):
    try:
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts
        )

    except Exception as error:
        logger.exception("Gemini answer generation failed")
        status_code = getattr(error, "status_code", None)

        if status_code == 429:
            raise GeminiServiceError(
                "The AI service rate limit has been reached. Please try again later.",
                status_code=429
            )

        if status_code == 503:
            raise GeminiServiceError(
                "The AI service is temporarily unavailable. Please try again later.",
                status_code=503
            )

        raise GeminiServiceError(
            "The AI service could not process the request. Please try again later.",
            status_code=503
        )

    if not response.embeddings:
        raise GeminiServiceError(
            "The AI service returned no embeddings.",
            status_code=503
        )

    return [embedding.values for embedding in response.embeddings]