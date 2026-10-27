from pathlib import Path
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.database import (
    initialize_database,
    create_conversation,
    conversation_exists,
    delete_conversation,
    get_conversations,
    create_document,
    get_document,
    get_documents,
    delete_document,
    add_message,
    get_messages,
    get_recent_messages,
    update_conversation_title
)

from app.gemini_service import GeminiServiceError
from app.generation.generator import generate_answer
from app.ingestion.indexer import index_document
from app.retrieval.contextualizer import contextualize_query
from app.retrieval.retriever import retrieve_documents
from app.vectorstore.chroma import delete_documents_by_document_id
from app.retrieval.context_builder import build_context

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

initialize_database()

class ConversationRequest(BaseModel):
    title: str = "New Conversation"

class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    document_id: str | None = None

UPLOAD_DIR = Path("documents")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS={".pdf",".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected server error occurred. Please try again later."
        }
    )

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required."
        )

    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are allowed."
        )

    document_id = str(uuid.uuid4())

    stored_filename = f"{document_id}{file_extension}"
    file_path = UPLOAD_DIR / stored_filename

    try:
        contents = await file.read()

        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File size must be 10 MB or less."
            )

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        with open(file_path, "wb") as output_file:
            output_file.write(contents)

        create_document(
            document_id=document_id,
            filename=file.filename,
            file_type=file_extension,
            file_size=len(contents)
        )

        index_document(
            file_path=str(file_path),
            document_id=document_id,
            source=file.filename
        )

    except HTTPException:
        if file_path.exists():
            file_path.unlink()

        raise

    except GeminiServiceError as error:
        if file_path.exists():
            file_path.unlink()

        delete_document(document_id)
        delete_documents_by_document_id(document_id)

        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    except Exception:
        if file_path.exists():
            file_path.unlink()

        delete_document(document_id)
        delete_documents_by_document_id(document_id)

        raise HTTPException(
            status_code=500,
            detail="The document could not be processed. Please try again."
        )

    return {
        "status": "success",
        "document_id": document_id,
        "filename": file.filename,
        "message": "Document uploaded and indexed successfully."
    }

@app.post("/conversations")
def create_new_conversation(request: ConversationRequest):
    conversation_id = create_conversation(request.title)

    return {
        "conversation_id": conversation_id,
        "title": request.title
    }
@app.get("/conversations")
def list_conversations():
    conversations = get_conversations()

    return {
        "conversations": conversations
    }

@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str):
    if not conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    messages = get_messages(conversation_id)

    return {
        "conversation_id": conversation_id,
        "messages": messages
    }
def create_conversation_title(query):
    title = " ".join(query.strip().split())

    # Common question patterns
    prefixes = [
        "what is ",
        "what are ",
        "how does ",
        "how do ",
        "why is ",
        "why are ",
        "why did ",
        "can you explain ",
        "explain ",
    ]

    lower_title = title.lower()

    for prefix in prefixes:
        if lower_title.startswith(prefix):
            title = title[len(prefix):].strip()
            break

    # Remove trailing question mark
    title = title.rstrip("?.!")

    # Common short forms that should stay uppercase
    replacements = {
        "rag": "RAG",
        "llm": "LLM",
        "llms": "LLMs",
        "ai": "AI",
        "api": "API",
        "apis": "APIs",
        "ml": "ML",
        "nlp": "NLP",
        "cnn": "CNN",
        "rnns": "RNNs",
        "rnn": "RNN",
    }

    words = title.split()

    formatted_words = []

    for word in words:
        key = word.lower().strip(".,!?")

        if key in replacements:
            formatted_words.append(replacements[key])
        else:
            formatted_words.append(word)

    title = " ".join(formatted_words)

    # If the title is still too long, shorten it
    if len(title) > 45:
        title = title[:45].rsplit(" ", 1)[0] + "..."

    return title 
@app.post("/conversations/{conversation_id}/chat")
def chat(
    conversation_id: str,
    request: ChatRequest
):
    if not conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    recent_messages = get_recent_messages(
        conversation_id=conversation_id,
        limit=2
    )

    is_first_message = len(recent_messages) == 0

    try:
        contextualized_query, needs_context = contextualize_query(
            query=request.query,
            recent_messages=recent_messages
        )
    except GeminiServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    conversation_context = None

    if needs_context:
        conversation_context = "\n".join(
            f'{message["role"].capitalize()}: {message["content"]}'
            for message in recent_messages
        )

    try:
        documents, metadatas = retrieve_documents(
            query=contextualized_query,
            top_k=request.top_k,
            document_id=request.document_id
        )
    except GeminiServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    combined_context = build_context(
        documents,
        metadatas
    )

    try:
        answer = generate_answer(
            query=request.query,
            context=combined_context,
            conversation_context=conversation_context
        )
    except GeminiServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    sources = []

    for metadata in metadatas:
        page = metadata.get("page")

        citation = metadata["source"]

        if page is not None:
            citation += f" — Page {page}"

        sources.append({
            "document_id": metadata["document_id"],
            "source": metadata["source"],
            "page": page,
            "chunk_index": metadata["chunk_index"],
            "citation": citation
        })

    add_message(
        conversation_id=conversation_id,
        role="user",
        content=request.query
    )

    add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        sources=sources
    )

    conversation_title = None

    if is_first_message:
        conversation_title = create_conversation_title(
            request.query
        )

        update_conversation_title(
            conversation_id=conversation_id,
            title=conversation_title
        )

    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "sources": sources,
        "conversation_title": conversation_title
    }
@app.get("/documents/{document_id}")
def get_document_details(document_id: str):
    document = get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return document

@app.get("/documents")
def list_documents():
    documents = get_documents()

    return {
        "documents": documents
    }

@app.post("/evaluate/retrieval")
def evaluate_retrieval(request: ChatRequest):
    try:
        documents, metadatas, distances = retrieve_documents(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
            include_distances=True
        )
    except GeminiServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    results = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):
        results.append({
            "document": document,
            "metadata": metadata,
            "distance": distance
        })

    return {
        "query": request.query,
        "top_k": request.top_k,
        "results": results
    }

@app.delete("/documents/{document_id}")
def delete_document_endpoint(document_id: str):
    document = get_document(document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    file_extension = document["file_type"]
    file_path = UPLOAD_DIR / f"{document_id}{file_extension}"

    try:
        # Remove the physical file
        if file_path.exists():
            file_path.unlink()

        # Remove the document's chunks from ChromaDB
        delete_documents_by_document_id(document_id)

        # Remove the document record from SQLite
        delete_document(document_id)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The document could not be deleted."
        )

    return {
        "status": "success",
        "document_id": document_id,
        "message": "Document deleted successfully."
    }
@app.delete("/conversations/{conversation_id}")
def delete_conversation_endpoint(conversation_id: str):
    if not conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    try:
        delete_conversation(conversation_id)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The conversation could not be deleted."
        )

    return {
        "status": "success",
        "conversation_id": conversation_id,
        "message": "Conversation deleted successfully."
    }
