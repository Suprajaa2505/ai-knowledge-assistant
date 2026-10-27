def calculate_precision_at_k(retrieved_chunks, relevant_chunks, k):
    retrieved_at_k = retrieved_chunks[:k]

    if not retrieved_at_k:
        return 0.0

    relevant_count = sum(
        chunk in relevant_chunks
        for chunk in retrieved_at_k
    )

    return relevant_count / len(retrieved_at_k)


def calculate_recall_at_k(retrieved_chunks, relevant_chunks, k):
    retrieved_at_k = retrieved_chunks[:k]

    if not relevant_chunks:
        return 0.0

    relevant_retrieved_count = sum(
        chunk in relevant_chunks
        for chunk in retrieved_at_k
    )

    return relevant_retrieved_count / len(relevant_chunks)


def calculate_mrr(retrieved_chunks, relevant_chunks):
    if not relevant_chunks:
        return 0.0

    for rank, chunk in enumerate(retrieved_chunks, start=1):
        if chunk in relevant_chunks:
            return 1 / rank

    return 0.0