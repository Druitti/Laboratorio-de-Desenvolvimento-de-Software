"""Coleta os PRs reais do cenário P1 do Lab04S01 (#61) pela API GraphQL do GitHub.

Cada repositório sorteado contribui com um único PR, e o grupo que ele alimenta
também é sorteado. Uma falha de rede ou de cota interrompe a coleta: nenhum erro
é contado como ausência de bot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from lab04.real_data import COLUMNS, DEFAULT_CONFIG, ROOT, WITH_BOT, WITHOUT_BOT, parse_utc, read_config

API = "https://api.github.com/graphql"
DEFAULT_OUTPUT_DIR = ROOT / "lab04" / "data"
DEFAULT_CACHE_DIR = DEFAULT_OUTPUT_DIR / "cache"
PAGE_SIZE = 25
ATTEMPTS = 7  # Cerca de 2 minutos de espera no total: o GitHub às vezes responde HTTP 502 em rajadas.
EXCLUDED_AUTHOR = "excluded_author"
EXCLUDED_FAST_MERGE = "excluded_fast_merge"
EXCLUDED_AMBIGUOUS = "excluded_ambiguous"
EXCLUDED_TRUNCATED = "excluded_truncated"
FUNNEL_COLUMNS = ["repository", "total_matches", "listed", WITH_BOT, WITHOUT_BOT, EXCLUDED_AUTHOR, EXCLUDED_FAST_MERGE,
                  EXCLUDED_AMBIGUOUS, EXCLUDED_TRUNCATED, "eligible", "assigned_group", "sampled_pr"]
SOURCE = "GitHub GraphQL API v4 (search type ISSUE)"
LIMITATIONS = ("Observacional, sem causalidade; somente PRs mergeados; inclui tempo em draft; "
               "repositorios populares do GitHub; o uso do bot pode depender do PR; vies de tempo imortal residual "
               "(review tardia exige PR aberto); presenca do bot nao mede a qualidade da revisao")
FRAME_QUERY = """
query($q: String!, $after: String) {
  search(type: REPOSITORY, query: $q, first: 100, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes { ... on Repository { nameWithOwner } }
  }
}
"""
QUERY = """
query($q: String!, $after: String) {
  search(type: ISSUE, query: $q, first: %d, after: $after) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number url createdAt mergedAt additions deletions changedFiles
        author { __typename login }
        repository { nameWithOwner }
        reviews(first: 100) { pageInfo { hasNextPage } nodes { submittedAt author { __typename login } } }
        comments(first: 100) { pageInfo { hasNextPage } nodes { author { __typename login } } }
      }
    }
  }
}
""" % PAGE_SIZE


class GraphQLClient:
    """Cliente mínimo da API GraphQL: repete falhas transitórias e guarda as respostas em disco.

    O cache permite retomar a coleta sem repetir páginas; resposta com erro nunca é guardada.
    """

    def __init__(self, token: str | None, cache_dir: Path, session=None):
        if not token:
            raise ValueError("Defina GITHUB_TOKEN no ambiente.")
        self.session = session or requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def graphql(self, query: str, variables: dict) -> dict:
        body = {"query": query, "variables": variables}
        key = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        data = self._post(body)
        temporary = path.with_suffix(f".{threading.get_ident()}.tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        temporary.replace(path)
        return data

    def _post(self, body: dict) -> dict:
        failure = ""
        for attempt in range(ATTEMPTS):
            time.sleep(2**attempt - 1)
            try:
                # O GitHub às vezes responde 200 com corpo que não é JSON; json() levanta
                # um RequestException, tratado como as demais falhas transitórias.
                response = self.session.post(API, json=body, timeout=60)
                if response.status_code == 200:
                    payload = response.json()
                    if not payload.get("errors"):
                        return payload["data"]
                    failure = "GraphQL retornou erros"
                elif response.status_code >= 500 or response.status_code in (403, 429):
                    failure = f"HTTP {response.status_code}"
                    time.sleep(float(response.headers.get("Retry-After", 0)))
                else:
                    raise RuntimeError(f"HTTP {response.status_code} na API do GitHub.")
            except requests.RequestException as exc:
                failure = type(exc).__name__
        raise RuntimeError(f"API do GitHub falhou após {ATTEMPTS} tentativas ({failure}) em "
                           f"{body['variables'].get('q')!r}; retome pelo cache.")


def fetch_frame(client, config: dict) -> list[str]:
    """Lista o quadro amostral: os repositórios mais populares segundo a busca configurada."""
    repositories: list[str] = []
    after = None
    while len(repositories) < config["frame_size"]:
        page = client.graphql(FRAME_QUERY, {"q": config["frame_query"], "after": after})["search"]
        repositories.extend(node["nameWithOwner"] for node in page["nodes"] if node)
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return repositories[: config["frame_size"]]


def search_query(repository: str, config: dict) -> str:
    """Filtra pela criação para que todo PR tenha, no mínimo, o mesmo seguimento até o corte."""
    # O qualificador created: é inclusivo; a janela do lab tem fim exclusivo.
    last_second = (parse_utc(config["window_end"]) - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f"repo:{repository} is:pr is:merged created:{config['window_start']}..{last_second} "
            f"merged:<{config['merged_before']} sort:created-desc")


def _is_listed_bot(author: dict, review_bots: set[str]) -> bool:
    # Logins como "claude" e "cursor" também podem ser de pessoas; o tipo da conta decide.
    return author["__typename"] == "Bot" and author["login"] in review_bots


def classify_pr(pr: dict, review_bots: set[str], *, min_minutes_to_merge: int) -> tuple[str, list[str]]:
    """Devolve o grupo do PR, ou o motivo da exclusão, e os bots que o revisaram antes do merge."""
    author = pr.get("author")
    if not author or author["__typename"] == "Bot":
        return EXCLUDED_AUTHOR, []
    merged_at = parse_utc(pr["mergedAt"])
    # Mergeado antes de o bot ter tempo de responder, o PR cairia em "sem bot" por
    # construção (viés de tempo imortal), não por ter dispensado a revisão.
    if merged_at - parse_utc(pr["createdAt"]) < timedelta(minutes=min_minutes_to_merge):
        return EXCLUDED_FAST_MERGE, []
    if pr["reviews"]["pageInfo"]["hasNextPage"] or pr["comments"]["pageInfo"]["hasNextPage"]:
        return EXCLUDED_TRUNCATED, []
    reviews, comments = pr["reviews"]["nodes"], pr["comments"]["nodes"]
    used = sorted({
        review["author"]["login"]
        for review in reviews
        if review["author"] and _is_listed_bot(review["author"], review_bots)
        and review["submittedAt"] and parse_utc(review["submittedAt"]) < merged_at
    })
    if used:
        return WITH_BOT, used
    # Sem prova de que nenhum bot revisou: review de outro bot ou tardia, comentário
    # de bot da lista ou autor removido não entram em nenhum dos dois grupos.
    if any(not review["author"] or review["author"]["__typename"] == "Bot" for review in reviews):
        return EXCLUDED_AMBIGUOUS, []
    if any(not comment["author"] or _is_listed_bot(comment["author"], review_bots) for comment in comments):
        return EXCLUDED_AMBIGUOUS, []
    return WITHOUT_BOT, []


def fetch_repository(client, repository: str, config: dict) -> tuple[int, list[dict]]:
    """Lista os PRs mais recentes da janela, até ``max_prs_per_repository``."""
    prs: list[dict] = []
    after = None
    while True:
        page = client.graphql(QUERY, {"q": search_query(repository, config), "after": after})["search"]
        prs.extend(node for node in page["nodes"] if node and _in_scope(node, config))
        if not page["pageInfo"]["hasNextPage"] or len(prs) >= config["max_prs_per_repository"]:
            return page["issueCount"], prs[: config["max_prs_per_repository"]]
        after = page["pageInfo"]["endCursor"]


def _in_scope(pr: dict, config: dict) -> bool:
    # A busca fornece o candidato; a janela e o corte são confirmados aqui.
    created_at, merged_at = parse_utc(pr["createdAt"]), parse_utc(pr["mergedAt"])
    return (parse_utc(config["window_start"]) <= created_at < parse_utc(config["window_end"])
            and merged_at < parse_utc(config["merged_before"]))


def screen_repository(client, repository: str, config: dict) -> tuple[dict, dict]:
    """Classifica os PRs de um repositório; devolve a linha do funil e os candidatos."""
    total, prs = fetch_repository(client, repository, config)
    review_bots = set(config["review_bots"])
    candidates: dict[str, list[dict]] = {WITH_BOT: [], WITHOUT_BOT: []}
    funnel = {"repository": repository, "total_matches": total, "listed": len(prs), WITH_BOT: 0, WITHOUT_BOT: 0,
              EXCLUDED_AUTHOR: 0, EXCLUDED_FAST_MERGE: 0, EXCLUDED_AMBIGUOUS: 0, EXCLUDED_TRUNCATED: 0}
    for pr in prs:
        category, used = classify_pr(pr, review_bots, min_minutes_to_merge=config["min_minutes_to_merge"])
        funnel[category] += 1
        if category in candidates:
            candidates[category].append({**pr, "review_bots": used})
    funnel["eligible"] = all(len(items) >= config["min_prs_per_group"] for items in candidates.values())
    return funnel, candidates


def draw_sample(pools: dict[str, dict[str, list[dict]]], *, n_per_group: int, seed: int) -> list[tuple[str, dict]]:
    """Sorteia os repositórios de cada grupo e um PR de cada; a mesma semente repete o sorteio."""
    if len(pools) < 2 * n_per_group:
        raise ValueError(f"Há {len(pools)} repositórios elegíveis; são necessários {2 * n_per_group}.")
    rng = random.Random(seed)
    drawn = rng.sample(sorted(pools), 2 * n_per_group)
    assignment = {WITH_BOT: drawn[:n_per_group], WITHOUT_BOT: drawn[n_per_group:]}
    sample = []
    for group, repositories in assignment.items():
        for repository in sorted(repositories):
            sample.append((group, rng.choice(sorted(pools[repository][group], key=lambda pr: pr["number"]))))
    return sample


def _method(config: dict) -> str:
    return (f"PR de autor humano criado em [{config['window_start']}, {config['window_end']}) e mergeado antes de "
            f"{config['merged_before']}, aberto por ao menos {config['min_minutes_to_merge']} min; sorteio com semente "
            f"{config['seed']}, um PR por repositorio; grupo pela review de bot da lista antes do merge; "
            "value = (mergedAt - createdAt) / 3600")


def _sample_row(group: str, pr: dict, config: dict, collected_at: str) -> dict:
    hours = (parse_utc(pr["mergedAt"]) - parse_utc(pr["createdAt"])).total_seconds() / 3600
    return {
        "group": group,
        "value": f"{hours:.4f}",
        "repository": pr["repository"]["nameWithOwner"],
        "pr_number": pr["number"],
        "source_url": pr["url"],
        "created_at": pr["createdAt"],
        "merged_at": pr["mergedAt"],
        "review_bots": ";".join(pr["review_bots"]),
        "additions": pr["additions"],
        "deletions": pr["deletions"],
        "changed_files": pr["changedFiles"],
        "collected_at": collected_at,
        "source": SOURCE,
        "method": _method(config),
        "limitations": LIMITATIONS,
    }


def collect(client, config: dict, repositories: list[str], output_dir: Path, *, workers: int = 1,
            now=None) -> list[dict]:
    """Executa toda a coleta e grava a amostra e o funil."""
    collected_at = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    funnel, pools = [], {}
    # map preserva a ordem do quadro: o sorteio não depende de qual thread termina antes.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        screened = executor.map(lambda repository: screen_repository(client, repository, config), repositories)
        for index, (row, candidates) in enumerate(screened, start=1):
            funnel.append(row)
            if row["eligible"]:
                pools[row["repository"]] = candidates
            if index % 25 == 0:
                print(f"{index}/{len(repositories)} repositórios; {len(pools)} elegíveis.", file=sys.stderr, flush=True)

    sample = draw_sample(pools, n_per_group=config["n_per_group"], seed=config["seed"])
    picked = {pr["repository"]["nameWithOwner"].lower(): (group, pr["number"]) for group, pr in sample}
    for row in funnel:
        group, number = picked.get(row["repository"].lower(), ("", ""))
        row.update(eligible=str(row["eligible"]).lower(), assigned_group=group, sampled_pr=number)
    rows = [_sample_row(group, pr, config, collected_at) for group, pr in sample]

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "real_prs.csv", COLUMNS, rows)
    _write_csv(output_dir / "real_funnel.csv", FUNNEL_COLUMNS, funnel)
    return rows


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    config = read_config(args.config)
    client = GraphQLClient(os.environ.get("GITHUB_TOKEN"), args.cache_dir)
    rows = collect(client, config, fetch_frame(client, config), args.output_dir, workers=args.workers)
    print(f"{len(rows)} observações gravadas em {args.output_dir}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
