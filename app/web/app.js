(() => {
  const root = document.documentElement;
  const safeRead = (key) => { try { return localStorage.getItem(key); } catch (_) { return null; } };
  const safeWrite = (key, value) => { try { localStorage.setItem(key, value); } catch (_) {} };

  const setMode = (mode) => {
    root.dataset.reading = mode;
    document.querySelectorAll('[data-set-mode]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.setMode === mode));
    });
    safeWrite('lsa-reading', mode);
  };
  setMode(safeRead('lsa-reading') === 'technical' ? 'technical' : 'plain');
  document.querySelectorAll('[data-set-mode]').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.setMode)));

  const themeButton = document.querySelector('[data-theme-toggle]');
  const setTheme = (theme) => {
    if (theme === 'dark') root.dataset.theme = 'dark'; else delete root.dataset.theme;
    themeButton.textContent = theme === 'dark' ? 'Light' : 'Dark';
    safeWrite('lsa-theme', theme);
  };
  setTheme(safeRead('lsa-theme') === 'dark' ? 'dark' : 'light');
  themeButton.addEventListener('click', () => setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));

  const panel = document.querySelector('#stack-panel');
  const stackButton = document.querySelector('.stack-button');
  const closePanel = () => { panel.hidden = true; stackButton.setAttribute('aria-expanded', 'false'); stackButton.focus(); };
  stackButton.addEventListener('click', async () => {
    panel.hidden = false; stackButton.setAttribute('aria-expanded', 'true');
    document.querySelector('[data-close-stack]').focus(); await loadHealth();
  });
  document.querySelector('[data-close-stack]').addEventListener('click', closePanel);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !panel.hidden) closePanel(); });

  async function loadHealth() {
    const list = document.querySelector('[data-integration-list]');
    try {
      const response = await fetch('/health/integrations');
      const payload = await response.json();
      list.replaceChildren(...Object.entries(payload.data.integrations).map(([name, value]) => {
        const item = document.createElement('li');
        const dot = document.createElement('span'); dot.className = `status-dot ${value.ok ? '' : 'down'}`;
        item.append(dot, document.createTextNode(`${name} · ${value.ok ? 'available' : 'unavailable'}`)); return item;
      }));
    } catch (_) { list.innerHTML = '<li><span class="status-dot down"></span>Health endpoint unavailable</li>'; }
  }

  document.querySelector('[data-mint-judge-key]').addEventListener('click', async (event) => {
    const button = event.currentTarget; button.disabled = true; button.textContent = 'Minting…';
    try {
      const response = await fetch('/v1/keys', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({tier:'judge'})});
      const payload = await response.json();
      button.textContent = response.ok ? `Copy key: ${payload.data.key.slice(0, 18)}…` : 'Key unavailable';
      if (response.ok) await navigator.clipboard.writeText(payload.data.key);
    } catch (_) { button.textContent = 'Key unavailable'; }
    finally { button.disabled = false; }
  });

  // ---- evidence board -------------------------------------------------
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const GATE_COPY = {
    'independent_source_domains>=3': 'Three or more independent source domains',
    'distinct_clue_families>=2': 'Two or more distinct clue families',
    'temporal_compatibility': 'Dates are mutually compatible',
    'entity_compatibility': 'Studio, performers and country agree',
    'unresolved_contradictions==0': 'No unresolved contradiction from the Skeptic',
    'every_decisive_claim_has_source': 'Every decisive claim carries a verified source',
    'human_approved': 'An archivist has approved the identity',
  };
  const AGENT_COPY = {
    visual_examiner: ['Visual Examiner', 'transcribe clues, never name the film'],
    phrase_hunter: ['Phrase Hunter', 'Parallel Search on rare literal strings'],
    holdings_researcher: ['Holdings Researcher', 'Parallel Task on alternate titles and archives'],
    skeptic: ['Skeptic', 'Parallel Search for disconfirming evidence'],
    evidence_compiler: ['Evidence Compiler', 'restate findings as typed claims'],
  };

  function verdictBanner(verdict, reason) {
    const box = el('div', undefined, `verdict verdict-${verdict}`);
    const copy = {
      probable: 'Probable identity — pending archivist approval',
      candidates: 'Candidates only — the evidence gate did not pass',
      abstain: 'Insufficient evidence — no identification offered',
      contradicted: 'Contradicted — the leading candidate was disproved',
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
      row.append(el('span', GATE_COPY[name] || name.replace(/_/g, ' ')));
      wrap.append(row);
    });
    return wrap;
  }

  function sourceRow(source) {
    const row = el('div', undefined, `srcrow ${source.verified ? 'ok' : 'unverified'}`);
    const head = el('div', undefined, 'srchead');
    head.append(el('span', source.domain, 'dom'));
    head.append(el('span', source.verified ? 'verified against Parallel output' : 'not found in retrieved text', 'vflag'));
    const link = el('a', 'open ↗');
    link.href = source.url; link.target = '_blank'; link.rel = 'noreferrer';
    head.append(link);
    row.append(head);
    row.append(el('q', source.excerpt));
    return row;
  }

  function claimCard(claim) {
    const card = el('article', undefined, `claim ${claim.stance}`);
    const top = el('div', undefined, 'claimtop');
    top.append(el('span', claim.stance, `stance ${claim.stance}`));
    top.append(el('span', claim.decisive_eligible ? 'decisive' : 'not decisive', `decisive ${claim.decisive_eligible ? 'yes' : 'no'}`));
    card.append(top);
    card.append(el('p', claim.claim_text, 'claimtext'));
    card.append(el('p', claim.confidence_basis, 'basis'));
    if (claim.sources.length) claim.sources.forEach((s) => card.append(sourceRow(s)));
    else card.append(el('p', 'No surviving source. This claim cannot be decisive.', 'nosrc'));
    return card;
  }

  function renderBoard(payload) {
    const host = document.querySelector('[data-board]');
    host.hidden = false;
    host.replaceChildren();
    const data = payload.data || {};
    const gate = data.gate || {};
    const ev = data.evidence || {};
    const retrieval = data.parallel_retrieval || {};

    host.append(verdictBanner(gate.verdict, gate.reason));

    const stats = el('div', undefined, 'boardstats');
    [
      [retrieval.sources_returned ?? 0, 'sources returned by Parallel'],
      [(retrieval.independent_domains || []).length, 'independent domains'],
      [(ev.claims || []).length, 'claims compiled'],
      [(ev.rejected_citations || []).length, 'citations rejected'],
    ].forEach(([v, l]) => {
      const d = el('div');
      d.append(el('b', String(v)), el('span', l));
      stats.append(d);
    });
    host.append(stats);

    const cols = el('div', undefined, 'boardcols');

    const left = el('section', undefined, 'boardcol');
    left.append(el('h3', 'The seven-threshold identity gate'));
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
      left.append(el('h3', 'Rejected citations'));
      left.append(el('p', 'A source Parallel did not return in this run is discarded before the gate sees it. A fabricated citation can only weaken a candidate, never support one.', 'colnote'));
      ev.rejected_citations.forEach((r) => {
        const row = el('div', undefined, 'rejrow');
        row.append(el('code', r.url || '(no url)'));
        row.append(el('span', r.reason.replace(/_/g, ' '), 'rreason'));
        left.append(row);
      });
    }
    cols.append(left);

    const right = el('section', undefined, 'boardcol');
    right.append(el('h3', 'Claims and their sources'));
    right.append(el('p', 'Supporting and contradicting claims are shown together. The Skeptic searches specifically for evidence against the leading candidate.', 'colnote'));
    const claims = ev.claims || [];
    if (!claims.length) right.append(el('p', 'No claim survived compilation. The gate abstained rather than guessing.', 'nosrc'));
    claims.forEach((c) => right.append(claimCard(c)));
    if ((ev.unresolved_questions || []).length) {
      right.append(el('h3', 'Unresolved questions'));
      const ul = el('ul', undefined, 'qlist');
      ev.unresolved_questions.forEach((q) => ul.append(el('li', q)));
      right.append(ul);
    }
    cols.append(right);
    host.append(cols);

    const agents = el('section', undefined, 'agentstrip');
    agents.append(el('h3', 'Five roles, separately inspectable'));
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

    const foot = el('p', 'Triage, not attribution authority. An archivist approves or rejects every identification; this page never does.', 'boardfoot');
    host.append(foot);
    host.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  document.querySelector('[data-demo-form]').addEventListener('submit', async (event) => {
    event.preventDefault();
    const events = document.querySelector('[data-run-events]');
    const board = document.querySelector('[data-board]');
    board.hidden = true;
    events.innerHTML = '<li>Running the five-role workflow. Parallel Search and Task calls are live, so this takes a moment…</li>';
    try {
      const response = await fetch('/v1/identify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ sample_id: new FormData(event.currentTarget).get('sample_id') }),
      });
      const payload = await response.json();
      if (!response.ok) {
        const detail = payload.detail || payload.error || {};
        events.innerHTML = `<li>${detail.message || 'The workflow did not run.'}</li>` +
          (detail.code === 'partner_credential_not_configured'
            ? '<li>No result was fabricated. Parallel is the only open-web path in this product, so without it the workflow stops rather than guessing.</li>'
            : '');
        return;
      }
      events.innerHTML = `<li>Verdict: <strong>${payload.meta.verdict}</strong></li>` +
        `<li>Passed: ${payload.meta.gate.passed.join(', ') || 'none'}</li>` +
        `<li>Failed: ${payload.meta.gate.failed.join(', ') || 'none'}</li>`;
      renderBoard(payload);
    } catch (_) {
      events.innerHTML = '<li>The demo endpoint is unavailable. No result was fabricated.</li>';
    }
  });
})();

