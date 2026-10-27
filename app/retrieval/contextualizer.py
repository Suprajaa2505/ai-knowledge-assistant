from google import genai

from app.config import GEMINI_API_KEY
from app.gemini_service import GeminiServiceError, logger


client = genai.Client(api_key=GEMINI_API_KEY)


def contextualize_query(query, recent_messages):
    if not recent_messages:
        return query, False

    conversation = "\n".join(
        f'{message["role"].capitalize()}: {message["content"]}'
        for message in recent_messages
    )

    prompt = f"""
You are helping a document-based RAG system understand whether a
user's current question depends on the previous conversation.

Previous conversation:
{conversation}

Current question:
{query}

Determine whether the current question depends on the previous
conversation.

If it is standalone and can be understood without the previous
conversation, return exactly:

NO

If it depends on the previous conversation, return:

YES
<rewritten question>

The rewritten question must be self-contained and preserve the
user's original meaning.

Do not answer the question.
Do not add explanations.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

    except Exception as error:
        logger.exception("Gemini contextualization failed")
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

    if not response.text:
        raise GeminiServiceError(
            "The AI service returned an empty response.",
            status_code=503
        )

    result = response.text.strip()

    if result == "NO":
        return query, False

    if result.startswith("YES"):
        rewritten_query = result[3:].strip()

        if rewritten_query:
            return rewritten_query, True

    return query, False