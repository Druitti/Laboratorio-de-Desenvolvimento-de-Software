#!/usr/bin/env python3
"""Coleta os repositórios mais populares do GitHub via GraphQL (Lab01S01)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
QUERY_PATH = Path(__file__).resolve().parent / "graphql" / "repos_query.graphql"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
DEFAULT_FIRST = 100


def load_token() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token

    # Fallback: gh CLI (não imprime o token)
    try:
        import subprocess

        result = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
        )
        token = result.stdout.strip()
        if token:
            return token
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    print(
        "Erro: defina GITHUB_TOKEN/GH_TOKEN ou autentique o GitHub CLI (`gh auth login`).",
        file=sys.stderr,
    )
    sys.exit(1)


def load_query() -> str:
    return QUERY_PATH.read_text(encoding="utf-8")


def graphql_request(token: str, query: str, variables: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    response = requests.post(
        GITHUB_GRAPHQL_URL,
        headers=headers,
        json={"query": query, "variables": variables},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise RuntimeError(f"Erros GraphQL: {json.dumps(payload['errors'], indent=2)}")
    return payload["data"]


def collect_top_repos(first: int = DEFAULT_FIRST) -> list[dict]:
    token = load_token()
    query = load_query()
    data = graphql_request(token, query, {"first": first})
    search = data["search"]
    repos = [node for node in search["nodes"] if node]
    print(f"repositoryCount (estimado pela API): {search['repositoryCount']}")
    print(f"repositórios retornados: {len(repos)}")
    return repos


def main() -> None:
    first = DEFAULT_FIRST
    if len(sys.argv) > 1:
        first = int(sys.argv[1])

    repos = collect_top_repos(first=first)
    out_dir = ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"top_{first}_repos.json"
    out_path.write_text(json.dumps(repos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"salvo em: {out_path}")

    for repo in repos[:5]:
        print(f"- {repo['nameWithOwner']} ({repo['stargazerCount']} stars)")


if __name__ == "__main__":
    main()
