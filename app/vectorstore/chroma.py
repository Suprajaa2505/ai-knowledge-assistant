import chromadb


client = chromadb.PersistentClient(
    path="./chroma_db"
)


collection = client.get_or_create_collection(
    name="knowledge_base"
)


def add_documents(chunks, embeddings, document_id, source):
    ids = [
        f"{document_id}-{i}"
        for i in range(len(chunks))
    ]

    metadatas = []

    for i, chunk in enumerate(chunks):
        metadata = {
        "document_id": document_id,
        "source": source,
        "chunk_index": i
    }

        if chunk["page"] is not None:
            metadata["page"] = chunk["page"]

        metadatas.append(metadata)

    

    documents = [
        chunk["text"]
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
def delete_documents_by_document_id(document_id):
    collection.delete(
        where={
            "document_id": document_id
        }
    )