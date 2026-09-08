"""Drive a real browser through docs/DEMO-SCRIPT.md, beat by beat, and report anything broken.

Curl proves an endpoint answers. It does not prove the page renders, that a
button exists where the script says to click, that a JS exception did not leave a
section blank, or that a control is reachable without hunting for it. Three of
the four errors already found in the demo script were exactly that kind, and they
would have been found on camera.

So this opens the deployed site, follows every NAVIGATE / POINT AT / DO in the
script in order, asserts what the presenter is told to look for is actually
visible, clicks what they are told to click, and fails loudly with a screenshot
if it is not there.

    python scripts/walk_demo.py
    python scripts/walk_demo.py --headed          # watch it happen
    python scripts/walk_demo.py https://your-deployment.example

It deliberately does NOT press Investigate. That is a real five-minute
investigation costing partner credit, and the script itself tells the presenter
to cut away from it. Everything up to and including the button is checked.

Screenshots land in eval/reports/demo-walk/ so the shots can be reviewed before
recording rather than after.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "eval" / "reports" / "demo-walk"
BASE = "https://last-seen-alive-109051079423.us-central1.run.app"

problems: list[str] = []
console_errors: list[str] = []


def check(ok: bool, what: str, detail: str = "") -> bool:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        problems.append(f"{what}{f' [{detail}]' if detail else ''}")
    return ok


def beat(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def main() -> int:
    global BASE
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        BASE = args[0].rstrip("/")
    headed = "--headed" in sys.argv
    SHOTS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        # The script tells the presenter to use ~1440px and the light theme.
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                color_scheme="light")
        page.set_default_timeout(20_000)

        page.on("console", lambda m: console_errors.append(f"{page.url} :: {m.text}")
                if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"{page.url} :: {e}"))

        def shot(name: str) -> None:
            page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False)

        # ---------------------------------------------------- 0:00 the problem
        beat("0:00-0:25  The problem, then what you built")
        page.goto(BASE, wait_until="networkidle")
        check(page.locator("h1").first.is_visible(), "landing h1 renders")
        check("Most of it is already gone" in page.content(), "the scale section exists")
        page.locator("#scale-title").scroll_into_view_if_needed()
        check(page.locator(".pullquote blockquote").first.is_visible(),
              "Billington pull quote is visible after scrolling")
        rows = page.locator("#scale-title ~ .table-scroll table tbody tr")
        check(rows.count() == 3, "Mostly Lost table has its three years", f"{rows.count()}")
        for pct in ("23%", "29%", "30%"):
            check(pct in page.content(), f"hit rate {pct} on screen")
        strip = page.locator(".fact-strip").inner_text()
        check("0 identities asserted" in strip,
              "masthead states the guarantee that held", strip.replace("\n", " ")[:70])
        check("0 false-confident" not in strip,
              "masthead no longer advertises the falsified metric")
        shot("00-problem")

        # ------------------------------------------------- 0:25 why it is hard
        beat("0:25-0:42  Why it is hard  (/presets)")
        page.click('.site-nav a[href="/presets"]')
        page.wait_for_load_state("networkidle")
        check(page.url.endswith("/presets"), "nav link reaches Fragments", page.url)
        cards = page.locator(".presetcard")
        check(cards.count() == 10, "ten fragments render", f"{cards.count()}")
        # Badges are uppercased by CSS, so compare case-insensitively.
        body = page.inner_text("main").lower()
        counts = {w: body.count(w.lower()) for w in
                  ("Probable identity", "Abstain", "Ranked candidates only",
                   "Contradict the supplied label")}
        check(counts["Probable identity"] == 5,
              "five cases badged Probable identity, as the narration says",
              str(counts))
        check(sum(counts.values()) >= 10, "every case carries an outcome badge", str(counts))
        check("sealed" in body, "the held-out five are visibly sealed")
        shot("01-presets")

        # -------------------------------------------------- 0:42 start a run
        beat("0:42-1:05  Start a real run  (landing)")
        page.click('.site-nav a[href="/"]')
        page.wait_for_load_state("networkidle")
        page.locator("#try-title").scroll_into_view_if_needed()
        tab = page.locator("#tab-preset")
        check(tab.is_visible(), "the 'Public demo fragment' tab is visible")
        check(tab.get_attribute("aria-selected") == "true",
              "that tab is already selected, so no click is needed")
        select = page.locator("select#preset")
        if not select.count():
            select = page.locator("[data-preset-select], select").first
        check(select.count() > 0, "the fragment dropdown exists")
        options = select.locator("option").all_inner_texts()
        check(len(options) == 5, "only the five development cases are offered",
              f"{len(options)}: {options}")
        check(select.input_value() == "D02",
              "dropdown defaults to D02, so D04 must be chosen deliberately",
              select.input_value())
        d04 = [o for o in options if o.startswith("D04")]
        check(bool(d04), "a D04 option exists", str(options))
        if d04:
            check(d04[0] == "D04 · Distinctive visual · expects probable identity",
                  "the D04 option reads exactly as the script says", d04[0])
        select.select_option("D04")
        check(select.input_value() == "D04", "selecting D04 works")
        btn = page.get_by_role("button", name="Investigate this fragment")
        check(btn.count() > 0 and btn.first.is_visible(),
              "the button is labelled 'Investigate this fragment'")
        note = page.locator(".run-empty, [data-run-events]").first.inner_text()
        check("minutes" in note.lower() or "run" in note.lower(),
              "the run panel sets a duration expectation before you press it",
              note.replace("\n", " ")[:80])
        shot("02-run-selected-d04")
        print("  (deliberately not pressing Investigate: five real minutes and partner credit)")

        # ------------------------------------------------------ 1:05 dossiers
        beat("1:05-1:50  The dossier  (/dossiers, D04)")
        page.click('.site-nav a[href="/dossiers"]')
        page.wait_for_load_state("networkidle")
        picks = page.locator(".dossier-pick")
        check(picks.count() == 5, "five dossier cards render", f"{picks.count()}")
        first = picks.first.inner_text()
        check(first.strip() != "" and len(first.split("\n")) >= 3,
              "cards are not blank", repr(first[:60]))
        page.locator('.dossier-pick[data-case="D04"]').click()
        page.wait_for_timeout(1500)
        board = page.locator("[data-dossier-board]").inner_text()
        check("Un coin de Paris" in board,
              "D04's wrong leading candidate is on screen, as the script says")
        check("refused" in board.lower(),
              "the refused citation is rendered and labelled")
        check("human_approved" in board, "the failing human_approved threshold is visible")
        refused = page.locator(".srcrow.refused, [data-refused], .srcrow").count()
        check(refused > 0, "source rows render", f"{refused}")
        shot("03-dossier-d04")

        # ---------------------------------------------------- 1:50 evaluation
        beat("1:50-2:20  The stability study  (landing table -> /evaluation)")
        page.click('.site-nav a[href="/"]')
        page.wait_for_load_state("networkidle")
        page.locator("#eval-title").scroll_into_view_if_needed()
        link = page.get_by_role("link", name="See every run, case by case")
        check(link.count() > 0, "the caption link the script tells you to click exists")
        link.first.click()
        page.wait_for_load_state("networkidle")
        check(page.url.endswith("/evaluation"), "it lands on /evaluation", page.url)
        page.wait_for_timeout(1500)
        metrics = page.locator("[data-eval-headline] .metric")
        check(metrics.count() >= 5, "the headline metrics rendered from the API",
              f"{metrics.count()}")
        main_text = page.inner_text("main")
        check("28" in main_text, "the 28-run figure is on the page")
        cases = page.locator("[data-eval-cases] .card")
        check(cases.count() == 5, "one card per case", f"{cases.count()}")
        run_rows = page.locator("[data-eval-cases] tbody tr")
        check(run_rows.count() == 28, "every one of the 28 runs is listed",
              f"{run_rows.count()}")
        check("Un coin de Paris" in main_text, "D04's wrong answers are shown by name")
        check(page.locator("[data-eval-fix] table").count() > 0,
              "the before/after table rendered")
        check(page.locator("[data-eval-method] .card").count() >= 3,
              "the scoring method and judgement calls rendered")
        page.locator("[data-eval-cases] .card").nth(3).scroll_into_view_if_needed()
        shot("04-evaluation-d04")

        # ------------------------------------------------------ 2:20 practice
        beat("2:20-2:32  The review we could not get  (/practice)")
        page.click('.site-nav a[href="/practice"]')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        text = page.inner_text("main")
        check("unanswered" in text.lower(), "the Unanswered group rendered")
        cards = page.locator("[data-practice-register] .obj")
        check(cards.count() == 14, "all fourteen entries rendered", f"{cards.count()}")
        first_group = page.locator("[data-practice-register] .subhead").first.inner_text()
        check(first_group.strip().lower() == "unanswered",
              "Unanswered renders first, above what the system does well", first_group)
        ids = [c.inner_text().split("\n")[0] for c in cards.all()[:4]]
        check("P5" in " ".join(ids), "P5 is inside the first group", str(ids))
        shot("05-practice")

        # ----------------------------------------------------------- 2:32 api
        beat("2:32-2:50  It is a product  (/api, then /stack)")
        page.click('.site-nav a[href="/api"]')
        page.wait_for_load_state("networkidle")
        mint = page.get_by_role("button", name="Mint a 60-day judge key")
        check(mint.count() > 0, "the mint button is labelled as the script says")
        mint.first.click()
        page.wait_for_timeout(3000)
        keyout = page.locator("[data-key-output]").inner_text()
        check(keyout.startswith("lsa_"), "a real key was minted on camera", keyout[:24])
        page.locator("select#endpoint").select_option("GET /v1/stack")
        page.get_by_role("button", name="Send request").click()
        page.wait_for_timeout(4000)
        out = page.locator("[data-out]").inner_text()
        check(len(out) > 200 and ("parallel" in out.lower() or "google" in out.lower()),
              "the live response rendered in the panel", out[:60].replace("\n", " "))
        shot("06-api-key-and-response")

        page.click('.site-nav a[href="/stack"]')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        rows = page.locator("[data-stack-table] tbody tr, .stackrow")
        check(rows.count() >= 11, "eleven sponsor surfaces render with their call sites",
              f"{rows.count()}")
        shot("07-stack-close")

        # ------------------------------------------------------- global checks
        beat("Across every page")
        for path in ("/", "/presets", "/dossiers", "/evaluation", "/practice", "/api", "/stack"):
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(600)
            nav = page.locator(".site-nav a").all_inner_texts()
            check(len(nav) == 7, f"{path}: seven nav links", str(nav))
            check("—" not in page.inner_text("body"),
                  f"{path}: no em dash visible to a viewer")
            check(page.evaluate("document.body.scrollWidth <= window.innerWidth + 2"),
                  f"{path}: no horizontal scroll at 1440px")

        browser.close()

    beat("Result")
    if console_errors:
        print(f"  {len(console_errors)} console/page error(s):")
        for e in console_errors[:12]:
            print("     ", e[:160])
        problems.extend(console_errors[:12])
    else:
        print("  no JavaScript errors on any page")
    print(f"\n  screenshots: {SHOTS}")
    print(f"  problems: {len(problems)}")
    for p in problems:
        print("   -", p[:150])
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
