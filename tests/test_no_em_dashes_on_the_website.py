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

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "web"

#: Python modules whose strings are served to the browser and rendered as page
#: text. The first sweep missed these entirely, and a browser walkthrough found
#: em dashes still on /presets and /stack because of it: the pages were clean and
#: the data feeding them was not.
SERVED_DATA = [
    ROOT / "app" / "presets.py",
    ROOT / "app" / "stack.py",
    ROOT / "app" / "standards.py",
    ROOT / "app" / "practice.py",
    ROOT / "app" / "api" / "main.py",
]

PAGES = sorted(
    [path for path in WEB.iterdir() if path.suffix in {".html", ".js", ".css"}],
    key=lambda p: p.name,
) + [path for path in SERVED_DATA if path.exists()]


#: The same character in every spelling that has actually got through. The
#: literal survived the first sweep inside Python data files that feed the API,
#: `&mdash;` survived the second in HTML, and the JS escape survived the third
#: inside a template string in common.js. A check that knows one spelling is not
#: a check, and each of those reached the deployed site.
ESCAPES = ("\\u2014", "\\U00002014", "&#8212;", "&#x2014;")


def decoded(page: Path) -> str:
    text = html.unescape(page.read_text(encoding="utf-8"))
    for escape in ESCAPES:
        text = text.replace(escape, "\u2014")
    return text


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_no_em_dash_survives_on_any_served_file(page: Path) -> None:
    text = decoded(page)
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
    assert len(PAGES) >= 15, f"expected the website and its data, found {len(PAGES)} files"
