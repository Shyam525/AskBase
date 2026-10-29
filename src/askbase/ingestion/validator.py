"""File upload validation, format verification, and safe storage path generation."""

import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from askbase.core.errors import BadRequestError


@dataclass(frozen=True)
class ValidatedFile:
    """Metadata and safe attributes for an ingested binary."""

    original_filename: str
    file_size_bytes: int
    mime_type: str
    content_hash: str
    safe_filename: str
    file_extension: str


def sanitize_filename(filename: str) -> str:
    """Strip dangerous directory separators and non-printable characters."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^\w\s.-]", "_", base)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or "document"


def compute_sha256(content: bytes) -> str:
    """Compute cryptographic SHA-256 digest."""
    return hashlib.sha256(content).hexdigest()


def validate_file_upload(
    content: bytes,
    filename: str,
    max_size_bytes: int = 20 * 1024 * 1024,
) -> ValidatedFile:
    """Validate uploaded binary for size limits, safe naming, and content magic bytes.

    Guarantees path traversal prevention and handles corrupt payloads safely.
    """
    if not content:
        raise BadRequestError("Uploaded file is empty.")

    file_size = len(content)
    if file_size > max_size_bytes:
        raise BadRequestError(
            f"File size ({file_size} bytes) exceeds maximum permitted limit ({max_size_bytes} bytes)."
        )

    clean_name = sanitize_filename(filename)
    ext = Path(clean_name).suffix.lower()

    if ext not in {".txt", ".md", ".pdf"}:
        raise BadRequestError(
            f"Unsupported file format '{ext}'. AskBase supports .txt, .md, and .pdf files."
        )

    # Magic bytes and content inspection (do not trust client MIME type)
    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise BadRequestError(
                "Malformed file: file claims to be PDF but lacks valid PDF header signature."
            )
        mime_type = "application/pdf"
    elif ext in {".txt", ".md"}:
        if b"\x00" in content:
            raise BadRequestError("Malformed file: text file contains binary null bytes.")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise BadRequestError(
                "Malformed text file: file contains invalid non-UTF-8 characters."
            ) from e
        mime_type = "text/markdown" if ext == ".md" else "text/plain"
    else:
        mime_type = "application/octet-stream"

    content_hash = compute_sha256(content)
    # Generate an un-guessable, collision-free server storage name
    safe_filename = f"{uuid.uuid4().hex}_{clean_name}"

    return ValidatedFile(
        original_filename=clean_name,
        file_size_bytes=file_size,
        mime_type=mime_type,
        content_hash=content_hash,
        safe_filename=safe_filename,
        file_extension=ext,
    )
