"""Score job matches against a resume profile."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

from .job_sources import JobPosting

_STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "have",
    "your",
    "will",
    "into",
    "such",
    "into",
    "into",
}


@dataclass
class JobScore:
    job: JobPosting
    skills_overlap: float
    keyword_overlap: float
    composite: float


class ResumeScorer:
    """Simple scorer that compares resume tokens with job descriptions."""

    def __init__(self, resume_text: str, skills: Sequence[str] | None = None) -> None:
        tokens = self._tokenise(resume_text)
        self.resume_counts = Counter(tokens)
        self.skills = {skill.lower() for skill in skills or []}

    def _tokenise(self, text: str) -> Iterable[str]:
        words = [word.strip().lower() for word in text.split()]
        return [word for word in words if word and word not in _STOP_WORDS]

    def score(self, job: JobPosting) -> JobScore:
        text_parts = [job.title, job.description or "", " ".join(job.tags)]
        tokens = list(self._tokenise(" ".join(text_parts)))
        job_counts = Counter(tokens)
        intersection = sum(min(job_counts[token], self.resume_counts[token]) for token in job_counts)
        resume_total = sum(self.resume_counts.values()) or 1
        keyword_overlap = intersection / resume_total
        skills_overlap = 0.0
        if self.skills:
            job_tokens = set(tokens)
            skills_overlap = len(job_tokens & self.skills) / max(len(self.skills), 1)
        composite = (keyword_overlap * 0.7) + (skills_overlap * 0.3)
        return JobScore(
            job=job,
            skills_overlap=skills_overlap,
            keyword_overlap=keyword_overlap,
            composite=composite,
        )
