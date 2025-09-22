"""Command line interface to run the auto-apply agent."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .agent import AutoApplyAgent
from .config import AgentConfig
from .job_sources import RemotiveJobSource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the auto-apply agent")
    parser.add_argument("config", type=Path, help="Path to the agent configuration file")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of applications")
    parser.add_argument(
        "--source",
        action="append",
        default=["remotive"],
        help="Job sources to use (currently only 'remotive' is implemented)",
    )
    return parser.parse_args()


def create_sources(names: list[str]):
    sources = []
    for name in names:
        if name.lower() == "remotive":
            sources.append(RemotiveJobSource())
        else:
            raise ValueError(f"Unsupported job source: {name}")
    return sources


def main() -> None:
    args = parse_args()
    config = AgentConfig.from_file(args.config)
    sources = create_sources(args.source)
    agent = AutoApplyAgent(config=config, job_sources=sources)

    results = asyncio.run(agent.apply(limit=args.limit))
    if not results:
        print("No applications were submitted.")
        return
    successes = sum(1 for result in results if result.success)
    print(f"Applications attempted: {len(results)}")
    print(f"Successful submissions: {successes}")
    for result in results:
        status = "✅" if result.success else "⚠️"
        print(f"{status} {result.job.title} at {result.job.company} - {result.message}")


if __name__ == "__main__":  # pragma: no cover
    main()
