"""Configuration models for the auto apply agent."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

from pydantic import BaseModel, Field, field_validator


class ResumeConfig(BaseModel):
    """Configuration for the candidate resume."""

    path: Path = Field(..., description="Path to the resume PDF file")
    parsed_text_cache: Optional[Path] = Field(
        None, description="Optional cache file for storing extracted resume text"
    )

    @field_validator("path")
    @classmethod
    def _check_path(cls, value: Path) -> Path:  # noqa: D401
        """Ensure the resume path exists."""
        if not value.exists():
            raise ValueError(f"Resume file does not exist: {value}")
        if value.suffix.lower() != ".pdf":
            raise ValueError("Resume file must be a PDF")
        return value


class JobSearchPreferences(BaseModel):
    """Preferences used to discover and filter job postings."""

    keywords: Sequence[str]
    locations: Sequence[str] = Field(default_factory=list)
    remote_only: bool = False
    max_age_days: int = 7
    freshness_buckets: Sequence[int] = Field(
        default_factory=lambda: [1, 3, 7],
        description="List of rolling time windows (in days) to prioritise more recent jobs.",
    )
    limit_per_bucket: int = 25
    exclude_companies: Sequence[str] = Field(default_factory=list)

    @field_validator("freshness_buckets")
    @classmethod
    def _validate_buckets(cls, value: Sequence[int]) -> Sequence[int]:
        if not value:
            raise ValueError("freshness_buckets must contain at least one value")
        if any(v <= 0 for v in value):
            raise ValueError("freshness_buckets must only contain positive integers")
        return sorted(set(value))


class AutomationSettings(BaseModel):
    """Settings for the browser automation component."""

    headless: bool = True
    wait_after_navigation: float = Field(2.0, ge=0.0)
    max_attempts_per_job: int = Field(3, ge=1)
    cooldown_between_jobs: float = Field(1.0, ge=0.0)


class UserProfile(BaseModel):
    """Information about the candidate used for personalisation."""

    full_name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list, description="Portfolio or social links")


class AgentConfig(BaseModel):
    """Top level configuration for the agent."""

    user: UserProfile
    resume: ResumeConfig
    search: JobSearchPreferences
    automation: AutomationSettings = Field(default_factory=AutomationSettings)

    @classmethod
    def from_file(cls, path: Path) -> "AgentConfig":
        """Load configuration from a JSON or YAML file."""
        path = path.expanduser()
        if not path.exists():
            raise FileNotFoundError(path)
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml  # type: ignore
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "YAML support requires the optional 'pyyaml' dependency"
                ) from exc
            data = yaml.safe_load(content)
        else:
            import json

            data = json.loads(content)
        return cls.parse_obj(data)
