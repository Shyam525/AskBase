"""Text and structural metadata extractor for plain text, Markdown, and PDF."""

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from askbase.core.errors import BadRequestError


@dataclass(frozen=True)
class ExtractedPassage:
    """A segment of text accompanied by provenance location."""

    text: str
    page_number: int | None
    section_heading: str | None


@dataclass(frozen=True)
class ExtractedDocument:
    """The aggregate extracted document with structural passages."""

    full_text: str
    page_count: int
    char_count: int
    passages: list[ExtractedPassage]


def extract_plain_text(content: bytes) -> ExtractedDocument:
    """Extract text from plain text files."""
    text = content.decode("utf-8").strip()
    return ExtractedDocument(
        full_text=text,
        page_count=1,
        char_count=len(text),
        passages=[
            ExtractedPassage(
                text=text,
                page_number=1,
                section_heading=None,
            )
        ]
        if text
        else [],
    )


def extract_markdown(content: bytes) -> ExtractedDocument:
    """Extract text and preserve heading sections from Markdown files."""
    text = content.decode("utf-8")
    lines = text.splitlines()

    passages: list[ExtractedPassage] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match:
            # Flush preceding section
            block = "\n".join(current_lines).strip()
            if block:
                passages.append(
                    ExtractedPassage(
                        text=block,
                        page_number=1,
                        section_heading=current_heading,
                    )
                )
                current_lines = []
            current_heading = match.group(2).strip()
        else:
            current_lines.append(line)

    # Flush final section
    block = "\n".join(current_lines).strip()
    if block:
        passages.append(
            ExtractedPassage(
                text=block,
                page_number=1,
                section_heading=current_heading,
            )
        )

    full_text = text.strip()
    return ExtractedDocument(
        full_text=full_text,
        page_count=1,
        char_count=len(full_text),
        passages=passages,
    )


def extract_pdf(content: bytes) -> ExtractedDocument:
    """Extract text and page numbers from PDF files using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as e:
                raise BadRequestError("Encrypted PDF cannot be read without a password.") from e

        passages: list[ExtractedPassage] = []
        page_texts: list[str] = []
        page_count = len(reader.pages)

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            extracted = page.extract_text() or ""
            clean_page_text = extracted.strip()
            if clean_page_text:
                page_texts.append(clean_page_text)
                passages.append(
                    ExtractedPassage(
                        text=clean_page_text,
                        page_number=page_num,
                        section_heading=f"Page {page_num}",
                    )
                )

        full_text = "\n\n".join(page_texts).strip()
        return ExtractedDocument(
            full_text=full_text,
            page_count=max(page_count, 1),
            char_count=len(full_text),
            passages=passages,
        )
    except PdfReadError as e:
        raise BadRequestError(f"Corrupt or unreadable PDF: {e}") from e
    except Exception as e:
        if isinstance(e, BadRequestError):
            raise
        raise BadRequestError(f"Failed to extract PDF contents: {e}") from e


def extract_content(content: bytes, file_extension: str) -> ExtractedDocument:
    """Dispatch extraction by verified file extension."""
    ext = file_extension.lower()
    if ext == ".txt":
        return extract_plain_text(content)
    elif ext == ".md":
        return extract_markdown(content)
    elif ext == ".pdf":
        return extract_pdf(content)
    else:
        raise BadRequestError(f"Unsupported extraction format '{file_extension}'.")
