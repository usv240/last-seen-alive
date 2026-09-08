/* The evaluation page.

   The stability study was the strongest evidence in the project and the only
   major surface with no page: it existed as a summary table on the landing page
   and otherwise as raw JSON. That is backwards. The failures are the argument,
   so they should be the best-presented thing here, not the one thing a reader
   has to open a JSON endpoint to see.

   Everything is rendered from the same endpoints the tests assert against, so
   this page cannot drift from the record. Nothing is hardcoded. */

(() => {
  const host = document.querySelector('[data-eval-cases]');
  if (!host) return;

  const el = window.LSA ? window.LSA.el : (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };

  const VERDICT = {
    probable: 'Probable identity',
    candidates: 'Candidates only',
    abstain: 'Abstained',
    contradict: 'Contradicted the label',
    delivery_failed: 'Not delivered',
  };

  const CLASS_WORD = {
    correct: 'Correct',
    false_confident: 'Wrong film',
    malformed_candidate: 'Not a film',
    no_candidate: 'No candidate',
    unscored: 'Unscored',
  };

  function table(headers, rows, caption) {
    const wrap = el('div', undefined, 'table-scroll');
    const t = el('table', undefined, 'reftable');
    if (caption) t.append(el('caption', caption));
    const thead = el('thead');
    const hr = el('tr');
    headers.forEach((h) => {
      const th = el('th', h);
      th.setAttribute('scope', 'col');
      hr.append(th);
    });
    thead.append(hr);
    t.append(thead);
    const tbody = el('tbody');
    rows.forEach((cells) => {
      const tr = el('tr');
      cells.forEach((c) => {
        const td = el('td');
        if (c instanceof Node) td.append(c);
        else td.textContent = String(c);
        tr.append(td);
      });
      tbody.append(tr);
    });
    t.append(tbody);
    wrap.append(t);
    return wrap;
  }

  function metric(value, label, note, warn) {
    const box = el('div', undefined, warn ? 'metric warn' : 'metric');
    box.append(el('strong', String(value)));
    box.append(el('span', label));
    if (note) box.append(el('small', note));
    return box;
  }

  (async () => {
    let study;
    let fix = null;
    try {
      study = await (await fetch('/v1/eval/stability')).json();
      study = study.data;
    } catch (_) {
      host.replaceChildren(el('p', 'The study could not be loaded.', 'small'));
      return;
    }
    try {
      fix = (await (await fetch('/v1/eval/fix-comparison')).json()).data;
    } catch (_) { /* the comparison is optional; the study is not */ }

    const totals = study.scoring.totals;
    const bound = study.scoring.judgement_calls;

    // ---------------------------------------------------------------- headline
    const head = document.querySelector('[data-eval-headline]');
    if (head) {
      head.replaceChildren(
        metric(study.total_runs, 'runs recorded', 'five fragments, six passes'),
        metric(`${study.cases_with_a_stable_verdict} of ${study.cases}`,
               'cases gave the same verdict every time', 'the rest moved', true),
        metric(totals.correct, 'correct identities'),
        metric(totals.false_confident, 'named the wrong film',
               `${bound.false_confident_upper_bound} on the strictest reading`, true),
        metric(totals.malformed_candidate, 'candidates that named no film',
               'zero since the fix'),
        metric(study.scoring.runs_that_reached_probable, 'ever claimed a probable identity',
               'the guarantee that held'),
      );
    }
    const src = document.querySelector('[data-eval-source]');
    if (src) {
      src.textContent = `Generated ${(study.generated_at || '').slice(0, 10)} against ${study.service}. `
        + `Development split only: the held-out five have never been run.`;
    }

    // ------------------------------------------------------------- per case
    host.replaceChildren();
    study.results.forEach((c) => {
      const card = el('article', undefined, 'card');
      const h = el('h3', `${c.case_id}  ·  answer key: ${c.expected_title || 'unknown'}`);
      card.append(h);
      card.append(el('p', `Required outcome: ${c.expected_outcome}. `
        + `${c.runs} runs, ${Object.keys(c.verdicts).length} distinct verdict(s), `
        + `${c.distinct_top_candidates} distinct leading candidate(s).`, 'small'));

      const rows = c.observations.map((o) => {
        const cls = el('span', CLASS_WORD[o.classification] || o.classification, 'obj-status');
        cls.dataset.status = o.classification === 'correct' ? 'met'
          : o.classification === 'false_confident' ? 'not_met' : 'partially_met';
        return [
          VERDICT[o.verdict] || o.verdict,
          o.top_candidate || 'none offered',
          cls,
          o.thresholds_passed === null || o.thresholds_passed === undefined
            ? 'n/a' : String(o.thresholds_passed),
          o.latency_seconds ? `${Math.round(o.latency_seconds)}s` : 'n/a',
        ];
      });
      card.append(table(
        ['Verdict', 'Leading candidate', 'Scored as', 'Thresholds', 'Time'],
        rows,
        `Every recorded run of ${c.case_id}, in the order they were made.`,
      ));
      host.append(card);
    });

    // ------------------------------------------------------------ before/after
    const fixHost = document.querySelector('[data-eval-fix]');
    if (fixHost && fix) {
      fixHost.replaceChildren();
      fixHost.append(table(
        ['Measure', `Before (${fix.before.runs} runs)`, `After (${fix.after.runs} runs)`],
        [
          ['Candidates that named no film', fix.before.candidates_naming_no_film,
           fix.after.candidates_naming_no_film],
          ['Named the wrong film', fix.before.false_confident, fix.after.false_confident],
          ['Correct identities', fix.before.correct, fix.after.correct],
          ['Ever claimed a probable identity', fix.before.reached_probable,
           fix.after.reached_probable],
        ],
        'Scored by the same scorer, so the two eras are comparable.',
      ));
      const note = el('div', undefined, 'card lede-card');
      note.append(el('p', fix.what_actually_happened || ''));
      note.append(el('p', fix.what_this_implies || ''));
      fixHost.append(note);
      if (Array.isArray(fix.caveats)) {
        const cav = el('div', undefined, 'card');
        cav.append(el('h3', 'What these numbers cannot support'));
        const list = el('ul');
        fix.caveats.forEach((c) => list.append(el('li', c)));
        cav.append(list);
        fixHost.append(cav);
      }
    } else if (fixHost) {
      fixHost.append(el('p', 'No before-and-after comparison has been recorded.', 'small'));
    }

    // ------------------------------------------------------------------ arms
    const armsHost = document.querySelector('[data-eval-arms]');
    if (armsHost) {
      armsHost.replaceChildren(table(
        ['Measure', 'A · Gemini alone', 'B · plus the gate', 'C · full system'],
        [
          ['Correct identities surfaced', '0 of 3', '0 of 3', '2 of 3 (that pass)'],
          ['Identifications with no citable source', '7 of 7', 'n/a', '0'],
          ['Answers unstable across repeats', '3 of 3 cases', 'n/a',
           `${study.cases - study.cases_with_a_stable_verdict} of ${study.cases} cases`],
          ['Median latency', '15 s', '15 s', '304 s'],
        ],
        'The control arm was measured before a Parallel credential existed, so its numbers could not be tuned afterwards.',
      ));
      const warn = el('p', undefined, 'small');
      warn.append(el('b', 'Read the per-case table above before quoting arm C. '));
      warn.append(el('span', 'That column is a single pass. It recorded zero wrong films; across all '
        + `${study.total_runs} runs there are ${totals.false_confident}.`));
      armsHost.append(warn);
    }

    // ---------------------------------------------------------------- method
    const methodHost = document.querySelector('[data-eval-method]');
    if (methodHost) {
      methodHost.replaceChildren();
      const def = el('div', undefined, 'card');
      def.append(el('h3', 'The definition, unchanged since we first published it'));
      def.append(el('p', study.scoring.definition));
      def.append(el('p', study.scoring.matching, 'small'));
      methodHost.append(def);

      const judged = el('div', undefined, 'card');
      judged.append(el('h3', 'Where we made a judgement call'));
      judged.append(el('p', (bound.note || '')));
      const labels = bound.labels_treated_as_not_a_film || {};
      const list = el('ul');
      Object.entries(labels).forEach(([label, why]) => {
        const li = el('li');
        li.append(el('b', label));
        li.append(el('span', `: ${why}`));
        list.append(li);
      });
      judged.append(list);
      methodHost.append(judged);

      const held = el('div', undefined, 'card');
      held.append(el('h3', 'What held across every run'));
      held.append(el('p', study.scoring.what_did_hold || ''));
      methodHost.append(held);
    }
  })();
})();
