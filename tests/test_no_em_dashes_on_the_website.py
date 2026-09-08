"""The served website contains no em dashes.

An editorial rule the owner asked for, kept by a test because prose drifts and
seventy-eight of them had already accumulated across ten files. Checking is
cheap; re-reading every page before each deploy is not.

The check unescapes HTML entities first. A rule that `&mdash;` slips past is not
a rule, and that exact class of gap had already let a stale latency figure
survive one sweep written as `40&ndash;120`.

En dashes are deliberately allowed. They carry meaning in a numeric range
("1912-1929", "23-30 percent"), they are correct typography rather than a
stylistic tic, and removing them would make ranges harder to read.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "app" / "web"
PAGES = sorted(
    [path for path in WEB.iterdir() if path.suffix in {".html", ".js", ".css"}],
    key=lambda p: p.name,
)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_no_em_dash_survives_on_any_served_file(page: Path) -> None:
    text = html.unescape(page.read_text(encoding="utf-8"))
    if "\u2014" not in text:
        return

    where = []
    for match in re.finditer("\u2014", text):
        line = text.count("\n", 0, match.start()) + 1
        start = max(0, match.start() - 45)
        where.append(f"    line {line}: ...{text[start:match.end() + 45]}...")
    pytest.fail(
        f"{page.name} contains {len(where)} em dash(es). Rewrite the sentence rather "
        f"than substituting a character: a colon where the clause amplifies, a comma "
        f"where it is parenthetical, a full stop where it is a new thought.\n"
        + "\n".join(where)
    )


def test_the_pages_were_actually_checked() -> None:
    """A parametrised test over an empty list passes and proves nothing."""
    assert len(PAGES) >= 10, f"expected the full website, found {len(PAGES)} files"
