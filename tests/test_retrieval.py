"""Real ChromaDB + fake (offline) embeddings."""
from app.ingestion.indexer import index_document, reindex_document
from app.retrieval.context_builder import build_context
from app.retrieval.retriever import retrieve_documents
from app.vectorstore.chroma import collection, delete_documents_by_document_id


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_search_returns_the_most_relevant_document(tmp_path):
    cats = write(tmp_path, "cats.txt", "Cats purr and chase mice. Cats sleep a lot.")
    cars = write(tmp_path, "cars.txt", "Engines burn fuel. Cars have four wheels and brakes.")
    index_document(cats, "doc-cats", "cats.txt")
    index_document(cars, "doc-cars", "cars.txt")

    documents, metadatas = retrieve_documents("Why do cats purr?", top_k=1)

    assert metadatas[0]["source"] == "cats.txt"
    assert "purr" in documents[0]


def test_document_filter_only_searches_that_document(tmp_path):
    index_document(write(tmp_path, "a.txt", "Apples are red fruit."), "doc-a", "a.txt")
    index_document(write(tmp_path, "b.txt", "Apples are also green fruit."), "doc-b", "b.txt")

    _, metadatas = retrieve_documents("apples", top_k=5, document_id="doc-b")

    assert {m["document_id"] for m in metadatas} == {"doc-b"}


def test_metadata_is_stored_with_every_chunk(tmp_path):
    index_document(write(tmp_path, "n.txt", "Some notes. " * 100), "doc-n", "n.txt")

    _, metadatas = retrieve_documents("notes", top_k=3)

    for metadata in metadatas:
        assert metadata["source"] == "n.txt"
        assert metadata["document_id"] == "doc-n"
        assert "chunk_index" in metadata


def test_deleting_a_document_removes_its_chunks(tmp_path):
    index_document(write(tmp_path, "x.txt", "temporary content"), "doc-x", "x.txt")
    assert collection.count() > 0

    delete_documents_by_document_id("doc-x")

    assert collection.count() == 0


def test_reindexing_replaces_old_chunks(tmp_path):
    path = write(tmp_path, "r.txt", "old content about bananas")
    index_document(path, "doc-r", "r.txt")
    write(tmp_path, "r.txt", "new content about oranges")

    reindex_document(path, "doc-r", "r.txt")

    documents, _ = retrieve_documents("oranges", top_k=5)
    assert all("bananas" not in d for d in documents)


def test_empty_collection_returns_no_results():
    documents, metadatas = retrieve_documents("anything", top_k=3)

    assert documents == [] and metadatas == []


def test_context_builder_shows_page_for_pdfs_and_not_for_txt():
    text = build_context(
        ["pdf text", "txt text"],
        [{"source": "a.pdf", "page": 4}, {"source": "b.txt"}],
    )

    assert "a.pdf — Page 4" in text
    assert "Location: b.txt" in text
    assert "pdf text" in text and "txt text" in text
