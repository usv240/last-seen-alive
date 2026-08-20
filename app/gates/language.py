"""Reject preservation claims that exceed what catalogue searching can establish."""

from __future__ import annotations

import re

_FORBIDDEN = (
    re.compile(r"\blast (?:surviving )?(?:copy|print|reel)\b", re.IGNORECASE),
    re.compile(r"\bonly surviving\b", re.IGNORECASE),
    re.compile(r"\b(?:the )?sole (?:copy|print|reel|survivor)\b", re.IGNORECASE),
)


def assert_permitted_holdings_language(text: str) -> str:
    for pattern in _FORBIDDEN:
        if pattern.search(text):
            raise ValueError(
                "Unsupported survival claim. State the named catalogues and search date instead."
            )
    return text

