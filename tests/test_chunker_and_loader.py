"""Ingestion: real PDF parsing (PyMuPDF) and the real chunker."""
import pymupdf

from app.ingestion.chunker import MAX_SECTION_SIZE, split_into_sections, split_pages
from app.ingestion.loader import load_pdf
from app.ingestion.indexer import _prepare_chunks


def make_pdf(path, page_texts):
    """Build a real PDF. An empty string makes a blank page."""
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_textbox(pymupdf.Rect(72, 72, 520, 700), text)
    document.save(str(path))
    document.close()


def test_pdf_pages_are_loaded_with_page_numbers(tmp_path):
    pdf = tmp_path / "two_pages.pdf"
    make_pdf(pdf, ["Cats purr.", "Dogs bark."])

    pages = load_pdf(str(pdf))

    assert [p["page"] for p in pages] == [1, 2]
    assert "Cats" in pages[0]["text"]
    assert "Dogs" in pages[1]["text"]


def test_chunks_keep_the_page_they_came_from(tmp_path):
    pdf = tmp_path / "doc.pdf"
    make_pdf(pdf, ["Page one is about cats.", "Page two is about dogs."])

    chunks = _prepare_chunks(str(pdf))

    page_of = {c["page"]: c["text"] for c in chunks}
    assert "cats" in page_of[1]
    assert "dogs" in page_of[2]


def test_blank_pdf_page_does_not_create_an_empty_chunk(tmp_path):
    """An empty chunk would be sent to the embedding API and can make the
    whole upload fail. Blank / image-only pages are common in real PDFs."""
    pdf = tmp_path / "with_blank.pdf"
    make_pdf(pdf, ["First page text.", "", "Third page text."])

    chunks = _prepare_chunks(str(pdf))

    assert all(chunk["text"].strip() for chunk in chunks)
    assert [c["page"] for c in chunks] == [1, 3]


def test_numbered_sections_are_split():
    text = "1. Introduction\nSome intro.\n2. Methods\nSome methods."

    sections = split_into_sections(text)

    assert len(sections) == 2
    assert sections[0].startswith("1. Introduction")
    assert sections[1].startswith("2. Methods")


def test_text_without_headings_stays_in_one_section():
    assert split_into_sections("just a plain paragraph") == ["just a plain paragraph"]


def test_long_section_is_split_into_bounded_chunks():
    paragraph = "word " * 100                       # ~500 characters
    long_section = "\n\n".join([paragraph] * 10)     # ~5000 characters

    chunks = split_pages([{"page": 7, "text": long_section}])

    assert len(chunks) > 1
    assert all(len(c["text"]) <= MAX_SECTION_SIZE for c in chunks)
    assert all(c["page"] == 7 for c in chunks)


def test_txt_file_has_no_page_numbers(tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("Some plain text notes. " * 50, encoding="utf-8")

    chunks = _prepare_chunks(str(txt))

    assert chunks and all(c["page"] is None for c in chunks)


def test_unsupported_extension_is_rejected(tmp_path):
    import pytest
    bad = tmp_path / "virus.exe"
    bad.write_bytes(b"x")

    with pytest.raises(ValueError):
        _prepare_chunks(str(bad))
