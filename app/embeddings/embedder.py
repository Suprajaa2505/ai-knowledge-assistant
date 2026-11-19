from google import genai

from app.config import GEMINI_API_KEY
from app.gemini_service import GeminiServiceError, call_with_retry


client = genai.Client(api_key=GEMINI_API_KEY)

# Send at most this many texts per request (keeps each request small and safe).
BATCH_SIZE = 100


def create_embeddings(texts):
    vectors = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]

        response = call_with_retry(
            client.models.embed_content,
            model="gemini-embedding-001",
            contents=batch
        )

        if not response.embeddings:
            raise GeminiServiceError(
                "The AI service returned no embeddings.",
                status_code=503
            )

        vectors.extend(embedding.values for embedding in response.embeddings)

    return vectors
