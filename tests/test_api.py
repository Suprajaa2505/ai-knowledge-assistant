"""The real FastAPI app, real SQLite, real ChromaDB. Only Gemini is fake."""
from app import main
from tests.helpers import REFUSAL_TEXT, rate_limit_error


# ------------------------------ basics ----------------------------------------

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ------------------------------ upload ----------------------------------------

def test_upload_rejects_wrong_file_type(client):
    response = client.post("/upload", files={"file": ("virus.exe", b"x", "application/octet-stream")})

    assert response.status_code == 400
    assert "PDF and TXT" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    response = client.post("/upload", files={"file": ("empty.txt", b"", "text/plain")})

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_rejects_file_over_10mb(client):
    big = b"a" * (10 * 1024 * 1024 + 1)

    response = client.post("/upload", files={"file": ("big.txt", big, "text/plain")})

    assert response.status_code == 400
    assert "10 MB" in response.json()["detail"]
    assert client.get("/documents").json()["documents"] == []


def test_upload_success_is_listed_and_indexed(client, uploaded_doc):
    from app.vectorstore.chroma import collection
    documents = client.get("/documents").json()["documents"]

    assert [d["filename"] for d in documents] == ["rag_notes.txt"]
    assert collection.count() > 0
    assert client.get(f"/documents/{uploaded_doc['document_id']}").status_code == 200


def test_failed_upload_leaves_nothing_behind(client, monkeypatch):
    """If Gemini fails halfway, there must be no half-saved document."""
    from app.gemini_service import GeminiServiceError
    from app.ingestion import indexer

    def broken_embed(texts):
        raise GeminiServiceError("The AI service is temporarily unavailable.", status_code=503)

    monkeypatch.setattr(indexer, "create_embeddings", broken_embed)

    response = client.post("/upload", files={"file": ("notes.txt", b"some text", "text/plain")})

    assert response.status_code == 503
    assert client.get("/documents").json()["documents"] == []
    assert list(main.UPLOAD_DIR.glob("*")) == []


def test_delete_document_removes_record_file_and_chunks(client, uploaded_doc):
    from app.vectorstore.chroma import collection
    document_id = uploaded_doc["document_id"]

    response = client.delete(f"/documents/{document_id}")

    assert response.status_code == 200
    assert client.get(f"/documents/{document_id}").status_code == 404
    assert collection.count() == 0
    assert list(main.UPLOAD_DIR.glob("*")) == []


def test_delete_unknown_document_is_404(client):
    assert client.delete("/documents/nope").status_code == 404


# ------------------------------ chat ------------------------------------------

def test_chat_unknown_conversation_is_404(client):
    response = client.post("/conversations/nope/chat", json={"query": "hi"})

    assert response.status_code == 404


def test_chat_rejects_empty_question(client, conversation_id):
    response = client.post(f"/conversations/{conversation_id}/chat", json={"query": ""})

    assert response.status_code == 422


def test_chat_rejects_out_of_range_top_k(client, conversation_id):
    response = client.post(
        f"/conversations/{conversation_id}/chat", json={"query": "hi", "top_k": 99}
    )

    assert response.status_code == 422


def test_chat_returns_answer_sources_and_saves_the_conversation(
    client, conversation_id, uploaded_doc, answer_ai, context_ai
):
    answer_ai.reply = "RAG retrieves chunks first (rag_notes.txt)."

    response = client.post(
        f"/conversations/{conversation_id}/chat",
        json={"query": "How does retrieval augmented generation work?"},
    )

    assert response.status_code == 200, response.text
    body = response.json()

    # response shape (the contract the React frontend depends on)
    assert set(body) == {"conversation_id", "answer", "sources", "conversation_title"}
    assert body["answer"] == "RAG retrieves chunks first (rag_notes.txt)."
    assert set(body["sources"][0]) == {"document_id", "source", "page", "chunk_index", "citation"}
    assert body["sources"][0]["source"] == "rag_notes.txt"
    assert body["conversation_title"]            # first message sets a title

    # the retrieved document really reached the model
    assert "Retrieval augmented generation first retrieves" in answer_ai.prompts[0]

    # persisted
    saved = client.get(f"/conversations/{conversation_id}/messages").json()["messages"]
    assert [m["role"] for m in saved] == ["user", "assistant"]
    assert saved[1]["sources"][0]["source"] == "rag_notes.txt"


def test_follow_up_question_uses_conversation_context(
    client, conversation_id, uploaded_doc, answer_ai, context_ai
):
    url = f"/conversations/{conversation_id}/chat"
    client.post(url, json={"query": "What is retrieval augmented generation?"})

    context_ai.reply = "YES\nWhy does retrieval augmented generation use chunks?"
    client.post(url, json={"query": "Why does it use chunks?"})

    last_prompt = answer_ai.prompts[-1]
    assert "BEGIN CONVERSATION CONTEXT" in last_prompt
    assert "What is retrieval augmented generation?" in last_prompt


def test_refusal_answer_does_not_show_unrelated_sources(
    client, conversation_id, uploaded_doc, answer_ai, context_ai
):
    """When the assistant says 'I couldn't find the answer', showing 'Sources: 2'
    under it is misleading (your own unsupported-question screenshot shows this)."""
    answer_ai.reply = REFUSAL_TEXT

    body = client.post(
        f"/conversations/{conversation_id}/chat", json={"query": "What is quantum computing?"}
    ).json()

    assert body["answer"] == REFUSAL_TEXT
    assert body["sources"] == []


def test_chat_reports_rate_limit_to_the_user(
    client, conversation_id, uploaded_doc, answer_ai, context_ai
):
    answer_ai.errors = [rate_limit_error()] * 10

    response = client.post(f"/conversations/{conversation_id}/chat", json={"query": "hello rag"})

    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_unexpected_crash_returns_clean_500_json(client, monkeypatch):
    monkeypatch.setattr(main, "get_documents", lambda: 1 / 0)

    response = client.get("/documents")

    assert response.status_code == 500
    assert "unexpected server error" in response.json()["detail"]


def test_conversation_delete_flow(client, conversation_id):
    assert client.delete(f"/conversations/{conversation_id}").status_code == 200
    assert client.delete(f"/conversations/{conversation_id}").status_code == 404


# ------------------------------ titles ----------------------------------------

def test_conversation_title_is_short_and_tidy():
    assert main.create_conversation_title("What is RAG?") == "RAG"
    long_title = main.create_conversation_title("Explain " + "very " * 30 + "long question")
    assert len(long_title) <= 48 and long_title.endswith("...")
