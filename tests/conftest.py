"""Shared test setup.

Goals:
  * Tests are FREE and OFFLINE: Gemini is replaced by a fake, so no API key,
    no network and no quota are used.
  * Tests never touch your real data: everything (app.db, chroma_db/, documents/)
    lives in a throw-away temp folder.
  * Everything else is REAL: real SQLite, real ChromaDB, real FastAPI app,
    real PDF parsing, real chunker.
"""
import hashlib
import os
import re
import tempfile
from types import SimpleNamespace

# --- This block must run BEFORE any `import app...` ---------------------------
# app/config.py reads the key at import time and chromadb/sqlite create their
# files relative to the current folder, so we set both up first.
os.environ["GEMINI_API_KEY"] = "test-key-not-real"   # never use a real key in tests
_SANDBOX = tempfile.mkdtemp(prefix="rag-tests-")
os.chdir(_SANDBOX)
# -------------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient

from app import database, main
from app.generation import generator
from app.retrieval import contextualizer, retriever
from app.ingestion import indexer
from app.embeddings import embedder
from app.vectorstore import chroma


# ---------- fakes -------------------------------------------------------------

def fake_embed(texts):
    """Deterministic 'embedding': hashed bag-of-words, 64 dimensions.

    Texts that share words get similar vectors, so real ChromaDB search still
    returns sensible results - without calling Gemini.
    """
    vectors = []
    for text in texts:
        vector = [0.0] * 64
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
        norm = sum(x * x for x in vector) ** 0.5 or 1.0
        vectors.append([x / norm for x in vector])
    return vectors


class FakeGeminiClient:
    """Stands in for genai.Client. Records prompts, can be told to fail.

    `reply` can be a string, or a function(prompt) -> string."""

    def __init__(self, reply="OK"):
        self.reply = reply
        self.errors = []          # exceptions raised (one per call) before replying
        self.prompts = []
        self.models = self        # so client.models.generate_content(...) works

    def generate_content(self, model=None, contents=None, **kwargs):
        self.prompts.append(contents)
        if self.errors:
            raise self.errors.pop(0)
        text = self.reply(contents) if callable(self.reply) else self.reply
        usage = SimpleNamespace(prompt_token_count=100, candidates_token_count=20,
                                thoughts_token_count=None)
        return SimpleNamespace(text=text, usage_metadata=usage)

    def embed_content(self, model=None, contents=None, **kwargs):
        self.prompts.append(contents)
        if self.errors:
            raise self.errors.pop(0)
        vectors = fake_embed(contents)
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=v) for v in vectors]
        )


# ---------- fixtures ----------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Fresh state before every test + offline embeddings + no real sleeping."""
    # empty the real SQLite tables
    connection = database.get_connection()
    for table in ("messages", "conversations", "documents"):
        connection.execute(f"DELETE FROM {table}")
    connection.commit()
    connection.close()

    # empty the real ChromaDB collection
    ids = chroma.collection.get()["ids"]
    if ids:
        chroma.collection.delete(ids=ids)

    # empty the uploads folder
    for file in main.UPLOAD_DIR.glob("*"):
        file.unlink()

    # offline embeddings everywhere they were imported by name
    monkeypatch.setattr(indexer, "create_embeddings", fake_embed)
    monkeypatch.setattr(retriever, "create_embeddings", fake_embed)

    # retry back-off must not slow the tests down
    from app import gemini_service
    if hasattr(gemini_service, "time"):
        monkeypatch.setattr(gemini_service.time, "sleep", lambda seconds: None)

    yield


@pytest.fixture
def answer_ai(monkeypatch):
    """Fake Gemini used by generate_answer()."""
    fake = FakeGeminiClient(reply="Default answer.")
    monkeypatch.setattr(generator, "client", fake)
    return fake


@pytest.fixture
def context_ai(monkeypatch):
    """Fake Gemini used by contextualize_query(). Default: 'NO' (standalone)."""
    fake = FakeGeminiClient(reply="NO")
    monkeypatch.setattr(contextualizer, "client", fake)
    return fake


@pytest.fixture
def embed_ai(monkeypatch):
    """Fake Gemini used by create_embeddings() (to test its error handling)."""
    fake = FakeGeminiClient()
    monkeypatch.setattr(embedder, "client", fake)
    return fake


@pytest.fixture
def client():
    # raise_server_exceptions=False -> we see the real 500 JSON the user would get
    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def conversation_id(client):
    return client.post("/conversations", json={}).json()["conversation_id"]


@pytest.fixture
def uploaded_doc(client):
    """Uploads a small real .txt document through the real /upload endpoint."""
    text = (
        "Retrieval augmented generation first retrieves relevant chunks from "
        "your documents and then asks the language model to answer using them."
    )
    response = client.post(
        "/upload", files={"file": ("rag_notes.txt", text.encode(), "text/plain")}
    )
    assert response.status_code == 200, response.text
    return response.json()
