"""Base interfaces for job sources."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Protocol, Sequence


@dataclass(slots=True)
class JobQuery:
    """Search query parameters passed to job sources."""

    keywords: Sequence[str]
    location: Optional[str] = None
    remote_only: bool = False
    posted_within_days: Optional[int] = None

    def to_keywords(self) -> str:
        """Return a keyword string for HTTP APIs."""
        return " ".join(self.keywords)


@dataclass(slots=True)
class JobPosting:
    """Representation of a job returned by a source."""

    id: str
    title: str
    company: str
    location: str
    url: str
    source: str
    published_at: datetime
    apply_url: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    tags: Sequence[str] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)


class JobSource(Protocol):
    """Protocol for job sources."""

    name: str

    def search(self, query: JobQuery, limit: int = 20) -> Iterable[JobPosting]:
        """Return a sequence of job postings matching the query."""


def filter_jobs_by_age(
    jobs: Iterable[JobPosting], max_age_days: Optional[int]
) -> List[JobPosting]:
    """Filter jobs by their published date."""
    if max_age_days is None:
        return list(jobs)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return [job for job in jobs if job.published_at >= cutoff]
