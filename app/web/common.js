/* Shared across every page: theme, reading mode, the sponsor stack ribbon,
   API-key handling, and the evidence board renderer.

   The stack ribbon is deliberately on all four pages and reads its contents
   from GET /v1/stack rather than from hardcoded markup, so a service that is
   unavailable is shown as unavailable everywhere at once. */

(() => {
  const root = document.documentElement;
  const safeRead = (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } };
  const safeWrite = (k, v) => { try { localStorage.setItem(k, v); } catch (_) {} };

  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };

  /* ---- reading mode + theme ---------------------------------------- */
  const setMode = (mode) => {
    root.dataset.reading = mode;
    document.querySelectorAll('[data-set-mode]').forEach((b) => {
      b.setAttribute('aria-pressed', String(b.dataset.setMode === mode));
    });
    safeWrite('lsa-reading', mode);
  };
  setMode(safeRead('lsa-reading') === 'technical' ? 'technical' : 'plain');
  document.querySelectorAll('[data-set-mode]').forEach((b) =>
    b.addEventListener('click', () => setMode(b.dataset.setMode)));

  const themeButton = document.querySelector('[data-theme-toggle]');
  const setTheme = (theme) => {
    if (theme === 'dark') root.dataset.theme = 'dark'; else delete root.dataset.theme;
    if (themeButton) themeButton.textContent = theme === 'dark' ? 'Light' : 'Dark';
    safeWrite('lsa-theme', theme);
  };
  setTheme(safeRead('lsa-theme') === 'dark' ? 'dark' : 'light');
  if (themeButton) themeButton.addEventListener('click', () =>
    setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));

  /* ---- API key ------------------------------------------------------
     The site is its own first API consumer. Every run you trigger from these
     pages goes through the same public endpoints, with a real key minted the
     same way yours would be. There is no privileged internal path. */
  const KEY_STORE = 'lsa-api-key';
  const readKey = () => { try { return sessionStorage.getItem(KEY_STORE); } catch (_) { return null; } };
  const writeKey = (v) => { try { sessionStorage.setItem(KEY_STORE, v); } catch (_) {} };

  async function mintKey(force) {
    const existing = !force && readKey();
    if (existing) return existing;
    const response = await fetch('/v1/keys', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ tier: 'judge' }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload?.error?.message || 'Key request failed.');
    writeKey(payload.data.key);
    document.dispatchEvent(new CustomEvent('lsa:key', { detail: payload.data }));
    return payload.data.key;
  }

  async function authedFetch(url, options = {}) {
    const key = await mintKey(false);
    const headers = { ...(options.headers || {}), authorization: `Bearer ${key}` };
    return fetch(url, { ...options, headers });
  }

  /* ---- sponsor stack ribbon ----------------------------------------- */
  const DOT = { live: '', unavailable: 'down', unknown: 'pending' };
  const STATUS_WORD = {
    live: 'reachable now',
    unavailable: 'not reachable',
    unknown: 'status unknown',
  };

  function ribbonGroup(label, entries) {
    const group = el('div', undefined, 'ribbon-group');
    group.append(el('span', label, 'ribbon-label'));
    const list = el('ul', undefined, 'ribbon-list');
    entries.forEach((entry) => {
      const item = el('li', undefined, `ribbon-item ${entry.status}`);
      item.append(el('span', '', `status-dot ${DOT[entry.status] ?? 'pending'}`));
      // Eleven full product names do not fit on one line at any sensible size,
      // so the chip carries a short label and the full one stays in the
      // accessible name and the tooltip.
      item.append(el('span', entry.short || entry.name, 'ribbon-name'));
      // Status is carried by a coloured dot and a tooltip, and neither reaches
      // a screen-reader or keyboard user. Write it into the accessible name.
      item.setAttribute('aria-label', `${entry.vendor} ${entry.name}: ${STATUS_WORD[entry.status] || entry.status}. ${entry.role}`);
      item.title = `${entry.name}: ${entry.status}\n${entry.role}\n${entry.call_site}`;
      list.append(item);
    });
    group.append(list);
    return group;
  }

  async function paintStack() {
    const hosts = document.querySelectorAll('[data-stack-ribbon]');
    const panel = document.querySelector('[data-integration-list]');
    const table = document.querySelector('[data-stack-table]');
    if (!hosts.length && !panel && !table) return;
    let data;
    try {
      const response = await fetch('/v1/stack');
      data = (await response.json()).data;
    } catch (_) {
      hosts.forEach((h) => h.replaceChildren(el('span', 'Stack status unavailable', 'ribbon-label')));
      return;
    }
    window.__lsaStack = data;

    hosts.forEach((host) => {
      host.replaceChildren();
      host.append(ribbonGroup('Google Cloud', data.google_cloud));
      host.append(ribbonGroup('Parallel', data.parallel));
      const link = el('a', 'How each one is used →', 'ribbon-more');
      link.href = '/stack';
      host.append(link);
    });

    if (panel) {
      panel.replaceChildren(...[...data.google_cloud, ...data.parallel].map((entry) => {
        const li = el('li');
        const head = el('div', undefined, 'panel-row');
        head.append(el('span', '', `status-dot ${DOT[entry.status] ?? 'pending'}`));
        head.append(el('b', entry.name));
        head.append(el('span', entry.vendor, 'panel-vendor'));
        li.append(head);
        li.append(el('p', entry.role, 'small'));
        li.append(el('code', entry.call_site));
        return li;
      }));
    }

    if (table) renderStackTable(table, data);
  }

  function renderStackTable(host, data) {
    host.replaceChildren();
    [['Google Cloud', data.google_cloud], ['Parallel', data.parallel]].forEach(([vendor, entries]) => {
      const section = el('section', undefined, 'stack-section');
      const head = el('div', undefined, 'stack-head');
      head.append(el('h2', vendor));
      head.append(el('span', `${entries.length} surfaces`, 'stack-count'));
      section.append(head);
      entries.forEach((entry) => {
        const card = el('article', undefined, `stackrow ${entry.status}`);
        const top = el('div', undefined, 'stackrow-top');
        top.append(el('span', '', `status-dot ${DOT[entry.status] ?? 'pending'}`));
        top.append(el('h3', entry.name));
        if (entry.required) top.append(el('span', 'REQUIRED', 'badge-mini req'));
        top.append(el('span', entry.status, `badge-mini ${entry.status}`));
        card.append(top);
        card.append(el('p', entry.role, 'stackrow-role'));
        if (entry.creative_note) {
          const note = el('p', undefined, 'stackrow-note');
          note.append(el('b', 'Why this way: '));
          note.append(document.createTextNode(entry.creative_note));
          card.append(note);
        }
        const meta = el('div', undefined, 'stackrow-meta');
        if (entry.used_by) meta.append(el('span', `Used by ${entry.used_by}`));
        if (entry.surface) meta.append(el('code', entry.surface));
        meta.append(el('code', entry.call_site));
        card.append(meta);
        section.append(card);
      });
      host.append(section);
    });
  }

  /* ---- stack side panel --------------------------------------------- */
  const panel = document.querySelector('#stack-panel');
  const stackButton = document.querySelector('.stack-button');
  if (panel && stackButton) {
    const close = () => { panel.hidden = true; stackButton.setAttribute('aria-expanded', 'false'); stackButton.focus(); };
    stackButton.addEventListener('click', async () => {
      panel.hidden = false;
      stackButton.setAttribute('aria-expanded', 'true');
      document.querySelector('[data-close-stack]')?.focus();
      await paintStack();
    });
    document.querySelector('[data-close-stack]')?.addEventListener('click', close);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !panel.hidden) close(); });
  }

  /* ---- evidence board ----------------------------------------------- */
  const GATE_COPY = {
    'independent_source_domains>=3': 'Three or more independent source domains',
    'distinct_clue_families>=2': 'Two or more distinct clue families',
    'competing_hypotheses>=2': 'At least one rival identity to test against',
    leading_hypothesis_has_diagnostic_evidence: 'Evidence fits this film and not the rival',
    temporal_compatibility: 'Dates are mutually compatible',
    entity_compatibility: 'Studio, performers and country agree',
    'unresolved_contradictions==0': 'No unresolved contradiction from the Skeptic',
    every_decisive_claim_has_source: 'Every decisive claim carries a verified source',
    human_approved: 'An archivist has approved the identity',
  };

  /* ---- plain-language explainers -------------------------------------
     This product uses a small private vocabulary. "Decisive claim", "clue
     family", "threshold" and "abstain" are precise and, to anyone meeting them
     for the first time, opaque. A reader should not have to hold seven
     definitions in their head to read one dossier.

     So every term that carries weight gets a small "i" beside it and one
     sentence of explanation with no jargon in it. It opens on hover, on focus
     and on click: hover alone would exclude every keyboard and touch user,
     which is exactly what the rest of this interface is built not to do. */
  const GLOSSARY = {
    verdict: ['What the system decided',
      'One of three outcomes. It abstains, offers ranked candidates for a person to judge, or (only with a human signature) records a probable identity. It can never assert one on its own.'],
    probable: ['Probable identity',
      'The strongest verdict, and it needs a real archivist to approve it. No API call can produce it, so nothing here is ever an automatic identification.'],
    candidates: ['Candidates only',
      'The evidence points somewhere but is not strong enough to name the film. You get the possibilities and the reasoning, and you decide.'],
    abstain: ['Abstained',
      'The system found nothing solid enough to offer. That is a correct answer, not a failure: a confident wrong guess is worse than none.'],
    gate: ['The identity gate',
      'Ordinary code, not the AI, counting whether the evidence clears a fixed set of bars. The model gathers evidence; this decides what it is worth.'],
    threshold: ['A threshold',
      'One bar the evidence has to clear. Every one is shown whether it passed or failed, so you can see exactly what was missing.'],
    decisive: ['A decisive claim',
      'A claim solid enough to count toward the verdict: it has a real source, and that source still had the quoted words when checked. Claims without one are still shown, but cannot count.'],
    clue_family: ['A clue family',
      'A kind of evidence: an intertitle, a performer, a studio, a release date. Two facts from the same family are weaker than two from different ones.'],
    domains: ['Independent source domains',
      'How many different websites back the claim. Three pages on one site count once, because one voice repeated is not corroboration.'],
    stance: ['Supports, contradicts or neutral',
      'Which way a claim cuts. Evidence against the leading candidate sits next to evidence for it, never hidden.'],
    audit: ['The live citation audit',
      'Every cited page is opened again and checked for the exact quoted words. A search result is a summary of a page; this is the page itself.'],
    rejected: ['Rejected citations',
      'Sources thrown out before the verdict, because the search never returned them or the quoted words are not on the page. A made-up citation can only weaken a result here, never strengthen it.'],
    surfaces: ['Parallel surfaces',
      'Which research tools this run used. Search finds rare phrases, Task researches holdings, Extract re-opens pages to verify them.'],
    sealed: ['Held out and sealed',
      'Five fragments the system has never been run on, kept back so results cannot be tuned to fit them. Their answers are public; the runs have not happened.'],
    false_confident: ['A false-confident identification',
      'The system named a specific film and the answer key says it is the wrong one. This is the number that matters most, and it is published even when it is bad.'],
    stability: ['Why runs disagree',
      'The same fragment can give different answers on different days, because the agents search a web that changes. Every recorded run is published, not the best one.'],
  };

  function explainer(key) {
    const entry = GLOSSARY[key];
    if (!entry) return null;
    const wrap = el('span', undefined, 'explain');
    const btn = el('button', 'i', 'explain-btn');
    btn.type = 'button';
    btn.setAttribute('aria-label', 'What does this mean? ' + entry[0]);
    btn.setAttribute('aria-expanded', 'false');
    const bubble = el('span', undefined, 'explain-bubble');
    bubble.setAttribute('role', 'tooltip');
    bubble.append(el('b', entry[0]));
    bubble.append(el('span', entry[1]));
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const open = wrap.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
    const close = () => {
      wrap.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    };
    btn.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') { close(); btn.focus(); }
    });
    // A pinned bubble should not follow you around the page.
    document.addEventListener('click', (event) => {
      if (!wrap.contains(event.target)) close();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') close();
    });
    wrap.append(btn, bubble);
    return wrap;
  }

  function withExplainer(node, key) {
    const tip = explainer(key);
    if (tip) node.append(tip);
    return node;
  }

  // Anything in the static HTML opts in with data-explain="key".
  function attachExplainers(root) {
    (root || document).querySelectorAll('[data-explain]').forEach((node) => {
      if (node.querySelector(':scope > .explain')) return;
      withExplainer(node, node.dataset.explain);
    });
  }
  attachExplainers(document);
  document.addEventListener('DOMContentLoaded', () => attachExplainers(document));
  const AGENT_COPY = {
    visual_examiner: ['Visual Examiner', 'Gemini · transcribe clues, never name the film'],
    phrase_hunter: ['Phrase Hunter', 'Parallel Search · rare literal strings'],
    holdings_researcher: ['Holdings Researcher', 'Parallel Task + FindAll · titles and catalogues'],
    skeptic: ['Skeptic', 'Parallel Search · disconfirming evidence'],
    evidence_compiler: ['Evidence Compiler', 'Gemini · restate findings as typed claims'],
  };

  const VERDICT_TERM = {
    probable: 'probable', candidates: 'candidates', abstain: 'abstain',
    contradicted: 'candidates', confirmed: 'probable',
  };

  function verdictBanner(verdict, reason) {
    const box = el('div', undefined, `verdict verdict-${verdict}`);
    const copy = {
      probable: 'Probable identity, pending archivist approval',
      candidates: 'Candidates only: the evidence gate did not pass',
      abstain: 'Insufficient evidence: no identification offered',
      contradicted: 'Contradicted: the leading candidate was disproved',
      confirmed: 'Confirmed',
    };
    box.append(el('strong', copy[verdict] || verdict));
    if (reason) box.append(el('p', reason));
    return box;
  }

  function gateGrid(gate) {
    const wrap = el('div', undefined, 'gategrid');
    Object.entries(gate.thresholds || {}).forEach(([name, passed]) => {
      const row = el('div', undefined, `gaterow ${passed ? 'ok' : 'no'}`);
      row.append(el('span', passed ? '✓' : '·', 'gmark'));
      const label = el('span', GATE_COPY[name] || name.replace(/_/g, ' '));
      const GATE_TERM = {
        'independent_source_domains>=3': 'domains',
        'distinct_clue_families>=2': 'clue_family',
        every_decisive_claim_has_source: 'decisive',
        human_approved: 'probable',
      };
      if (GATE_TERM[name]) withExplainer(label, GATE_TERM[name]);
      row.append(label);
      wrap.append(row);
    });
    return wrap;
  }

  function sourceRow(source) {
    const counts = source.counts_toward_gate !== false;
    const row = el('div', undefined, `srcrow ${counts ? 'ok' : 'unverified'}`);
    const head = el('div', undefined, 'srchead');
    head.append(el('span', source.domain, 'dom'));
    let flag;
    if (source.live_verified === true) flag = 'confirmed on the live page';
    else if (source.live_verified === false) flag = 'not on the live page, refused by the gate';
    else if (source.verified) flag = 'verified against Parallel output';
    else flag = 'not found in retrieved text';
    head.append(el('span', flag, 'vflag'));
    const link = el('a', 'open ↗');
    link.href = source.url; link.target = '_blank'; link.rel = 'noreferrer';
    head.append(link);
    row.append(head);
    row.append(el('q', source.excerpt));
    return row;
  }

  /* A dossier can carry fourteen claims, each with several sources and a full
     excerpt apiece. Rendered flat that is several screens of scrolling before a
     reader reaches the audit, and the two things worth seeing first -- what was
     refused, and what contradicts the leading candidate -- are buried in the
     middle of it.

     So each claim is a <details>. The summary carries everything needed to
     decide whether to open it: stance, whether it can be decisive, the claim
     itself, and how its sources fared in the live audit. Nothing is removed;
     the excerpts are one click away and every one of them prints. */
  function claimSummaryTag(claim) {
    const n = claim.sources.length;
    if (!n) return 'no source';
    const confirmed = claim.sources.filter((s) => s.live_verified === true).length;
    const refused = claim.sources.filter((s) => s.live_verified === false).length;
    const parts = [`${n} source${n === 1 ? '' : 's'}`];
    if (confirmed) parts.push(`${confirmed} confirmed`);
    if (refused) parts.push(`${refused} refused`);
    return parts.join(' · ');
  }

  function claimCard(claim) {
    const card = el('details', undefined, `claim ${claim.stance}`);
    const sum = el('summary', undefined, 'claimsum');
    sum.append(el('span', claim.stance, `stance ${claim.stance}`));
    sum.append(el('span', claim.decisive_eligible ? 'decisive' : 'not decisive',
      `decisive ${claim.decisive_eligible ? 'yes' : 'no'}`));
    sum.append(el('span', claim.claim_text, 'claimtext'));
    const refused = claim.sources.some((s) => s.live_verified === false);
    const tag = el('span', claimSummaryTag(claim), 'srcsum');
    if (refused) tag.classList.add('has-refused');
    if (!claim.sources.length) tag.classList.add('has-none');
    sum.append(tag);
    card.append(sum);

    const body = el('div', undefined, 'claimbody');
    body.append(el('p', claim.confidence_basis, 'basis'));
    if (claim.sources.length) claim.sources.forEach((s) => body.append(sourceRow(s)));
    else body.append(el('p', 'No surviving source. This claim cannot be decisive.', 'nosrc'));
    card.append(body);

    // Opened by default only where the reader would otherwise miss the point:
    // a citation the live audit threw out, or evidence against the candidate.
    if (refused || claim.stance === 'contradicts') card.open = true;
    return card;
  }

  function auditPanel(audit) {
    const box = el('section', undefined, 'auditbox');
    box.append(withExplainer(el('h3', 'Live citation audit · Parallel Extract'), 'audit'));
    if (!audit || audit.status === 'skipped' || audit.status === 'not_requested') {
      box.append(el('p', audit?.reason || 'Not run for this investigation.', 'colnote'));
      return box;
    }
    if (audit.status === 'unavailable') {
      box.append(el('p', audit.reason, 'colnote'));
      return box;
    }
    box.append(el('p',
      'Every decisive citation was re-opened and checked against the page as it stands today. A search snippet is Parallel’s summary of a page; this is the page itself.',
      'colnote'));

    // The per-page rows repeat URLs already shown against their claims, so the
    // list collapses and the outcome -- which is the part that matters -- moves
    // into the summary where it is readable without opening anything.
    const rows = audit.audited || [];
    const held = rows.filter((e) => e.excerpt_present_on_live_page).length;
    const fold = el('details', undefined, 'auditfold');
    if (held < rows.length) fold.open = true;
    const sum = el('summary', undefined, 'auditsum');
    sum.append(el('b', `${held} of ${rows.length} cited pages still carry their quotation`));
    if (held < rows.length) {
      sum.append(el('span', `${rows.length - held} refused`, 'auditbad'));
    }
    fold.append(sum);
    rows.forEach((entry) => {
      const row = el('div', undefined, `auditrow ${entry.excerpt_present_on_live_page ? 'ok' : 'no'}`);
      row.append(el('span', entry.excerpt_present_on_live_page ? '✓' : '✕', 'gmark'));
      const body = el('div');
      body.append(el('b', entry.page_title || entry.url));
      body.append(el('span', entry.note, 'auditnote'));
      row.append(body);
      fold.append(row);
    });
    box.append(fold);
    return box;
  }

  function falsificationPanel(fals) {
    if (!fals || !['completed', 'partial'].includes(fals.status)) return null;
    const box = el('section', undefined, 'auditbox');
    box.append(el('h3', 'Independent falsification · Parallel Task Group'));
    box.append(el('p',
      'One researcher per candidate, each of which has never seen the others, each asked only to disprove its own candidate.',
      'colnote'));
    (fals.verdicts || []).forEach((v) => {
      const d = el('details', undefined, 'agentcard');
      const s = el('summary');
      s.append(el('b', v.candidate_id));
      // The finding belongs in the summary. Collapsing it behind a disclosure
      // that only says "completed" hides the one thing the reader came for.
      const content = v.content && typeof v.content === 'object' ? v.content : null;
      if (content) {
        const found = (content.contradictions || []).length;
        s.append(el('span', content.disproved ? 'disproved' : 'not disproved',
          `badge-mini ${content.disproved ? 'outcome-contradict' : 'outcome-identify'}`));
        s.append(el('span', `${found} contradiction${found === 1 ? '' : 's'} found`, 'arole'));
      } else {
        s.append(el('span', v.status, 'arole'));
      }
      d.append(s);
      d.append(el('pre', typeof v.content === 'string' ? v.content : JSON.stringify(v.content, null, 2)));
      box.append(d);
    });
    return box;
  }

  function languagePanel(findings) {
    if (!findings || !findings.length) return null;
    const box = el('section', undefined, 'auditbox warnbox');
    box.append(el('h3', 'Unsupportable survival language, caught'));
    box.append(el('p',
      'Searching every catalogue you can name tells you where a print is. It can never tell you no other print exists. These sentences were written by the model and are flagged, not published as findings.',
      'colnote'));
    findings.forEach((f) => {
      const row = el('div', undefined, 'rejrow');
      row.append(el('code', f.matched));
      row.append(el('span', f.where, 'rreason'));
      row.append(el('q', f.context));
      box.append(row);
    });
    return box;
  }

  function renderBoard(payload, host) {
    host = host || document.querySelector('[data-board]');
    if (!host) return;
    host.hidden = false;
    host.replaceChildren();
    const data = payload.data || {};
    const gate = data.gate || {};
    const ev = data.evidence || {};
    const retrieval = data.parallel_retrieval || {};

    // A worked example must be impossible to mistake for a run, at any scroll
    // position. The banner is sticky inside the board and the panels go dashed.
    const isExample = Boolean(payload.meta?.example || data.example);
    host.classList.toggle('is-example', isExample);
    if (isExample) {
      const banner = el('div', undefined, 'example-banner');
      banner.setAttribute('role', 'note');
      banner.append(el('b', 'Worked example, not a real investigation'));
      banner.append(el('span', payload.meta?.disclaimer || data.disclaimer || ''));
      host.append(banner);
    }

    host.append(verdictBanner(gate.verdict, gate.reason));

    const stats = el('div', undefined, 'boardstats');
    [
      [retrieval.sources_returned ?? 0, 'sources returned by Parallel'],
      [(retrieval.independent_domains || []).length, 'independent domains'],
      [(ev.claims || []).length, 'claims compiled'],
      [(ev.rejected_citations || []).length, 'citations rejected'],
      [(retrieval.surfaces_used || []).length, 'Parallel surfaces called'],
      [Math.round((data.latency_ms || 0) / 1000) + 's', 'end to end'],
    ].forEach(([v, l]) => {
      const d = el('div');
      d.append(el('b', String(v)), el('span', l));
      stats.append(d);
    });
    host.append(stats);

    const cols = el('div', undefined, 'boardcols');

    const left = el('section', undefined, 'boardcol');
    left.append(withExplainer(el('h3', 'The nine-threshold identity gate'), 'gate'));
    left.append(el('p', 'Deterministic code, not the model, decides. Every threshold is shown whether it passed or not.', 'colnote'));
    left.append(gateGrid(gate));
    if ((ev.candidates || []).length) {
      left.append(el('h3', 'Candidates'));
      ev.candidates.forEach((c) => {
        const row = el('div', undefined, 'candrow');
        row.append(el('b', c.label));
        row.append(el('span', `${c.decisive_claim_ids.length} decisive claim${c.decisive_claim_ids.length === 1 ? '' : 's'}`, 'cmeta'));
        const bar = el('div', undefined, 'cbar');
        const fill = el('i'); fill.style.width = `${Math.round(c.score * 100)}%`;
        bar.append(fill); row.append(bar);
        left.append(row);
      });
    }
    if ((ev.rejected_citations || []).length) {
      left.append(withExplainer(el('h3', 'Rejected citations'), 'rejected'));
      left.append(el('p', 'A source Parallel did not return in this run, or whose quoted text is not on the live page, is discarded before the gate sees it. A fabricated citation can only weaken a candidate, never support one.', 'colnote'));
      ev.rejected_citations.forEach((r) => {
        const row = el('div', undefined, 'rejrow');
        row.append(el('code', r.url || '(no url)'));
        row.append(el('span', r.reason.replace(/_/g, ' '), 'rreason'));
        left.append(row);
      });
    }
    cols.append(left);

    const right = el('section', undefined, 'boardcol');
    right.append(withExplainer(el('h3', 'Claims and their sources'), 'stance'));
    right.append(el('p', 'Supporting and contradicting claims are shown together. The Skeptic searches specifically for evidence against the leading candidate.', 'colnote'));
    const claims = ev.claims || [];
    if (!claims.length) right.append(el('p', 'No claim survived compilation. The gate abstained rather than guessing.', 'nosrc'));
    if (claims.length) {
      const decisive = claims.filter((c) => c.decisive_eligible).length;
      const bar = el('div', undefined, 'claimbar');
      bar.append(el('span', `${claims.length} claims · ${decisive} can be decisive`, 'claimcount'));
      const toggle = el('button', 'Expand all', 'link-button');
      toggle.type = 'button';
      toggle.addEventListener('click', () => {
        const cards = right.querySelectorAll('details.claim');
        const opening = toggle.textContent === 'Expand all';
        cards.forEach((d) => { d.open = opening; });
        toggle.textContent = opening ? 'Collapse all' : 'Expand all';
      });
      bar.append(toggle);
      right.append(bar);
    }
    claims.forEach((c) => right.append(claimCard(c)));
    if ((ev.unresolved_questions || []).length) {
      right.append(el('h3', 'Unresolved questions'));
      const ul = el('ul', undefined, 'qlist');
      ev.unresolved_questions.forEach((q) => ul.append(el('li', q)));
      right.append(ul);
    }
    cols.append(right);
    host.append(cols);

    host.append(auditPanel(data.citation_audit));
    const fals = falsificationPanel(data.falsification);
    if (fals) host.append(fals);
    const lang = languagePanel(data.language_findings);
    if (lang) host.append(lang);

    if (data.cold_case?.eligible) {
      const cold = el('section', undefined, 'auditbox');
      cold.append(el('h3', 'This fragment stays unidentified: keep looking'));
      cold.append(el('p', 'An abstention is the right answer today and the wrong answer forever. Archives digitise continuously. A Parallel Monitor leaves a standing weekly query on the strings visible in this frame.', 'colnote'));
      const strings = data.cold_case.watchable_strings || [];
      const fold = el('details', undefined, 'coldfold');
      const sum = el('summary', undefined, 'auditsum');
      sum.append(el('b', `${strings.length} string${strings.length === 1 ? '' : 's'} would be watched`));
      fold.append(sum);
      const list = el('ul', undefined, 'qlist');
      strings.forEach((str) => list.append(el('li', str)));
      fold.append(list);
      cold.append(fold);
      const watch = el('button', 'Leave a standing watch', 'secondary-button');
      watch.addEventListener('click', async () => {
        watch.disabled = true; watch.textContent = 'Registering…';
        try {
          const r = await authedFetch('/v1/watch', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({
              fragment_label: data.origin || 'unidentified fragment',
              rare_strings: data.cold_case.watchable_strings.slice(0, 5),
            }),
          });
          const p = await r.json();
          watch.textContent = r.ok ? `Watching · ${p.data.monitor_id || 'registered'}` : (p?.error?.message || 'Could not register');
        } catch (_) { watch.textContent = 'Could not register'; }
      });
      cold.append(watch);
      host.append(cold);
    }

    const agents = el('details', undefined, 'agentstrip');
    const agentsum = el('summary', undefined, 'auditsum');
    agentsum.append(el('b', 'Five roles, separately inspectable'));
    agentsum.append(el('span', 'raw output from each agent in this run', 'colnote'));
    agents.append(agentsum);
    const strip = el('div', undefined, 'strip');
    Object.entries(data.outputs || {}).forEach(([key, value], i) => {
      const spec = AGENT_COPY[key] || [key, ''];
      const card = el('details', undefined, 'agentcard');
      const sum = el('summary');
      sum.append(el('span', String(i + 1), 'anum'), el('b', spec[0]), el('span', spec[1], 'arole'));
      card.append(sum);
      const body = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
      card.append(el('pre', body || 'This role produced no output.'));
      strip.append(card);
    });
    agents.append(strip);
    host.append(agents);

    const actions = el('div', undefined, 'boardactions');
    const dl = el('button', 'Download this dossier (JSON)', 'secondary-button');
    dl.addEventListener('click', () => {
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `last-seen-alive_${data.sample_id || 'upload'}_${(data.session_id || '').slice(0, 12)}.json`;
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    actions.append(dl);
    host.append(actions);

    host.append(el('p', 'Triage, not attribution authority. An archivist approves or rejects every identification; this page never does.', 'boardfoot'));
    host.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /** Load and render the worked example dossier. Public, no key needed. */
  async function showWorkedExample(host, button) {
    const original = button ? button.textContent : null;
    if (button) { button.disabled = true; button.textContent = 'Loading example…'; }
    try {
      const response = await fetch('/v1/example/dossier');
      const payload = await response.json();
      if (!response.ok) throw new Error('unavailable');
      renderBoard(payload, host);
    } catch (_) {
      if (host) {
        host.hidden = false;
        host.replaceChildren(el('p', 'The worked example could not be loaded.', 'nosrc'));
      }
    } finally {
      if (button) { button.disabled = false; button.textContent = original; }
    }
  }

  window.LSA = {
    el, mintKey, authedFetch, readKey, renderBoard, paintStack,
    showWorkedExample,
  };
  paintStack();
})();

/* ---- standards conformance table (stack page) ----------------------
   Rendered from GET /v1/standards so the page cannot drift from the data
   the tests assert against. */
(async () => {
  const host = document.querySelector('[data-standards-table]');
  if (!host) return;
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const LABEL = {
    conforms: ['Conforms', 'live'],
    partial: ['Partial', 'unknown'],
    was_failing_now_conforms: ['Was failing \u00b7 now fixed', 'req'],
  };
  let data;
  try {
    data = (await (await fetch('/v1/standards')).json()).data;
  } catch (_) {
    host.replaceChildren(el('p', 'Conformance data unavailable.', 'nosrc'));
    return;
  }
  host.replaceChildren();
  data.requirements.forEach((r) => {
    const [text, tone] = LABEL[r.status] || [r.status, 'unknown'];
    const card = el('article', undefined, 'stackrow ' + (r.status === 'partial' ? 'unknown' : 'live'));
    const top = el('div', undefined, 'stackrow-top');
    top.append(el('span', r.id, 'preset-id'));
    top.append(el('h3', r.requirement));
    top.append(el('span', text, `badge-mini ${tone}`));
    card.append(top);
    const quote = el('p', undefined, 'stackrow-note');
    quote.append(el('q', r.quote));
    quote.append(el('span', ' \u00b7 ' + r.citation, 'cmeta'));
    card.append(quote);
    card.append(el('p', r.how, 'stackrow-role'));
    if (r.tests.length) {
      const meta = el('div', undefined, 'stackrow-meta');
      r.tests.forEach((name) => meta.append(el('code', name)));
      card.append(meta);
    }
    host.append(card);
  });
  const note = el('p', data.disclaimer, 'colnote');
  note.style.marginTop = 'var(--s4)';
  host.append(note);
})();
