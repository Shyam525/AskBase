"""Document chunking strategies preserving structural and page provenance."""

from dataclasses import dataclass

from askbase.ingestion.extractor import ExtractedPassage


@dataclass(frozen=True)
class RawChunk:
    """A bounded segment of searchable text with location provenance."""

    chunk_index: int
    text: str
    char_count: int
    page_number: int | None
    section_heading: str | None


def chunk_text(
    passages: list[ExtractedPassage],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[RawChunk]:
    """Chunk passages into overlapping segments honoring word boundaries and location provenance.

    Strategy:
    1. Iterates over structured passages (each having known section or page context).
    2. If a passage is within `chunk_size`, it is preserved as an atomic chunk.
    3. If larger than `chunk_size`, a sliding window of `chunk_size` characters with
       `chunk_overlap` is applied, snapping boundaries to whitespace to avoid severed words.
    4. Each output chunk retains the page number and section heading of its source passage.
    """
    if chunk_size <= 0:
        chunk_size = 500
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        chunk_overlap = min(50, chunk_size // 4)

    raw_chunks: list[RawChunk] = []
    chunk_counter = 0

    for passage in passages:
        text = passage.text.strip()
        if not text:
            continue

        if len(text) <= chunk_size:
            raw_chunks.append(
                RawChunk(
                    chunk_index=chunk_counter,
                    text=text,
                    char_count=len(text),
                    page_number=passage.page_number,
                    section_heading=passage.section_heading,
                )
            )
            chunk_counter += 1
            continue

        # Split passage using overlapping sliding window with word snapping
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # Snap end to nearest space if we're not at the very end of the string
            if end < text_len:
                space_idx = text.rfind(" ", start + (chunk_size // 2), end)
                if space_idx != -1:
                    end = space_idx

            chunk_content = text[start:end].strip()
            if chunk_content:
                raw_chunks.append(
                    RawChunk(
                        chunk_index=chunk_counter,
                        text=chunk_content,
                        char_count=len(chunk_content),
                        page_number=passage.page_number,
                        section_heading=passage.section_heading,
                    )
                )
                chunk_counter += 1

            if end >= text_len:
                break

            # Advance window with overlap, snapping start to whitespace
            start = max(start + 1, end - chunk_overlap)
            while start < text_len and text[start].isspace():
                start += 1

    return raw_chunks
