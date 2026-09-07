"""All six Parallel surfaces: fail-closed behaviour and the contracts around them.

These run without a network. What is being checked is not that Parallel works —
that is Parallel's job — but that this system cannot quietly stop using it, and
that a citation which does not survive verification cannot carry a verdict.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentic_core.evidence import Claim, Source, stable_claim_id
from app.gates.language import assert_permitted_holdings_language, find_prohibited_language
from app.partners import parallel_client, parallel_research, parallel_verify
from app.partners.citation_registry import CitationRegistry

REAL_URL = "https://www.loc.gov/item/2014600156/"
QUOTE = (
    "the film was released under the former supplied title and later corrected "
    "by the library after a review of the surviving elements and trade notices"
)


# --------------------------------------------------------------- fail closed

@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda: parallel_research.search_archival_evidence("objective", ["one", "two"]),
            id="search",
        ),
        pytest.param(lambda: parallel_research.deep_holdings_research("question"), id="task"),
        pytest.param(
            lambda: parallel_research.census_named_catalogues("A Title", "1921"), id="findall"
        ),
        pytest.param(
            lambda: parallel_verify.audit_citations_with_extract([(REAL_URL, QUOTE)]), id="extract"
        ),
        pytest.param(
            lambda: parallel_verify.falsify_candidates_with_task_group(
                [{"candidate_id": "x", "label": "X"}], visual_summary="s"
            ),
            id="task_group",
        ),
        pytest.param(
            lambda: parallel_verify.open_cold_case_monitor(
                fragment_label="reel", rare_strings=["a long enough visible intertitle string"]
            ),
            id="monitor",
        ),
    ],
)
def test_every_surface_fails_closed_without_a_credential(monkeypatch, call) -> None:
    """No Parallel credential means no answer, on every surface.

    The alternative — degrading to what the model already believes — would let
    recalled text be presented as retrieved evidence, which is the single worst
    thing this product could do.
    """
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    with pytest.raises(parallel_client.ParallelNotConfigured):
        call()


def test_search_validates_query_shape_before_any_network_call() -> None:
    with pytest.raises(ValueError, match="two to five"):
        parallel_research.search_archival_evidence("Find an archival identity", ["one query"])
    with pytest.raises(ValueError, match="200"):
        parallel_research.search_archival_evidence(
            "Find an archival identity", ["a" * 201, "second query"]
        )


# ------------------------------------------------------------ extract audit

class _FakeExtract:
    def __init__(self, results, errors=()):
        self._results = results
        self._errors = list(errors)

    def extract(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            extract_id="extract_test",
            session_id=kwargs.get("session_id") or "sess_test",
            results=self._results,
            errors=self._errors,
        )


def _page(url, full_content, title="A page"):
    return SimpleNamespace(
        url=url, full_content=full_content, excerpts=[], title=title, publish_date=None
    )


def test_extract_audit_confirms_a_quotation_that_is_on_the_live_page(monkeypatch) -> None:
    fake = _FakeExtract([_page(REAL_URL, f"Preamble. {QUOTE}. Postamble.")])
    monkeypatch.setattr(parallel_verify, "client", lambda: fake)

    report = parallel_verify.audit_citations_with_extract([(REAL_URL, QUOTE)])
    assert report["status"] == "completed"
    assert report["audited"][0]["excerpt_present_on_live_page"] is True


def test_extract_audit_flags_a_quotation_that_is_not_on_the_live_page(monkeypatch) -> None:
    fake = _FakeExtract([_page(REAL_URL, "This page is about something else entirely.")])
    monkeypatch.setattr(parallel_verify, "client", lambda: fake)

    report = parallel_verify.audit_citations_with_extract([(REAL_URL, QUOTE)])
    assert report["audited"][0]["excerpt_present_on_live_page"] is False
    assert "not found" in report["audited"][0]["note"]


def test_extract_audit_flags_a_page_that_could_not_be_reopened(monkeypatch) -> None:
    monkeypatch.setattr(parallel_verify, "client", lambda: _FakeExtract([]))
    report = parallel_verify.audit_citations_with_extract([(REAL_URL, QUOTE)])
    assert report["audited"][0]["excerpt_present_on_live_page"] is False


def test_extract_audit_is_bounded(monkeypatch) -> None:
    """A live fetch per citation has to have a ceiling or a demo never returns."""
    captured: dict = {}

    class Recorder(_FakeExtract):
        def extract(self, **kwargs):
            captured.update(kwargs)
            return super().extract(**kwargs)

    monkeypatch.setattr(parallel_verify, "client", lambda: Recorder([]))
    parallel_verify.audit_citations_with_extract(
        [(f"https://example.com/{index}", QUOTE) for index in range(50)]
    )
    assert len(captured["urls"]) == parallel_verify.MAX_AUDITED_URLS


def test_phrase_overlap_accepts_reflowed_text_but_not_unrelated_text() -> None:
    needle = parallel_verify.normalise_text(QUOTE)
    reflowed = parallel_verify.normalise_text(
        "…" + QUOTE.replace(" ", "\n  ") + " and then other material"
    )
    assert parallel_verify._phrase_overlap(needle, reflowed)
    assert not parallel_verify._phrase_overlap(
        needle, parallel_verify.normalise_text("an entirely different sentence about something")
    )


def test_a_source_failing_the_live_audit_cannot_be_decisive() -> None:
    """The whole point of the Extract surface, stated as a test.

    A citation that matched a search snippet but is not on the page today is
    still shown to the archivist. It must not be able to satisfy a threshold.
    """
    passed = Source(
        url=REAL_URL, domain="loc.gov", excerpt=QUOTE, verified=True, live_verified=True
    )
    unaudited = Source(url=REAL_URL, domain="loc.gov", excerpt=QUOTE, verified=True)
    failed = Source(
        url=REAL_URL, domain="loc.gov", excerpt=QUOTE, verified=True, live_verified=False
    )

    def claim(source: Source) -> Claim:
        return Claim(
            claim_id=stable_claim_id("c", "release_date", "text"),
            claim_text="A dated claim.",
            subject="c",
            agent_id="EvidenceCompiler",
            stance="supports",
            sources=(source,),
            confidence_basis="cited",
        )

    assert claim(passed).is_decisive_eligible is True
    assert claim(unaudited).is_decisive_eligible is True
    assert claim(failed).is_decisive_eligible is False
    assert claim(failed).independent_domains == frozenset()


# ----------------------------------------------------------------- findall

def test_findall_census_is_commissioned_not_awaited(monkeypatch) -> None:
    """A census takes minutes to an hour, so the workflow must not block on it.

    Parallel's own console quotes 5-60 minutes for FindAll. Awaiting it inside a
    synchronous investigation made the endpoint unusable, which is exactly the
    kind of thing only a live credential reveals.
    """
    awaited = []
    fake = SimpleNamespace(
        beta=SimpleNamespace(
            findall=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    findall_id="fa_1",
                    generator="base",
                    status=SimpleNamespace(status="queued", is_active=True),
                ),
                result=lambda _id: awaited.append(_id) or SimpleNamespace(candidates=[]),
            )
        )
    )
    monkeypatch.setattr(parallel_research, "client", lambda: fake)
    registry = CitationRegistry()
    monkeypatch.setattr(parallel_research, "active_registry", lambda: registry)

    payload = parallel_research.census_named_catalogues("Through the Breakers", "1928")
    assert awaited == [], "the agent tool must not wait for the census result"
    assert payload["findall_id"] == "fa_1"
    assert payload["collect_at"] == "/v1/census/fa_1"
    assert payload["institutions"] == [], "no institutions are known yet"
    assert "minutes to an hour" in payload["asynchronous"]
    # It still refuses uniqueness language even before it has any results.
    assert_permitted_holdings_language(payload["prohibited_statement"])


def test_collecting_a_finished_census_returns_its_institutions(monkeypatch) -> None:
    fake = SimpleNamespace(
        beta=SimpleNamespace(
            findall=SimpleNamespace(
                retrieve=lambda _id: SimpleNamespace(
                    status=SimpleNamespace(status="completed", is_active=False)
                ),
                result=lambda _id: SimpleNamespace(
                    candidates=[
                        SimpleNamespace(
                            name="Library of Congress",
                            url="https://www.loc.gov/item/123/",
                            match_status="matched",
                            enrichments=None,
                        )
                    ]
                ),
            )
        )
    )
    monkeypatch.setattr(parallel_research, "client", lambda: fake)
    payload = parallel_research.collect_named_catalogue_census("fa_1")
    assert payload["complete"] is True
    assert payload["institutions"][0]["name"] == "Library of Congress"
    assert_permitted_holdings_language(payload["permitted_statement"])


def test_collecting_a_running_census_says_so_rather_than_blocking(monkeypatch) -> None:
    fetched = []
    fake = SimpleNamespace(
        beta=SimpleNamespace(
            findall=SimpleNamespace(
                retrieve=lambda _id: SimpleNamespace(
                    status=SimpleNamespace(status="running", is_active=True)
                ),
                result=lambda _id: fetched.append(_id) or SimpleNamespace(candidates=[]),
            )
        )
    )
    monkeypatch.setattr(parallel_research, "client", lambda: fake)
    payload = parallel_research.collect_named_catalogue_census("fa_1")
    assert payload["complete"] is False
    assert fetched == [], "must not fetch a result that is not ready"
    assert "Poll" in payload["note"]


# ------------------------------------------------------------- task group

def test_task_group_gives_each_candidate_an_independent_run(monkeypatch) -> None:
    submitted: dict = {}

    def add_runs(_group_id, **kwargs):
        submitted.update(kwargs)
        return SimpleNamespace()

    fake = SimpleNamespace(
        task_group=SimpleNamespace(
            create=lambda **_: SimpleNamespace(task_group_id="tg_1"),
            add_runs=add_runs,
            get_runs=lambda _id, **_kw: [
                SimpleNamespace(
                    run=SimpleNamespace(
                        run_id="r1", status="completed", metadata={"candidate_id": "a"}
                    ),
                    output=SimpleNamespace(content={"disproved": False}, basis=[]),
                ),
                SimpleNamespace(
                    run=SimpleNamespace(
                        run_id="r2", status="completed", metadata={"candidate_id": "b"}
                    ),
                    output=SimpleNamespace(content={"disproved": True}, basis=[]),
                ),
            ],
        )
    )
    monkeypatch.setattr(parallel_verify, "client", lambda: fake)

    report = parallel_verify.falsify_candidates_with_task_group(
        [{"candidate_id": "a", "label": "A (1921)"}, {"candidate_id": "b", "label": "B (1922)"}],
        visual_summary="a dark interior",
    )
    assert report["status"] == "completed"
    assert len(submitted["inputs"]) == 2
    assert {v["candidate_id"] for v in report["verdicts"]} == {"a", "b"}
    # Each run is told to disprove, never to argue for, its own candidate.
    for run_input in submitted["inputs"]:
        assert "DISPROVE" in run_input["input"]
        assert "Do not argue for the candidate" in run_input["input"]


def test_task_group_is_bounded(monkeypatch) -> None:
    submitted: dict = {}
    fake = SimpleNamespace(
        task_group=SimpleNamespace(
            create=lambda **_: SimpleNamespace(task_group_id="tg_1"),
            add_runs=lambda _id, **kwargs: submitted.update(kwargs) or SimpleNamespace(),
            get_runs=lambda _id, **_kw: [],
        )
    )
    monkeypatch.setattr(parallel_verify, "client", lambda: fake)
    parallel_verify.falsify_candidates_with_task_group(
        [{"candidate_id": str(i), "label": str(i)} for i in range(20)], visual_summary="s"
    )
    assert len(submitted["inputs"]) == parallel_verify.MAX_FALSIFIED_CANDIDATES


# ---------------------------------------------------------------- monitor

def test_monitor_watches_the_strings_actually_visible_in_the_frame(monkeypatch) -> None:
    captured: dict = {}
    fake = SimpleNamespace(
        monitor=SimpleNamespace(
            create=lambda **kwargs: captured.update(kwargs)
            or SimpleNamespace(monitor_id="mon_1")
        )
    )
    monkeypatch.setattr(parallel_verify, "client", lambda: fake)

    report = parallel_verify.open_cold_case_monitor(
        fragment_label="Unidentified reel, can 41B",
        rare_strings=["Tell Mara the lamp still burns"],
    )
    assert report["status"] == "watching"
    assert report["monitor_id"] == "mon_1"
    assert "Tell Mara the lamp still burns" in captured["settings"]["objective"]


def test_monitor_refuses_to_watch_nothing(monkeypatch) -> None:
    """A monitor on an empty or trivial string is noise an archive would drown in."""
    monkeypatch.setattr(parallel_verify, "client", lambda: pytest.fail("must not call Parallel"))
    report = parallel_verify.open_cold_case_monitor(fragment_label="reel", rare_strings=["", "  "])
    assert report["status"] == "skipped"


def test_rare_strings_prefers_whole_intertitles() -> None:
    clues = {
        "intertitles": ["Tell Mara the lamp still burns tonight", "END"],
        "logos": ["Bray"],
        "nested": [{"note": "a costume of the late Edwardian period is visible"}],
    }
    found = parallel_verify.rare_strings_from_clues(clues)
    assert "Tell Mara the lamp still burns tonight" in found
    assert "END" not in found
    assert "Bray" not in found


# --------------------------------------------------------------- language

def test_prohibited_survival_language_is_found_anywhere_in_the_output() -> None:
    outputs = {
        "holdings_researcher": {
            "summary": "This appears to be the last surviving copy held anywhere.",
            "notes": ["Fine."],
        },
        "skeptic": ["The reel is presumed lost outside this collection."],
    }
    findings = find_prohibited_language(outputs)
    rules = {finding["rule"] for finding in findings}
    assert rules == {"last_copy", "presumed_lost"}
    for finding in findings:
        assert finding["where"]
        assert "named catalogues" in finding["permitted_instead"]


def test_permitted_coverage_formulation_passes() -> None:
    permitted = (
        "No additional holding was found across these named catalogues as of this search date: "
        "Library of Congress, BFI National Archive, EYE Filmmuseum."
    )
    assert assert_permitted_holdings_language(permitted) == permitted
    assert find_prohibited_language(permitted) == []
