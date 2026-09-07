"""What each Parallel surface actually puts on the wire.

The other Parallel tests use fake client objects, which proves our code calls
the right method with the right arguments but says nothing about whether the
SDK turns those arguments into a request the API will accept. Six surfaces are
implemented and none has ever run against the real service, so the parameter
shapes are the largest untested risk in the project: a mis-nested
`source_policy` or a wrongly-typed `task_spec` would fail on the first live
call, which is also the call that matters most.

These tests intercept the SDK's HTTP transport and assert on the JSON body that
would be sent. They need no credential and no network, and they catch the class
of error that would otherwise surface only after the credential is attached.
"""

from __future__ import annotations

import json

import httpx
import parallel
import pytest

from app.partners import parallel_research as research
from app.partners import parallel_verify as verify


class Wire:
    """Records every request the SDK would send, and answers each plausibly."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def _respond(self, url: str) -> httpx.Response:
        if "/search" in url:
            return httpx.Response(
                200,
                json={"search_id": "s_1", "session_id": "x", "results": [], "warnings": [], "usage": []},
            )
        if "/extract" in url:
            return httpx.Response(
                200,
                json={
                    "extract_id": "e_1", "session_id": "x", "results": [],
                    "errors": [], "warnings": [], "usage": [],
                },
            )
        if "findall" in url and url.endswith("/result"):
            return httpx.Response(
                200,
                json={
                    "findall_id": "fa_1", "candidates": [],
                    "status": {"status": "completed", "is_active": False},
                },
            )
        if "findall" in url:
            return httpx.Response(
                200,
                json={
                    "findall_id": "fa_1", "generator": "base",
                    "status": {"status": "running", "is_active": True},
                },
            )
        if "monitors" in url:
            return httpx.Response(
                200,
                json={
                    "monitor_id": "mon_1", "type": "event_stream",
                    "frequency": "weekly", "created_at": None, "status": "active",
                },
            )
        if "groups" in url and url.endswith("/runs"):
            return httpx.Response(200, json={"status": "ok"})
        if "groups" in url:
            # The API field is `taskgroup_id`; the SDK model aliases it to
            # `task_group_id`. Answering with the model's Python name instead of
            # the wire name parses to None, which is how this fixture was wrong
            # the first time and is worth keeping written down.
            return httpx.Response(
                200,
                json={
                    "taskgroup_id": "tg_1",
                    "status": {
                        "num_task_runs": 0, "task_run_status_counts": {},
                        "is_active": False, "status_message": None, "modified_at": None,
                    },
                },
            )
        if "/result" in url:
            return httpx.Response(
                200,
                json={
                    "run": {
                        "run_id": "r_1", "status": "completed", "is_active": False,
                        "created_at": None, "modified_at": None, "processor": "base",
                        "metadata": None, "warnings": None, "error": None,
                    },
                    "output": {"type": "json", "content": {}, "basis": []},
                },
            )
        return httpx.Response(
            200,
            json={
                "run_id": "r_1", "status": "queued", "is_active": True,
                "created_at": None, "modified_at": None, "processor": "base",
                "metadata": None, "warnings": None, "error": None,
            },
        )

    def handler(self, request: httpx.Request) -> httpx.Response:
        body: dict = {}
        if request.content:
            try:
                body = json.loads(request.content)
            except json.JSONDecodeError:
                body = {}
        self.calls.append((request.method, str(request.url), body))
        self._last_headers = dict(request.headers)
        return self._respond(str(request.url))

    def client(self) -> parallel.Parallel:
        return parallel.Parallel(
            api_key="test-key-not-real",
            http_client=httpx.Client(transport=httpx.MockTransport(self.handler)),
        )

    def sent(self, fragment: str) -> dict:
        for _method, url, body in self.calls:
            if fragment in url and body:
                return body
        raise AssertionError(f"no request body sent to a URL containing {fragment!r}")

    def url_for(self, fragment: str) -> str:
        for _method, url, _body in self.calls:
            if fragment in url:
                return url
        raise AssertionError(f"no request sent to a URL containing {fragment!r}")


@pytest.fixture
def wire(monkeypatch) -> Wire:
    recorder = Wire()
    monkeypatch.setattr(research, "client", recorder.client)
    monkeypatch.setattr(verify, "client", recorder.client)
    return recorder


# ------------------------------------------------------------------ Search

def test_search_request_shape(wire: Wire) -> None:
    research.search_archival_evidence("Identify an archival fragment", ["\"a rare line\"", "second"])
    body = wire.sent("/v1/search")

    assert "/v1/search" in wire.url_for("/search")
    assert body["search_queries"] == ['"a rare line"', "second"]
    assert body["mode"] == "advanced"
    assert body["objective"]

    # Search's source policy is nested inside advanced_settings. Task's is
    # top-level. Getting these the wrong way round is silently accepted by
    # Python and rejected by the API.
    advanced = body["advanced_settings"]
    assert "source_policy" not in body
    assert advanced["source_policy"]["exclude_domains"], "content-recycling filter lost"
    assert "include_domains" not in advanced["source_policy"], (
        "Search must stay open to the whole web; a rare phrase can surface anywhere"
    )
    assert advanced["excerpt_settings"]["max_chars_per_result"] >= 4000, (
        "excerpts must be long enough to match a verbatim intertitle later"
    )


def test_search_sends_the_credential_as_a_header_not_a_query_parameter(wire: Wire) -> None:
    research.search_archival_evidence("objective", ["one", "two"])
    assert "x-api-key" in {k.lower() for k in wire._last_headers}
    assert "api_key" not in wire.url_for("/search"), "credential must never reach a URL"


# -------------------------------------------------------------------- Task

def test_task_request_shape(wire: Wire) -> None:
    research.deep_holdings_research("Which archives hold this film?")
    body = wire.sent("/v1/tasks/runs")

    # Measured against this exact schema: base 69s, pro-fast 268s. A four-minute
    # partner call inside a synchronous request is a timeout, not a budget.
    assert body["processor"] == "base"
    assert body["input"]

    # Task's source policy IS top-level, unlike Search's.
    assert body["source_policy"]["include_domains"], "archival source policy lost"
    assert "loc.gov" in body["source_policy"]["include_domains"]

    schema = body["task_spec"]["output_schema"]
    assert schema["type"] == "json"
    assert schema["json_schema"]["type"] == "object"
    for field in ("candidate_title", "named_catalogues_searched", "holdings_found"):
        assert field in schema["json_schema"]["properties"], f"{field} missing from output schema"
    assert body["metadata"]["workflow"] == "last-seen-alive-holdings"


# ----------------------------------------------------------------- FindAll

def test_findall_request_shape(wire: Wire) -> None:
    research.census_named_catalogues("The Lamplighter's Daughter", "1921")
    body = wire.sent("/v1beta/findall/runs")

    assert body["generator"] == "base"
    assert isinstance(body["match_limit"], int) and body["match_limit"] > 0
    assert body["entity_type"]
    assert "1921" in body["objective"], "the year has to reach the census objective"

    conditions = body["match_conditions"]
    assert len(conditions) >= 2
    for condition in conditions:
        assert condition["name"] and condition["description"], "match conditions need both fields"

    # The census exists to support a coverage statement, so it must ask for the
    # institution's own record rather than any mention of the title.
    joined = " ".join(c["description"] for c in conditions).lower()
    assert "catalogue" in joined


# ----------------------------------------------------------------- Extract

def test_extract_request_shape(wire: Wire) -> None:
    verify.audit_citations_with_extract([("https://trade.example.org/1921", "a quoted line")])
    body = wire.sent("/v1/extract")

    assert body["urls"] == ["https://trade.example.org/1921"]
    # Full content is the whole point: an excerpt would only re-confirm the
    # snippet we already had, not that the live page still says it.
    assert body["advanced_settings"]["full_content"] is True
    assert body["objective"]


def test_extract_never_requests_more_pages_than_its_ceiling(wire: Wire) -> None:
    verify.audit_citations_with_extract(
        [(f"https://example.org/{i}", "quote") for i in range(40)]
    )
    body = wire.sent("/v1/extract")
    assert len(body["urls"]) == verify.MAX_AUDITED_URLS


# -------------------------------------------------------------- Task Group

def test_task_group_request_shape(wire: Wire) -> None:
    verify.falsify_candidates_with_task_group(
        [
            {"candidate_id": "a", "label": "A (1921)"},
            {"candidate_id": "b", "label": "B (1922)"},
        ],
        visual_summary="a dark interior with one legible intertitle",
    )
    create = wire.sent("/v1/tasks/groups")
    assert create["metadata"]["workflow"] == "last-seen-alive-falsification"

    add = wire.sent("/runs")
    inputs = add["inputs"]
    assert len(inputs) == 2
    # Each run must be identifiable when the results stream back, or the
    # verdicts cannot be attached to the candidates they belong to.
    assert {run["metadata"]["candidate_id"] for run in inputs} == {"a", "b"}
    for run in inputs:
        assert "DISPROVE" in run["input"]
        assert "Do not argue for the candidate" in run["input"]

    schema = add["default_task_spec"]["output_schema"]
    assert schema["type"] == "json"
    assert "disproved" in schema["json_schema"]["properties"]


# ----------------------------------------------------------------- Monitor

def test_monitor_request_shape(wire: Wire) -> None:
    verify.open_cold_case_monitor(
        fragment_label="Unidentified reel, can 41B",
        rare_strings=["Tell Mara the lamp still burns"],
    )
    body = wire.sent("/v1/monitors")

    assert body["type"] == "event_stream"
    assert body["frequency"] == "weekly"
    assert body["processor"] == "base"
    settings = body["settings"]
    assert "Tell Mara the lamp still burns" in settings["objective"]
    # Quoted, so the monitor matches the phrase rather than its words.
    assert settings["search_queries"] == ['"Tell Mara the lamp still burns"']
    assert body["metadata"]["workflow"] == "last-seen-alive-cold-case"


# ------------------------------------------------------------------ shared

def test_every_surface_reaches_the_documented_parallel_host(wire: Wire) -> None:
    """No surface may be pointed at anything but Parallel's API."""
    research.search_archival_evidence("o", ["a", "b"])
    research.deep_holdings_research("q")
    research.census_named_catalogues("T", "1921")
    verify.audit_citations_with_extract([("https://a.example.org/x", "q")])
    verify.open_cold_case_monitor(fragment_label="r", rare_strings=["a long enough string here"])

    hosts = {httpx.URL(url).host for _m, url, _b in wire.calls}
    assert hosts == {"api.parallel.ai"}, hosts
    assert len(wire.calls) >= 6
