"""Utilities for loading and caching resume information."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pypdf import PdfReader


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF resume."""
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def load_resume_text(resume_path: Path, cache_path: Optional[Path] = None) -> str:
    """Load resume text using a cache if provided."""
    if cache_path and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    text = extract_text_from_pdf(resume_path)
    if cache_path:
        cache_path.write_text(text, encoding="utf-8")
    return text
