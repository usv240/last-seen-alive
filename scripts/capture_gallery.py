"""Capture the project gallery screenshots, framed and sized for Devpost.

Devpost asks for a 3:2 ratio, so the viewport is 1440x960 and every shot is the
viewport rather than the full page. A full-page capture of a dossier is six
screens tall and unreadable as a thumbnail.

Order matters: the first image is the cover in the gallery, so it leads with what
the product is, and the sequence afterwards tells the same story the site does.

    python scripts/capture_gallery.py
    python scripts/capture_gallery.py --with-run   # also captures a live run console

`--with-run` presses Investigate and captures the console a few seconds in. That
starts a real five-minute investigation which we abandon, so it costs one run of
partner credit. Worth it for one screenshot: the six named stages with a live
clock are the clearest picture of the architecture anywhere in the product.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "reports" / "gallery"
BASE = "https://last-seen-alive-109051079423.us-central1.run.app"

#: 3:2, and wide enough that the stack ribbon sits on two tidy rows.
WIDTH, HEIGHT = 1440, 960


def main() -> int:
    base = next((a for a in sys.argv[1:] if a.startswith("http")), BASE).rstrip("/")
    with_run = "--with-run" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    shots: list[tuple[str, str]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT},
                                color_scheme="light", device_scale_factor=2)
        page.set_default_timeout(30_000)

        def shot(name: str, caption: str) -> None:
            page.screenshot(path=str(OUT / f"{name}.png"))
            shots.append((f"{name}.png", caption))
            print(f"  captured  {name}.png")

        def go(path: str, settle: int = 1800) -> None:
            page.goto(base + path, wait_until="networkidle")
            page.wait_for_timeout(settle)

        def frame(selector: str, top: int = 200, nth: int = 0) -> None:
            """Put an element's top edge at a fixed distance from the viewport top.

            scroll_into_view_if_needed only guarantees visibility, so it can leave
            the target at the bottom of the screen with the interesting content
            below the fold. Positioning it explicitly is the difference between a
            screenshot of a section and a screenshot of the gap above it.
            """
            page.evaluate(
                """([sel, top, nth]) => {
                    const el = document.querySelectorAll(sel)[nth];
                    if (!el) return;
                    const y = el.getBoundingClientRect().top + window.scrollY - top;
                    window.scrollTo({top: Math.max(0, y), behavior: 'instant'});
                }""",
                [selector, top, nth],
            )
            page.wait_for_timeout(600)

        # 1 ------------------------------------------------- the cover
        go("/")
        shot("01-what-it-is",
             "A reel arrives with no name. This works out what it might be, and says so only when the evidence holds up.")

        # 2 ------------------------------------------------- the route
        frame("#path-title", top=170)
        shot("02-start-here",
             "Three pages, in order. Watch a fragment, read what it found, then see where it got things wrong.")

        # 3 ------------------------------------------------- the cited problem
        frame("#scale-title", top=170)
        shot("03-the-problem",
             "Only 14% of American silent features survive. The experts who identify them get under a third of what they screen.")

        # 4 ------------------------------------------------- the corpus
        go("/presets")
        frame(".presetcard", top=180)
        shot("04-ten-fragments",
             "Ten real fragments. Five should be identified, five should not, and five more stay sealed so results cannot be tuned.")

        # 5 ------------------------------------------------- real footage
        go("/presets")
        try:
            frame("video", top=170)
            page.wait_for_timeout(900)
            shot("05-real-footage",
             "Every fragment plays in the browser, downloads in one click, and carries its Library of Congress credit.")
        except Exception as exc:
            print("  skipped 05 (no video element):", exc)

        # 6 ------------------------------------------------- the dossier
        go("/dossiers#D04", settle=2600)
        frame(".verdict", top=150)
        shot("06-the-verdict",
             "A dossier, not an answer. Nine thresholds, each shown whether it passed or failed, decided by code.")

        # 7 ------------------------------------------------- the refused citation
        try:
            frame(".boardcol h3", top=170, nth=1)   # the "Rejected citations" heading
            shot("07-refused-citation",
             "Every cited page is reopened and checked for the quoted words. These were not there, so the gate threw them out.")
        except Exception as exc:
            print("  skipped 07:", exc)

        # 8 ------------------------------------------------- it was wrong
        try:
            frame("details.claim[open]", top=180, nth=1)
            shot("08-evidence-both-ways",
             "Evidence for and against, side by side. One source confirmed on the live page, one refused, both left visible.")
        except Exception as exc:
            print("  skipped 08:", exc)

        # 9 ------------------------------------------------- the study
        go("/evaluation", settle=2600)
        frame("#headline-title", top=170)
        shot("09-28-runs",
             "We ran it 28 times and published every run. Nine named the wrong film. None ever claimed a probable identity.")

        # 10 ------------------------------------------------ per case
        try:
            frame("[data-eval-cases] .card", top=170, nth=3)
            shot("10-every-run",
             "Every run, case by case, with the candidate it produced and how that scored against the sealed answer key.")
        except Exception as exc:
            print("  skipped 10:", exc)

        # 11 ------------------------------------------------ the fix that half worked
        try:
            frame("#fix-title", top=170)
            shot("11-fix-comparison",
             "Two defects found and fixed. Only one improved the results, and we published the one that did not.")
        except Exception as exc:
            print("  skipped 11:", exc)

        # 12 ------------------------------------------------ the review we could not get
        go("/practice", settle=2400)
        frame("#register-title", top=170)
        shot("12-practitioner-register",
             "No archivist has reviewed this, so we answered 14 demands they already published. The four we miss come first.")

        # 13 ------------------------------------------------ the stack
        go("/stack", settle=2000)
        frame(".stackrow", top=180)
        shot("13-eleven-surfaces",
             "Eleven sponsor surfaces, each with the job it does, the code that calls it, and whether it is live right now.")

        # 14 ------------------------------------------------ it is a product
        go("/api", settle=1600)
        page.get_by_role("button", name="Mint a 60-day judge key").click()
        page.wait_for_timeout(3000)
        page.get_by_role("button", name="Send request").click()
        page.wait_for_timeout(4000)
        frame("#play-title", top=170)
        shot("14-live-api",
             "No signup. Mint a key with no email and call the same public endpoints this page calls.")

        # optional ------------------------------------------ the run console
        if with_run:
            go("/", settle=1500)
            page.locator("#try-title").scroll_into_view_if_needed()
            page.locator("select#preset").select_option("D04")
            page.get_by_role("button", name="Investigate this fragment").click()
            page.wait_for_timeout(9000)
            frame("#run-title", top=170)
            shot("15-run-console",
             "The wait explains itself: six named stages, which agent owns each one, and a real elapsed clock.")

        browser.close()

    index = OUT / "CAPTIONS.md"
    lines = ["# Gallery captions", "",
             "Upload in this order. The first image is the gallery cover.", ""]
    for i, (name, caption) in enumerate(shots, 1):
        lines.append(f"**{i}. `{name}`**")
        lines.append(f"> {caption}")
        lines.append("")
    index.write_text("\n".join(lines), encoding="utf-8")

    total = sum(f.stat().st_size for f in OUT.glob("*.png"))
    print(f"\n  {len(shots)} screenshots in {OUT}")
    print(f"  captions: {index}")
    print(f"  total size: {total/1_048_576:.1f} MB "
          f"(largest {max(f.stat().st_size for f in OUT.glob('*.png'))/1_048_576:.2f} MB, limit 5 MB each)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
