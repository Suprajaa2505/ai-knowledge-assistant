def build_context(documents, metadatas):
    context_parts = []

    for document, metadata in zip(documents, metadatas):
        source = metadata["source"]
        page = metadata.get("page")

        if page is not None:
            source_info = f"{source} — Page {page}"
        else:
            source_info = source

        context_parts.append(
            f"""
--- Source ---
Document: {source}
Location: {source_info}

Content:
{document}
"""
        )

    return "\n".join(context_parts)