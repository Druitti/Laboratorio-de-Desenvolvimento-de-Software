#!/usr/bin/env python3
"""Validação rápida de amostra (5–10 repos) — RQ01 a RQ04 (#3+#4)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from collect_repos import collect_top_repos  # noqa: E402


def age_days(created_at: str, now: datetime | None = None) -> float:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = now or datetime.now(timezone.utc)
    return (now - created).total_seconds() / 86400.0


def days_since(iso_ts: str, now: datetime | None = None) -> float:
    ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    now = now or datetime.now(timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def validate_repo(repo: dict) -> list[str]:
    problems: list[str] = []
    name = repo.get("nameWithOwner", "?")
    if not repo.get("createdAt"):
        problems.append(f"{name}: createdAt ausente (RQ01)")
    if "pullRequests" not in repo or repo["pullRequests"].get("totalCount") is None:
        problems.append(f"{name}: pullRequests MERGED ausente (RQ02)")
    if "releases" not in repo or repo["releases"].get("totalCount") is None:
        problems.append(f"{name}: releases ausente (RQ03)")
    if not repo.get("pushedAt") and not repo.get("updatedAt"):
        problems.append(f"{name}: pushedAt/updatedAt ausentes (RQ04)")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida amostra RQ01-RQ04")
    parser.add_argument("--sample", type=int, default=8)
    args = parser.parse_args()
    sample = max(5, min(10, args.sample))

    repos = collect_top_repos(first=sample)
    problems: list[str] = []
    for repo in repos:
        problems.extend(validate_repo(repo))
        print(
            f"- {repo['nameWithOwner']}: idade~={age_days(repo['createdAt']):.0f}d | "
            f"PRs={repo['pullRequests']['totalCount']} | "
            f"releases={repo['releases']['totalCount']} | "
            f"dias desde push~={days_since(repo['pushedAt']):.0f}"
        )

    if problems:
        print("\nFalhas:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print(f"\nValidacao OK (RQ01-RQ04) na amostra de {len(repos)} repos.")


if __name__ == "__main__":
    main()
