
from io import BytesIO

from pypdf import PdfReader
from docx import Document


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from a PDF resume.
    """

    if not file_bytes:
        raise ValueError("PDF file is empty")

    try:
        pdf_reader = PdfReader(
            BytesIO(file_bytes)
        )

        extracted_text = []

        for page in pdf_reader.pages:

            page_text = page.extract_text()

            if page_text:
                extracted_text.append(
                    page_text
                )

        final_text = "\n".join(
            extracted_text
        ).strip()

        if not final_text:
            raise ValueError(
                "No readable text found in PDF"
            )

        return final_text

    except Exception as e:
        raise ValueError(
            f"Failed to extract PDF text: {e}"
        )


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from a DOCX resume.
    """

    if not file_bytes:
        raise ValueError("DOCX file is empty")

    try:
        document = Document(
            BytesIO(file_bytes)
        )

        extracted_text = []

        for paragraph in document.paragraphs:

            paragraph_text = (
                paragraph.text.strip()
            )

            if paragraph_text:
                extracted_text.append(
                    paragraph_text
                )

        final_text = "\n".join(
            extracted_text
        ).strip()

        if not final_text:
            raise ValueError(
                "No readable text found in DOCX"
            )

        return final_text

    except Exception as e:
        raise ValueError(
            f"Failed to extract DOCX text: {e}"
        )


def extract_resume_text(
    file_bytes: bytes,
    content_type: str
) -> str:
    """
    Detect the resume file type and extract text.
    """

    if content_type == "application/pdf":

        return extract_text_from_pdf(
            file_bytes
        )

    if (
        content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):

        return extract_text_from_docx(
            file_bytes
        )

    raise ValueError(
        "Unsupported resume file type"
    )
