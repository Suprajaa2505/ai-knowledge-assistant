import pymupdf


def load_text_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    return text


def load_pdf(file_path):
    document = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text()

        pages.append({
            "page": page_number,
            "text": text
        })

    document.close()

    return pages