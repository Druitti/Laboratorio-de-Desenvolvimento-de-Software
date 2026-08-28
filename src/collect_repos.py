#!/usr/bin/env python3
"""Coleta os repositórios mais populares do GitHub via GraphQL (Lab01S01)."""

from __future__ import annotations

import csv
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
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

# Fonte de linguagens populares (RQ05) — referência única em todo o Lab01
TIOBE_TOP_LANGUAGES = {
    "Python", "C", "C++", "Java", "C#", "JavaScript", "Visual Basic",
    "Go", "Delphi/Object Pascal", "SQL", "Fortran", "Rust", "PHP", "R",
    "MATLAB", "Assembly language", "Swift", "Ruby", "Kotlin", "Scratch",
}
TIOBE_SOURCE = "https://www.tiobe.com/tiobe-index/"


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


def parse_github_date(value: str) -> datetime:
    """Converte uma data ISO 8601 retornada pelo GitHub."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def print_rq_metrics(repos: list[dict]) -> None:
    """Calcula e imprime as métricas das RQs 01 a 03."""
    now = datetime.now(timezone.utc)
    ages_days = [
        (now - parse_github_date(repo["createdAt"])).days
        for repo in repos
        if repo.get("createdAt")
    ]
    merged_prs = [
        repo["pullRequests"]["totalCount"]
        for repo in repos
        if repo.get("pullRequests", {}).get("totalCount") is not None
    ]
    releases = [
        repo["releases"]["totalCount"]
        for repo in repos
        if repo.get("releases", {}).get("totalCount") is not None
    ]

    print()
    print("=" * 60)
    print("MÉTRICAS E RESPOSTAS DOS RQs 01 A 03")
    print("=" * 60)

    if ages_days:
        median_age_days = statistics.median(ages_days)
        median_age_years = median_age_days / 365.25
        print("\nRQ01 - Sistemas populares são maduros/antigos?")
        print(f"Repositórios analisados: {len(ages_days)}")
        print(f"Idade mediana: {median_age_days:.1f} dias ({median_age_years:.1f} anos)")
        print(f"Idade média: {statistics.mean(ages_days):.1f} dias")
        print(f"Menor idade: {min(ages_days)} dias")
        print(f"Maior idade: {max(ages_days)} dias")
        print(
            "Resposta: "
            + (
                "Sim. A idade mediana indica que os sistemas populares são maduros."
                if median_age_years >= 3
                else "Não. A idade mediana não indica sistemas antigos."
            )
        )

    if merged_prs:
        median_prs = statistics.median(merged_prs)
        print("\nRQ02 - Sistemas populares recebem muita contribuição externa?")
        print(f"Repositórios analisados: {len(merged_prs)}")
        print(f"Mediana de pull requests aceitas: {median_prs:.1f}")
        print(f"Média de pull requests aceitas: {statistics.mean(merged_prs):.1f}")
        print(f"Menor quantidade: {min(merged_prs)}")
        print(f"Maior quantidade: {max(merged_prs)}")
        print(
            "Resposta: "
            + (
                "Sim. A mediana mostra uma quantidade relevante de contribuições aceitas."
                if median_prs > 100
                else "Em geral, não. A mediana de contribuições aceitas é baixa."
            )
        )

    if releases:
        median_releases = statistics.median(releases)
        without_releases = sum(value == 0 for value in releases)
        without_releases_percent = without_releases / len(releases) * 100
        print("\nRQ03 - Sistemas populares lançam releases com frequência?")
        print(f"Repositórios analisados: {len(releases)}")
        print(f"Mediana de releases: {median_releases:.1f}")
        print(f"Média de releases: {statistics.mean(releases):.1f}")
        print(f"Menor quantidade: {min(releases)}")
        print(f"Maior quantidade: {max(releases)}")
        print(
            f"Repositórios sem releases: {without_releases} "
            f"({without_releases_percent:.1f}%)"
        )
        print(
            "Resposta: "
            + (
                "Sim. A mediana indica que os sistemas populares costumam publicar releases."
                if median_releases > 10
                else "Não necessariamente. A mediana de releases é baixa."
            )
        )


def print_rq_metrics_rq04_rq07(repos: list[dict]) -> None:
    """Calcula e imprime as métricas das RQs 04 a 07."""
    now = datetime.now(timezone.utc)

    print()
    print("=" * 60)
    print("MÉTRICAS E RESPOSTAS DOS RQs 04 A 07")
    print("=" * 60)

    # RQ04
    days_list = []
    for repo in repos:
        ts = repo.get("pushedAt") or repo.get("updatedAt")
        if not ts:
            continue
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        days_list.append(max(0.0, (now - dt).total_seconds() / 86400.0))

    if days_list:
        median_days = statistics.median(days_list)
        print("\nRQ04 - Sistemas populares são atualizados com frequência?")
        print(f"Repositórios analisados: {len(days_list)}")
        print(f"Mediana (dias desde último push): {median_days:.1f}")
        print(f"Média: {statistics.mean(days_list):.1f} dias")
        print(f"Menor valor: {min(days_list):.0f} dias")
        print(f"Maior valor: {max(days_list):.0f} dias")
        print(
            "Resposta: "
            + (
                "Sim. A mediana indica que os sistemas populares são atualizados frequentemente."
                if median_days <= 30
                else "Não necessariamente. A mediana indica atualizações pouco frequentes."
            )
        )

    # RQ05
    lang_counts: dict[str, int] = {}
    tiobe_count = 0
    nao_tiobe_count = 0
    sem_lang_count = 0

    for repo in repos:
        lang = (repo.get("primaryLanguage") or {}).get("name")
        if not lang:
            sem_lang_count += 1
        elif lang in TIOBE_TOP_LANGUAGES:
            tiobe_count += 1
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        else:
            nao_tiobe_count += 1
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    total = len(repos)
    print("\nRQ05 - Sistemas populares são escritos nas linguagens mais populares?")
    print(f"Repositórios analisados: {total}  (fonte: TIOBE Index — {TIOBE_SOURCE})")
    print(f"  TIOBE top 20: {tiobe_count} ({tiobe_count / total * 100:.1f}%)")
    print(f"  Não TIOBE:    {nao_tiobe_count} ({nao_tiobe_count / total * 100:.1f}%)")
    print(f"  Sem linguagem: {sem_lang_count} ({sem_lang_count / total * 100:.1f}%)")
    print("Top 10 linguagens:")
    for lang, cnt in sorted(lang_counts.items(), key=lambda x: -x[1])[:10]:
        mark = "[TIOBE]" if lang in TIOBE_TOP_LANGUAGES else "       "
        print(f"  {mark}  {lang}: {cnt}")
    print(
        "Resposta: "
        + (
            "Sim. A maioria dos repositórios populares usa linguagens do TIOBE top 20."
            if tiobe_count / total >= 0.5
            else "Não necessariamente. Menos da metade usa linguagens TIOBE top 20."
        )
    )

    # RQ06
    ratios: list[float] = []
    sem_issues = 0
    for repo in repos:
        total_issues = repo.get("issues", {}).get("totalCount")
        closed = repo.get("closedIssues", {}).get("totalCount")
        if total_issues is None or closed is None:
            continue
        if total_issues == 0:
            sem_issues += 1
            continue
        ratios.append(closed / total_issues)

    if ratios:
        median_ratio = statistics.median(ratios)
        print("\nRQ06 - Sistemas populares possuem alto percentual de issues fechadas?")
        print(f"Repositórios com issues > 0: {len(ratios)}")
        print(f"Repositórios sem issues: {sem_issues}")
        print(f"Mediana de issues fechadas: {median_ratio:.3f} ({median_ratio * 100:.1f}%)")
        print(f"Média: {statistics.mean(ratios):.3f} ({statistics.mean(ratios) * 100:.1f}%)")
        print(f"Menor valor: {min(ratios):.3f}  |  Maior valor: {max(ratios):.3f}")
        print(
            "Resposta: "
            + (
                "Sim. A mediana indica um alto percentual de issues fechadas."
                if median_ratio >= 0.5
                else "Não. A mediana indica um baixo percentual de issues fechadas."
            )
        )

    # RQ07
    groups: dict[str, list[dict]] = {"TIOBE": [], "Não TIOBE": []}
    for repo in repos:
        lang = (repo.get("primaryLanguage") or {}).get("name")
        if not lang:
            continue
        cat = "TIOBE" if lang in TIOBE_TOP_LANGUAGES else "Não TIOBE"
        ts = repo.get("pushedAt") or repo.get("updatedAt")
        days_val = None
        if ts:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            days_val = max(0.0, (now - dt).total_seconds() / 86400.0)
        groups[cat].append({
            "prs": repo.get("pullRequests", {}).get("totalCount"),
            "releases": repo.get("releases", {}).get("totalCount"),
            "days": days_val,
        })

    print("\nRQ07 (bônus) - Sistemas em linguagens TIOBE recebem mais contribuição,"
          " lançam mais releases e são atualizados com mais frequência?")
    for metric, label, unit in [
        ("prs",      "PRs merged (RQ02)",      "PRs"),
        ("releases", "Releases (RQ03)",         "releases"),
        ("days",     "Dias desde push (RQ04)",  "dias"),
    ]:
        print(f"  {label}:")
        for cat, items in groups.items():
            vals = [r[metric] for r in items if r[metric] is not None]
            med = statistics.median(vals)
            mean = statistics.mean(vals)
            print(f"    {cat}: n={len(vals)}  mediana={med:.1f} {unit}  média={mean:.1f} {unit}")


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

    print_rq_metrics(repos)

    print_rq_metrics_rq04_rq07(repos)

    print()
    print("Coleta finalizada com sucesso.")


if __name__ == "__main__":
    main()
