"""Auto-apply agent package."""

from .agent import AutoApplyAgent, ApplicationResult
from .config import AgentConfig, JobSearchPreferences, UserProfile

__all__ = [
    "AgentConfig",
    "JobSearchPreferences",
    "UserProfile",
    "AutoApplyAgent",
    "ApplicationResult",
]
