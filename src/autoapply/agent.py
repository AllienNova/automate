"""Orchestrates job discovery and automated applications."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, List, Optional, Sequence

from .config import AgentConfig, AutomationSettings, UserProfile
from .job_sources import JobPosting, JobQuery, JobSource
from .scoring import JobScore, ResumeScorer
from .utils.resume_loader import load_resume_text


@dataclass
class ApplicationResult:
    """Outcome of a single automated application attempt."""

    job: JobPosting
    success: bool
    attempts: int
    message: str = ""


class AutoApplyAgent:
    """High level interface for the auto-apply workflow."""

    def __init__(
        self,
        config: AgentConfig,
        job_sources: Sequence[JobSource],
        automation_factory: Optional[Callable[[AgentConfig], "AutomationRunner"]] = None,
        resume_text: Optional[str] = None,
    ) -> None:
        self.config = config
        self.job_sources = list(job_sources)
        self.automation_factory = automation_factory or (
            lambda cfg: AutomationRunner(cfg.automation)
        )
        self._resume_text = resume_text
        self._scorer: Optional[ResumeScorer] = None
        self._applied_ids: set[str] = set()

    @property
    def resume_text(self) -> str:
        if self._resume_text is None:
            self._resume_text = load_resume_text(
                self.config.resume.path, self.config.resume.parsed_text_cache
            )
        return self._resume_text

    @property
    def scorer(self) -> ResumeScorer:
        if self._scorer is None:
            self._scorer = ResumeScorer(self.resume_text, skills=self.config.user.skills)
        return self._scorer

    def discover_jobs(self) -> List[JobPosting]:
        """Collect jobs from all sources respecting freshness buckets."""
        all_jobs: dict[str, JobPosting] = {}
        search_prefs = self.config.search
        locations = list(search_prefs.locations) or [None]
        excluded_companies = {company.lower() for company in search_prefs.exclude_companies}
        for bucket in search_prefs.freshness_buckets:
            effective_age = min(bucket, search_prefs.max_age_days)
            for location in locations:
                query = JobQuery(
                    keywords=search_prefs.keywords,
                    location=location,
                    remote_only=search_prefs.remote_only,
                    posted_within_days=effective_age,
                )
                for source in self.job_sources:
                    try:
                        jobs = source.search(query, limit=search_prefs.limit_per_bucket)
                    except Exception as exc:  # pragma: no cover - network error path
                        print(f"Failed to fetch jobs from {source.name}: {exc}")
                        continue
                    for job in jobs:
                        if job.id in all_jobs:
                            continue
                        company_name = (job.company or "").lower()
                        if company_name in excluded_companies:
                            continue
                        if not self._is_within_age(job, search_prefs.max_age_days):
                            continue
                        all_jobs[job.id] = job
        return list(all_jobs.values())

    def _is_within_age(self, job: JobPosting, max_age: Optional[int]) -> bool:
        if max_age is None:
            return True
        now = datetime.now(timezone.utc)
        published = job.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return (now - published).days <= max_age

    def rank_jobs(self, jobs: Iterable[JobPosting]) -> List[JobScore]:
        scores = [self.scorer.score(job) for job in jobs]
        scores.sort(key=lambda score: (score.composite, score.job.published_at), reverse=True)
        return scores

    async def apply(self, limit: Optional[int] = None) -> List[ApplicationResult]:
        jobs = self.rank_jobs(self.discover_jobs())
        results: List[ApplicationResult] = []
        if not jobs:
            return results
        async with self.automation_factory(self.config) as automation:
            for index, score in enumerate(jobs):
                if limit is not None and index >= limit:
                    break
                job = score.job
                if job.id in self._applied_ids:
                    continue
                attempts = 0
                success = False
                message = ""
                while attempts < self.config.automation.max_attempts_per_job and not success:
                    attempts += 1
                    success, message = await automation.apply_to_job(
                        job, self.config.user, self.config.resume.path
                    )
                    if not success:
                        await asyncio.sleep(0.5)
                self._applied_ids.add(job.id)
                results.append(
                    ApplicationResult(job=job, success=success, attempts=attempts, message=message)
                )
                await asyncio.sleep(self.config.automation.cooldown_between_jobs)
        return results


class AutomationRunner:
    """Thin wrapper around the browser automation implementation."""

    def __init__(self, settings: AutomationSettings):
        from .browser.automation import BrowserAutomation

        self.settings = settings
        self._automation = BrowserAutomation(settings=settings)

    async def __aenter__(self) -> "AutomationRunner":
        await self._automation.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._automation.__aexit__(exc_type, exc, tb)

    async def apply_to_job(self, job: JobPosting, user: UserProfile, resume_path) -> tuple[bool, str]:
        return await self._automation.apply_to_job(job, user, resume_path)
