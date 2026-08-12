#!/usr/bin/env python3
"""Validação rápida de amostra (5–10 repos) para as métricas das RQs 01–06."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from collect_repos import collect_top_repos  # noqa: E402

# Fonte de linguagens populares (RQ05) — mesma referência em todo o Lab01
TIOBE_TOP_LANGUAGES = {
    "Python",
    "C",
    "C++",
    "Java",
    "C#",
    "JavaScript",
    "Visual Basic",
    "Go",
    "Delphi/Object Pascal",
    "SQL",
    "Fortran",
    "Rust",
    "PHP",
    "R",
    "MATLAB",
    "Assembly language",
    "Swift",
    "Ruby",
    "Kotlin",
    "Scratch",
}
TIOBE_SOURCE = "https://www.tiobe.com/tiobe-index/"


def age_days(created_at: str, now: datetime | None = None) -> float:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = now or datetime.now(timezone.utc)
    return (now - created).total_seconds() / 86400.0


def days_since(iso_ts: str, now: datetime | None = None) -> float:
    ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    now = now or datetime.now(timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def closed_issue_ratio(repo: dict) -> float | None:
    total = repo["issues"]["totalCount"]
    if total == 0:
        return None
    return repo["closedIssues"]["totalCount"] / total


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
    if "primaryLanguage" not in repo:
        problems.append(f"{name}: primaryLanguage ausente (RQ05)")
    if "issues" not in repo or "closedIssues" not in repo:
        problems.append(f"{name}: issues/closedIssues ausentes (RQ06)")

    return problems


def print_sample(repos: list[dict]) -> None:
    print(f"Fonte linguagens populares (RQ05): TIOBE Index — {TIOBE_SOURCE}")
    print(f"Amostra: {len(repos)} repositorios\n")

    for repo in repos:
        lang = (repo.get("primaryLanguage") or {}).get("name")
        ratio = closed_issue_ratio(repo)
        ratio_txt = f"{ratio:.2%}" if ratio is not None else "n/a"
        popular = "sim" if lang in TIOBE_TOP_LANGUAGES else "nao"
        print(
            f"{repo['nameWithOwner']}\n"
            f"  RQ01 idade~={age_days(repo['createdAt']):.0f}d | "
            f"RQ02 PRs merged={repo['pullRequests']['totalCount']} | "
            f"RQ03 releases={repo['releases']['totalCount']}\n"
            f"  RQ04 dias desde push~={days_since(repo['pushedAt']):.0f} | "
            f"RQ05 lang={lang or 'null'} (TIOBE top? {popular}) | "
            f"RQ06 closed/total={ratio_txt}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida amostra das metricas Lab01")
    parser.add_argument(
        "--sample",
        type=int,
        default=8,
        help="Tamanho da amostra (5-10 recomendado)",
    )
    args = parser.parse_args()
    sample = max(5, min(10, args.sample))

    repos = collect_top_repos(first=sample)
    problems: list[str] = []
    for repo in repos:
        problems.extend(validate_repo(repo))

    print_sample(repos)

    if problems:
        print("\nFalhas na validacao:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("\nValidacao OK: todos os campos das RQs 01-06 presentes na amostra.")


if __name__ == "__main__":
    main()
