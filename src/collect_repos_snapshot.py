#!/usr/bin/env python3
"""Coleta os repositórios mais populares do GitHub via GraphQL (Lab01S01)."""

from __future__ import annotations

import csv
import json
import os
import sys
import time
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

# S02: coleta de até 1000 repositórios
DEFAULT_FIRST = 1000

# Quantidade de repositórios buscados por requisição.
# Pode ser alterada pelo argumento de linha de comando.
DEFAULT_PAGE_SIZE = 20


def load_token() -> str:
    """
    Obtém o token de autenticação do GitHub.

    Ordem de tentativa:
    1. GITHUB_TOKEN
    2. GH_TOKEN
    3. GitHub CLI (gh auth token)
    """
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    if token:
        return token

    # Fallback: tenta obter o token pelo GitHub CLI
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
    """Carrega a query GraphQL utilizada na coleta."""
    return QUERY_PATH.read_text(encoding="utf-8")


def graphql_request(
    token: str,
    query: str,
    variables: dict,
    retries: int = 4,
) -> dict:
    """
    Faz uma requisição para a API GraphQL do GitHub.

    Em caso de erros temporários, realiza novas tentativas
    utilizando exponential backoff.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            response = requests.post(
                GITHUB_GRAPHQL_URL,
                headers=headers,
                json={
                    "query": query,
                    "variables": variables,
                },
                timeout=120,
            )

            # Erros considerados temporários
            if response.status_code in {502, 503, 504}:
                raise requests.HTTPError(
                    f"{response.status_code} transient",
                    response=response,
                )

            response.raise_for_status()

            payload = response.json()

            # A requisição HTTP pode funcionar, mas o GraphQL
            # ainda pode retornar erros.
            if "errors" in payload:
                raise RuntimeError(
                    "Erros GraphQL: "
                    f"{json.dumps(payload['errors'], indent=2, ensure_ascii=False)}"
                )

            return payload["data"]

        except (
            requests.HTTPError,
            requests.Timeout,
            requests.ConnectionError,
        ) as exc:
            last_error = exc

            wait = 2**attempt

            print(
                f"Aviso: falha na tentativa "
                f"{attempt + 1}/{retries}: {exc}; "
                f"nova tentativa em {wait}s"
            )

            time.sleep(wait)

    raise RuntimeError(
        f"GraphQL falhou após {retries} tentativas: {last_error}"
    )


def collect_top_repos(
    first: int = DEFAULT_FIRST,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[dict]:
    """
    Coleta até `first` repositórios mais populares do GitHub.

    A paginação é realizada por cursor utilizando endCursor
    e hasNextPage retornados pela API GraphQL.
    """
    token = load_token()
    query = load_query()

    repos: list[dict] = []
    cursor: str | None = None
    repository_count: int | None = None
    page_number = 0

    while len(repos) < first:
        # A API GraphQL do GitHub aceita no máximo 100 itens
        # em campos paginados.
        batch = min(page_size, first - len(repos), 100)

        variables = {
            "first": batch,
            "after": cursor,
        }

        page_number += 1

        print(
            f"Coletando página {page_number} "
            f"({len(repos)}/{first} repositórios coletados)..."
        )

        data = graphql_request(
            token=token,
            query=query,
            variables=variables,
        )

        search = data["search"]

        if repository_count is None:
            repository_count = search["repositoryCount"]

        # Alguns nodes podem eventualmente ser null
        batch_repos = [
            node
            for node in search["nodes"]
            if node is not None
        ]

        repos.extend(batch_repos)

        page_info = search["pageInfo"]

        # Interrompe se não houver mais páginas
        if not page_info.get("hasNextPage"):
            break

        # Também interrompe caso uma página não retorne resultados
        if not batch_repos:
            break

        cursor = page_info["endCursor"]

    # Garante que nunca retornaremos mais do que solicitado
    repos = repos[:first]

    print()
    print(
        f"repositoryCount (estimado pela API): "
        f"{repository_count}"
    )
    print(f"Repositórios retornados: {len(repos)}")

    return repos


def save_json(repos: list[dict], out_path: Path) -> None:
    """Salva os repositórios no formato JSON."""
    out_path.write_text(
        json.dumps(
            repos,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"JSON salvo em: {out_path}")


def repo_to_csv_row(repo: dict) -> dict:
    """
    Converte a estrutura GraphQL de um repositório
    para uma estrutura simples utilizada no CSV.
    """

    primary_language = repo.get("primaryLanguage")

    if primary_language:
        language_name = primary_language.get("name")
    else:
        language_name = None

    return {
        "nameWithOwner": repo.get("nameWithOwner"),
        "url": repo.get("url"),
        "stargazerCount": repo.get("stargazerCount"),
        "createdAt": repo.get("createdAt"),
        "updatedAt": repo.get("updatedAt"),
        "pushedAt": repo.get("pushedAt"),
        "primaryLanguage": language_name,
        "mergedPullRequests": (
            repo.get("pullRequests", {}).get("totalCount")
        ),
        "releases": (
            repo.get("releases", {}).get("totalCount")
        ),
        "issues": (
            repo.get("issues", {}).get("totalCount")
        ),
        "closedIssues": (
            repo.get("closedIssues", {}).get("totalCount")
        ),
    }


def save_csv(repos: list[dict], out_path: Path) -> None:
    """Salva os repositórios coletados no formato CSV."""

    fieldnames = [
        "nameWithOwner",
        "url",
        "stargazerCount",
        "createdAt",
        "updatedAt",
        "pushedAt",
        "primaryLanguage",
        "mergedPullRequests",
        "releases",
        "issues",
        "closedIssues",
    ]

    with out_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for repo in repos:
            writer.writerow(
                repo_to_csv_row(repo)
            )

    print(f"CSV salvo em: {out_path}")


def main() -> None:
    """
    Executa a coleta e salva os resultados
    nos formatos JSON e CSV.

    Uso:
        python collect_repos.py
        python collect_repos.py 1000
        python collect_repos.py 1000 50

    Argumento 1:
        quantidade de repositórios.

    Argumento 2:
        tamanho da página.
    """

    first = DEFAULT_FIRST
    page_size = DEFAULT_PAGE_SIZE

    if len(sys.argv) > 1:
        first = int(sys.argv[1])

    if len(sys.argv) > 2:
        page_size = int(sys.argv[2])

    if first <= 0:
        print(
            "Erro: a quantidade de repositórios deve ser maior que zero.",
            file=sys.stderr,
        )
        sys.exit(1)

    if page_size <= 0:
        print(
            "Erro: o tamanho da página deve ser maior que zero.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Evita ultrapassar o limite máximo usado pela paginação GraphQL
    page_size = min(page_size, 100)

    print("=" * 60)
    print("Coleta de repositórios populares do GitHub")
    print("=" * 60)
    print(f"Quantidade desejada: {first}")
    print(f"Tamanho da página: {page_size}")
    print()

    repos = collect_top_repos(
        first=first,
        page_size=page_size,
    )

    # Cria diretório data/
    out_dir = ROOT / "data"
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Caminhos dos arquivos
    json_path = out_dir / f"top_{first}_repos.json"
    csv_path = out_dir / f"top_{first}_repos.csv"

    print()
    print("Salvando arquivos...")

    save_json(
        repos=repos,
        out_path=json_path,
    )

    save_csv(
        repos=repos,
        out_path=csv_path,
    )

    # Mostra uma pequena amostra
    print()
    print("Top 5 repositórios coletados:")

    for repo in repos[:5]:
        print(
            f"- {repo['nameWithOwner']} "
            f"({repo['stargazerCount']} stars)"
        )

    print()
    print("Coleta finalizada com sucesso.")


if __name__ == "__main__":
    main()