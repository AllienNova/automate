from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pypdf import PdfWriter

from autoapply.agent import AutoApplyAgent
from autoapply.config import (
    AgentConfig,
    AutomationSettings,
    JobSearchPreferences,
    ResumeConfig,
    UserProfile,
)
from autoapply.job_sources.base import JobPosting, JobQuery


class FakeJobSource:
    name = "fake"

    def __init__(self, jobs):
        self._jobs = jobs

    def search(self, query: JobQuery, limit: int = 20):
        return self._jobs


class FakeAutomationContext:
    def __init__(self):
        self.calls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def apply_to_job(self, job: JobPosting, user: UserProfile, resume_path: Path):
        self.calls.append(job.id)
        return True, "submitted"


@pytest.mark.asyncio
async def test_agent_ranks_jobs_and_respects_limit(tmp_path):
    resume_path = tmp_path / "resume.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with resume_path.open("wb") as fh:
        writer.write(fh)

    config = AgentConfig(
        user=UserProfile(
            full_name="Alex Candidate",
            email="alex@example.com",
            skills=["python", "automation"],
        ),
        resume=ResumeConfig(path=resume_path),
        search=JobSearchPreferences(
            keywords=["python", "automation"],
            locations=[],
            remote_only=False,
            max_age_days=3,
            freshness_buckets=[1, 3],
            limit_per_bucket=10,
        ),
        automation=AutomationSettings(
            headless=True,
            wait_after_navigation=0.0,
            max_attempts_per_job=1,
            cooldown_between_jobs=0.0,
        ),
    )

    now = datetime.now(timezone.utc)
    jobs = [
        JobPosting(
            id="job-1",
            title="Python Automation Engineer",
            company="Automation Inc",
            location="Remote",
            url="https://example.com/job-1",
            source="fake",
            published_at=now - timedelta(hours=1),
            description="We need an automation expert with Python skills",
            tags=["Python", "Automation"],
        ),
        JobPosting(
            id="job-2",
            title="Data Analyst",
            company="DataWorks",
            location="Remote",
            url="https://example.com/job-2",
            source="fake",
            published_at=now - timedelta(hours=2),
            description="Analyse data",
            tags=["SQL"],
        ),
    ]

    fake_context = FakeAutomationContext()

    def automation_factory(_config: AgentConfig):
        return fake_context

    agent = AutoApplyAgent(
        config=config,
        job_sources=[FakeJobSource(jobs)],
        automation_factory=automation_factory,
        resume_text="Python automation specialist",
    )

    results = await agent.apply(limit=1)

    assert len(results) == 1
    assert results[0].job.id == "job-1"
    assert fake_context.calls == ["job-1"]
