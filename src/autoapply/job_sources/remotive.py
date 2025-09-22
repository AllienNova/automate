"""Job source implementation using the public Remotive API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional

import requests
from dateutil import parser

from .base import JobPosting, JobQuery, JobSource


class RemotiveJobSource(JobSource):
    """Fetch job postings from the Remotive public API."""

    name = "remotive"
    api_url = "https://remotive.com/api/remote-jobs"

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self._session = session or requests.Session()

    def search(self, query: JobQuery, limit: int = 20) -> Iterable[JobPosting]:  # noqa: D401
        """Return matching job postings from Remotive."""
        params = {
            "search": query.to_keywords(),
            "limit": limit,
        }
        if query.location:
            params["location"] = query.location
        response = self._session.get(self.api_url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs", [])
        return self._convert_jobs(jobs, query)

    def _convert_jobs(
        self, jobs_payload: List[dict], query: JobQuery
    ) -> List[JobPosting]:
        postings: List[JobPosting] = []
        for job in jobs_payload:
            published = parser.isoparse(job["publication_date"]).astimezone(timezone.utc)
            if (
                query.posted_within_days
                and (datetime.now(timezone.utc) - published).days > query.posted_within_days
            ):
                continue
            location = job.get("candidate_required_location", "Remote")
            if query.remote_only and "remote" not in location.lower():
                continue
            posting = JobPosting(
                id=f"remotive-{job['id']}",
                title=job.get("title", ""),
                company=job.get("company_name", "Unknown"),
                location=location,
                url=job.get("url", ""),
                source=self.name,
                published_at=published,
                apply_url=job.get("url"),
                description=job.get("description"),
                salary=job.get("salary"),
                tags=job.get("tags", []),
                metadata={
                    "job_type": job.get("job_type"),
                    "category": job.get("category"),
                },
            )
            postings.append(posting)
        return postings
