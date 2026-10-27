from pathlib import Path

from app.ingestion.loader import load_pdf, load_text_file
from app.ingestion.chunker import split_text, split_pages
from app.embeddings.embedder import create_embeddings
from app.vectorstore.chroma import (
    add_documents,
    delete_documents_by_document_id
)


def _prepare_chunks(file_path):
    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        pages = load_pdf(file_path)

        if not any(page["text"].strip() for page in pages):
             raise ValueError("The document contains no extractable text.")
             
        page_chunks = split_pages(pages)

        chunks = [
            {
                "text": chunk["text"],
                "page": chunk["page"]
            }
            for chunk in page_chunks
        ]

    elif extension == ".txt":
        text = load_text_file(file_path)

        text_chunks = split_text(text)

        chunks = [
            {
                "text": chunk,
                "page": None
            }
            for chunk in text_chunks
        ]

    else:
        raise ValueError(f"Unsupported file type: {extension}")

    return chunks


def index_document(file_path, document_id, source):
    chunks = _prepare_chunks(file_path)

    texts = [chunk["text"] for chunk in chunks]

    embeddings = create_embeddings(texts)

    add_documents(
        chunks=chunks,
        embeddings=embeddings,
        document_id=document_id,
        source=source
    )


def reindex_document(file_path, document_id, source):
    chunks = _prepare_chunks(file_path)

    texts = [chunk["text"] for chunk in chunks]

    embeddings = create_embeddings(texts)

    delete_documents_by_document_id(document_id)

    add_documents(
        chunks=chunks,
        embeddings=embeddings,
        document_id=document_id,
        source=source
    )