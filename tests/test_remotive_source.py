from __future__ import annotations

from datetime import datetime, timedelta, timezone

import responses

from autoapply.job_sources import JobQuery
from autoapply.job_sources.remotive import RemotiveJobSource


@responses.activate
def test_remotive_filters_by_age():
    source = RemotiveJobSource()
    now = datetime.now(timezone.utc)
    old_date = (now - timedelta(days=5)).isoformat()
    fresh_date = (now - timedelta(hours=12)).isoformat()
    responses.add(
        responses.GET,
        "https://remotive.com/api/remote-jobs",
        json={
            "jobs": [
                {
                    "id": 1,
                    "title": "Python Developer",
                    "company_name": "Fresh Corp",
                    "candidate_required_location": "Remote",
                    "publication_date": fresh_date,
                    "url": "https://remotive.com/jobs/1",
                    "description": "Work with Python",
                    "tags": ["Python"],
                },
                {
                    "id": 2,
                    "title": "Old Job",
                    "company_name": "Legacy Corp",
                    "candidate_required_location": "Remote",
                    "publication_date": old_date,
                    "url": "https://remotive.com/jobs/2",
                    "description": "Old listing",
                    "tags": [],
                },
            ]
        },
    )
    query = JobQuery(keywords=["python"], posted_within_days=2)
    results = list(source.search(query, limit=10))
    assert len(results) == 1
    assert results[0].company == "Fresh Corp"
