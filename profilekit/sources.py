from __future__ import annotations

from pathlib import Path


MAX_SOURCE_BYTES = 5 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".tsv"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic"}


class SourceError(ValueError):
    pass


def _check_source(path: Path) -> None:
    if not path.is_file():
        raise SourceError(f"Source does not exist or is not a file: {path}")
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise SourceError(f"Source exceeds the 5 MB local limit: {path.name}")


def extract_source(path: Path) -> str:
    """Extract user-selected local content without asserting public-use permission."""
    path = path.expanduser().resolve()
    _check_source(path)
    suffix = path.suffix.lower()

    if suffix in TEXT_SUFFIXES:
        content = path.read_text(encoding="utf-8-sig")
    elif suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        content = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document

        document = Document(path)
        content = "\n".join(paragraph.text for paragraph in document.paragraphs)
    elif suffix in IMAGE_SUFFIXES:
        return (
            f"SOURCE: {path.name}\n"
            "[Image supplied by the user. Do not infer its contents or treat it as "
            "authorized for public use. Record it as authorization needed and offer a "
            "text-only or placeholder option.]"
        )
    else:
        raise SourceError(
            f"Unsupported source type {suffix or '(none)'} for {path.name}. "
            "Use text, Markdown, JSON, YAML, CSV/TSV, PDF, DOCX, or a common image format."
        )

    content = content.strip()
    if not content:
        content = "[No extractable text found. Mark the source as needing confirmation.]"
    return f"SOURCE: {path.name}\n{content}"


def build_source_bundle(paths: list[Path]) -> str:
    if not paths:
        return ""
    extracted = [extract_source(path) for path in paths]
    return (
        "\n\n--- USER-SELECTED SOURCE MATERIALS ---\n"
        "These sources are approved for inspection only, not automatically for public use.\n\n"
        + "\n\n---\n\n".join(extracted)
    )
