"""Reject preservation claims that exceed what catalogue searching can establish.

Searching every catalogue you can name tells you where a print *is*. It can never
tell you that no other print exists: unlisted holdings, private collections and
uncatalogued cans are exactly the material this field keeps rediscovering. So
"last surviving copy" is not a strong claim here, it is an unsupportable one, and
an archive that acted on it could deaccession the wrong thing.

The permitted formulation names the catalogues searched and the date searched.
"""

from __future__ import annotations

import re
from typing import Any

_FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\blast (?:known )?(?:surviving )?(?:copy|print|reel|element)\b", re.IGNORECASE),
        "last_copy",
    ),
    (re.compile(r"\bonly (?:known )?surviving\b", re.IGNORECASE), "only_surviving"),
    (
        re.compile(r"\b(?:the )?sole (?:copy|print|reel|element|survivor)\b", re.IGNORECASE),
        "sole_copy",
    ),
    (re.compile(r"\bpresumed lost\b", re.IGNORECASE), "presumed_lost"),
    (re.compile(r"\bno other (?:copy|print) (?:exists|survives)\b", re.IGNORECASE), "no_other_copy"),
    (re.compile(r"\bnowhere else\b", re.IGNORECASE), "nowhere_else"),
)

PERMITTED_FORMULATION = (
    "No additional holding was found across these named catalogues as of this search date."
)


def assert_permitted_holdings_language(text: str) -> str:
    """Raise if the text makes a survival claim catalogue searching cannot support."""
    for pattern, _name in _FORBIDDEN:
        if pattern.search(text):
            raise ValueError(
                "Unsupported survival claim. State the named catalogues and search date instead."
            )
    return text


def find_prohibited_language(value: Any) -> list[dict[str, str]]:
    """Walk any nested agent output and report every unsupportable survival claim.

    Non-raising, because this runs over live model output during an investigation
    where the right response is to flag the sentence to the archivist and refuse
    to let it stand as evidence, not to discard the whole run.
    """

    findings: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def walk(node: Any, path: str) -> None:
        if isinstance(node, str):
            for pattern, name in _FORBIDDEN:
                match = pattern.search(node)
                if not match:
                    continue
                start = max(0, match.start() - 90)
                snippet = node[start : match.end() + 90].strip()
                key = (name, snippet)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    {
                        "rule": name,
                        "matched": match.group(0),
                        "where": path,
                        "context": snippet,
                        "permitted_instead": PERMITTED_FORMULATION,
                    }
                )
        elif isinstance(node, dict):
            for key, item in node.items():
                walk(item, f"{path}.{key}" if path else str(key))
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value, "")
    return findings
