"""Shared Parallel client, session identity, and source policy.

One investigation is one Parallel *session*. Parallel uses `session_id` to relate
the calls an agent makes while working on a single task, so every surface we
touch during one fragment investigation carries the same id. That is what makes
the retrieval record in `citation_registry.py` a record of one investigation
rather than a pile of unrelated requests.
"""

from __future__ import annotations

import os
import uuid
from contextvars import ContextVar

from parallel import Parallel

#: Domains that recycle plot summaries and each other's text. Excluding them from
#: research keeps the "three independent domains" threshold meaningful: three
#: mirrors of the same summary are one source, not three.
RECYCLED_CONTENT_DOMAINS = (
    "pinterest.com",
    "quora.com",
    "answers.com",
    "ranker.com",
    "fandom.com",
)

#: Where film-historical primary evidence actually lives. Used to *prefer*, never
#: to restrict: a rare intertitle can surface anywhere, so Search stays open and
#: only the deep holdings Task is pointed at institutional sources.
ARCHIVAL_SOURCE_DOMAINS = (
    ".gov",
    ".edu",
    ".ac.uk",
    "loc.gov",
    "archive.org",
    "bfi.org.uk",
    "eyefilm.nl",
    "filmportal.de",
    "cinematheque.fr",
    "nfsa.gov.au",
    "silentera.com",
    "afi.com",
    "imdb.com",
    "wikidata.org",
    "europeanfilmgateway.eu",
    "filmarchives-online.eu",
    "mediahistoryproject.org",
    "lantern.mediahist.org",
)

_SESSION: ContextVar[str | None] = ContextVar("parallel_session", default=None)


class ParallelNotConfigured(RuntimeError):
    """Raised when a Parallel call is attempted with no credential.

    Deliberately a hard error. Parallel is the only open-web path in this
    product; if it is absent the investigation must stop, not fall back to model
    memory and present recalled text as retrieved evidence.
    """


def start_session() -> str:
    """Begin one investigation's Parallel session and return its id."""
    session_id = f"lsa_{uuid.uuid4().hex}"
    _SESSION.set(session_id)
    return session_id


def current_session() -> str | None:
    return _SESSION.get()


def is_configured() -> bool:
    return bool(os.environ.get("PARALLEL_API_KEY"))


def client() -> Parallel:
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        raise ParallelNotConfigured(
            "PARALLEL_API_KEY is required; Parallel is the only open-web path and "
            "this workflow will not fall back to model memory."
        )
    return Parallel(api_key=api_key)
