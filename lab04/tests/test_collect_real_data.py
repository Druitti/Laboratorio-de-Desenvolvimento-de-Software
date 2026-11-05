import csv
from datetime import datetime, timezone

import pytest
import requests

from lab04.collect_real_data import (
    ATTEMPTS,
    GraphQLClient,
    classify_pr,
    collect,
    draw_sample,
    fetch_frame,
    search_query,
)
from lab04.real_data import WITH_BOT, WITHOUT_BOT, load_real_data, read_config

BOTS = {"coderabbitai"}
HUMAN = {"__typename": "User", "login": "alice"}
BOT = {"__typename": "Bot", "login": "coderabbitai"}
OTHER_BOT = {"__typename": "Bot", "login": "github-advanced-security"}
NAMESAKE = {"__typename": "User", "login": "coderabbitai"}


def make_pr(number=1, repository="o/r", author=HUMAN, reviews=(), comments=(), truncated=False):
    return {
        "number": number,
        "url": f"https://github.com/{repository}/pull/{number}",
        "createdAt": "2026-02-01T00:00:00Z",
        "mergedAt": "2026-02-02T00:00:00Z",
        "additions": 3,
        "deletions": 1,
        "changedFiles": 2,
        "author": author,
        "repository": {"nameWithOwner": repository},
        "reviews": {"pageInfo": {"hasNextPage": truncated}, "nodes": list(reviews)},
        "comments": {"pageInfo": {"hasNextPage": False}, "nodes": list(comments)},
    }


def review(author, submitted_at="2026-02-01T12:00:00Z"):
    return {"author": author, "submittedAt": submitted_at}


@pytest.mark.parametrize(
    "pr,expected",
    [
        (make_pr(reviews=[review(BOT)]), (WITH_BOT, ["coderabbitai"])),
        (make_pr(reviews=[review(HUMAN)]), (WITHOUT_BOT, [])),
        (make_pr(), (WITHOUT_BOT, [])),
        (make_pr(comments=[{"author": OTHER_BOT}]), (WITHOUT_BOT, [])),
        (make_pr(reviews=[review(NAMESAKE)], comments=[{"author": NAMESAKE}]), (WITHOUT_BOT, [])),
        (make_pr(author=BOT), ("excluded_author", [])),
        (make_pr(author=None), ("excluded_author", [])),
        (make_pr(truncated=True), ("excluded_truncated", [])),
        (make_pr(reviews=[review(OTHER_BOT)]), ("excluded_ambiguous", [])),
        (make_pr(reviews=[review(None)]), ("excluded_ambiguous", [])),
        (make_pr(comments=[{"author": BOT}]), ("excluded_ambiguous", [])),
        (make_pr(reviews=[review(BOT, "2026-02-03T00:00:00Z")]), ("excluded_ambiguous", [])),
    ],
)
def test_classification_only_accepts_proven_groups(pr, expected):
    assert classify_pr(pr, BOTS, min_minutes_to_merge=10) == expected


@pytest.mark.parametrize(
    "merged_at,expected",
    [("2026-02-01T00:09:59Z", "excluded_fast_merge"), ("2026-02-01T00:10:00Z", WITHOUT_BOT)],
)
def test_pr_merged_before_the_bot_could_respond_joins_no_group(merged_at, expected):
    pr = {**make_pr(), "mergedAt": merged_at}
    assert classify_pr(pr, BOTS, min_minutes_to_merge=10)[0] == expected


def pools(count=6):
    return {
        f"o/r{index}": {
            WITH_BOT: [make_pr(number, f"o/r{index}") for number in range(1, 7)],
            WITHOUT_BOT: [make_pr(number, f"o/r{index}") for number in range(7, 13)],
        }
        for index in range(count)
    }


def test_draw_is_reproducible_and_uses_each_repository_once():
    first = draw_sample(pools(), n_per_group=3, seed=7)
    assert first == draw_sample(pools(), n_per_group=3, seed=7)
    repositories = [pr["repository"]["nameWithOwner"] for _, pr in first]
    assert len(repositories) == len(set(repositories)) == 6
    assert sum(group == WITH_BOT for group, _ in first) == 3
    for group, pr in first:
        assert (pr["number"] <= 6) == (group == WITH_BOT)


def test_draw_fails_without_enough_repositories():
    with pytest.raises(ValueError, match="elegíveis"):
        draw_sample(pools(5), n_per_group=3, seed=7)


class FakeClient:
    """Responde por repositório; o repositório o/r6 só tem PRs sem bot."""

    def graphql(self, query, variables):
        repository = variables["q"].split()[0].removeprefix("repo:")
        reviews = {"o/r6": ()}.get(repository, (review(BOT),))
        nodes = [make_pr(number, repository, reviews=reviews if number % 2 else ()) for number in range(1, 5)]
        out_of_window = {**make_pr(99, repository), "createdAt": "2025-12-31T23:59:59Z"}
        page = {"issueCount": len(nodes) + 1, "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [*nodes, out_of_window, {}]}
        return {"search": page}


def test_collect_writes_a_sample_accepted_by_the_validator(tmp_path):
    config = {**read_config(), "n_per_group": 3, "min_prs_per_group": 2, "seed": 1, "review_bots": ["coderabbitai"]}
    repositories = [f"o/r{index}" for index in range(7)]
    now = datetime(2026, 11, 5, tzinfo=timezone.utc)
    rows = collect(FakeClient(), config, repositories, tmp_path, workers=3, now=now)

    assert rows == collect(FakeClient(), config, repositories, tmp_path, workers=1, now=now)
    assert len(rows) == 6
    assert len(load_real_data(tmp_path / "real_prs.csv", config)) == 6
    with (tmp_path / "real_funnel.csv").open(newline="", encoding="utf-8") as stream:
        funnel = {row["repository"]: row for row in csv.DictReader(stream)}
    assert list(funnel) == repositories
    assert funnel["o/r6"]["eligible"] == "false"
    assert funnel["o/r6"]["sampled_pr"] == ""
    assert funnel["o/r0"]["listed"] == "4"
    assert sum(bool(row["sampled_pr"]) for row in funnel.values()) == 6


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload
        self.headers = {}

    def json(self):
        if self.payload is None:
            raise requests.exceptions.JSONDecodeError("corpo vazio", "", 0)
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.posts = 0

    def post(self, url, json, timeout):
        self.posts += 1
        return self.responses.pop(0)


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr("lab04.collect_real_data.time.sleep", lambda _: None)


def test_client_retries_transient_failures_and_reuses_the_cache(tmp_path, no_sleep):
    session = FakeSession([FakeResponse(), FakeResponse(502), FakeResponse(200, {"errors": [{}]}),
                           FakeResponse(200, {"data": {"search": 1}})])
    client = GraphQLClient("token", tmp_path, session=session)
    assert client.graphql("q", {}) == {"search": 1}
    assert session.posts == 4
    assert client.graphql("q", {}) == {"search": 1}
    assert session.posts == 4


def test_client_gives_up_without_caching_the_failure(tmp_path, no_sleep):
    session = FakeSession([FakeResponse(502) for _ in range(ATTEMPTS)])
    with pytest.raises(RuntimeError, match="HTTP 502"):
        GraphQLClient("token", tmp_path, session=session).graphql("q", {})
    assert list(tmp_path.iterdir()) == []


def test_client_does_not_retry_authentication_errors(tmp_path, no_sleep):
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(RuntimeError, match="HTTP 401"):
        GraphQLClient("token", tmp_path, session=session).graphql("q", {})
    assert session.posts == 1


def test_client_requires_a_token(tmp_path):
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        GraphQLClient(None, tmp_path)


class FrameClient:
    def graphql(self, query, variables):
        first_page = variables["after"] is None
        names = ["a/1", "a/2"] if first_page else ["a/3", "a/4"]
        info = {"hasNextPage": first_page, "endCursor": "next" if first_page else None}
        return {"search": {"pageInfo": info, "nodes": [{"nameWithOwner": name} for name in names]}}


@pytest.mark.parametrize("size,expected", [(3, ["a/1", "a/2", "a/3"]), (9, ["a/1", "a/2", "a/3", "a/4"])])
def test_frame_is_paginated_and_limited_by_its_size(size, expected):
    assert fetch_frame(FrameClient(), {"frame_query": "q", "frame_size": size}) == expected


def test_search_query_uses_inclusive_end_of_window():
    query = search_query("o/r", read_config())
    assert "repo:o/r is:pr is:merged" in query
    assert "created:2026-01-01T00:00:00Z..2026-06-30T23:59:59Z" in query
    assert "merged:<2026-11-01T00:00:00Z" in query
