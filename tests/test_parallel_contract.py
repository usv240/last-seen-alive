import pytest

from app.partners.parallel_research import search_archival_evidence


def test_parallel_search_rejects_too_few_queries_before_network() -> None:
    with pytest.raises(ValueError, match="two to five"):
        search_archival_evidence("Find an archival identity", ["one query"])


def test_parallel_search_rejects_oversized_query_before_network() -> None:
    with pytest.raises(ValueError, match="200"):
        search_archival_evidence("Find an archival identity", ["a" * 201, "second query"])

