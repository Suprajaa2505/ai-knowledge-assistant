from google import genai

from app.config import GEMINI_API_KEY
from app.gemini_service import GeminiServiceError, call_with_retry


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

    response = call_with_retry(
        client.models.generate_content,
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    if not response.text:
        raise GeminiServiceError(
            "The AI service returned an empty response.",
            status_code=503
        )

    result = response.text.strip()

    # LLMs do not follow output formats perfectly ("yes", "YES:", "No.").
    # Be tolerant; if unsure, fall back to the user's own question.
    first_word = result.upper().split(None, 1)[0].strip(":.,") if result else ""

    if first_word == "YES":
        rewritten_query = result[3:].lstrip(" :\n\t").strip()

        if rewritten_query:
            return rewritten_query, True

    return query, False
