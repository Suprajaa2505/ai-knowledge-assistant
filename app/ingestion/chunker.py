import re

from langchain_text_splitters import RecursiveCharacterTextSplitter


MAX_SECTION_SIZE = 1200

SECTION_PATTERNS = [
    re.compile(r"(?m)^(?=\d+\.\s+.+$)"),
    re.compile(r"(?m)^(?=\d+\.\d+\s+.+$)"),
    re.compile(r"(?mi)^(?=chapter\s+\d+[:.\s].*$)"),
    re.compile(r"(?mi)^(?=section\s+\d+[:.\s].*$)"),
    re.compile(r"(?m)^(?=#{1,6}\s+.+$)")
]


def split_text(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    return splitter.split_text(text)


def split_into_sections(text):
    for pattern in SECTION_PATTERNS:
        if pattern.search(text):
            sections = pattern.split(text)

            sections = [
                section.strip()
                for section in sections
                if section.strip()
            ]

            if len(sections) > 1:
                return sections

    return [text.strip()]


def split_large_section(section):
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", section)
        if paragraph.strip()
    ]

    if len(paragraphs) > 1:
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            candidate = (
                f"{current_chunk}\n\n{paragraph}"
                if current_chunk
                else paragraph
            )

            if len(candidate) <= MAX_SECTION_SIZE:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                if len(paragraph) <= MAX_SECTION_SIZE:
                    current_chunk = paragraph
                else:
                    current_chunk = ""

                    fallback_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=500,
                        chunk_overlap=100
                    )

                    chunks.extend(
                        fallback_splitter.split_text(paragraph)
                    )

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    return fallback_splitter.split_text(section)


def split_pages(pages):
    chunks = []

    for page in pages:
        text = page["text"].strip()

        sections = split_into_sections(text)

        for section in sections:
            if len(section) <= MAX_SECTION_SIZE:
                chunks.append({
                    "text": section,
                    "page": page["page"]
                })

            else:
                section_chunks = split_large_section(section)

                for chunk in section_chunks:
                    chunks.append({
                        "text": chunk,
                        "page": page["page"]
                    })

    return chunks