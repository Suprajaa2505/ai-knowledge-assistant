from app.embeddings.embedder import create_embeddings
from app.vectorstore.chroma import collection


def retrieve_documents(query, top_k=3, document_id=None, include_distances=False):
    query_embedding = create_embeddings([query])[0]

    where = None

    if document_id:
        where = {
            "document_id": document_id
        }

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if include_distances:
        return documents, metadatas, distances

    return documents, metadatas