/* The dossier archive.

   These are captured responses, but they are rendered by exactly the renderer a
   live run uses (LSA.renderBoard). That is deliberate: if the archive drew its
   own prettier version of a dossier, the page would be a mock-up of the product
   rather than the product. Anything you can read here you would see, in the same
   shape, by running the fragment yourself and waiting.

   Selection is reflected in the URL hash so a judge can send someone a link to
   one specific dossier. */

(() => {
  const list = document.querySelector('[data-dossier-list]');
  const board = document.querySelector('[data-dossier-board]');
  const note = document.querySelector('[data-capture-note]');
  if (!list || !board) return;

  const el = window.LSA ? window.LSA.el : (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };

  const VERDICT_WORD = {
    identify: 'Identified',
    probable: 'Probable identity',
    candidates: 'Candidates, human review required',
    abstain: 'Abstained',
    contradict: 'Contradicted its label',
  };

  let buttons = [];

  async function show(caseId, { push = true } = {}) {
    buttons.forEach((b) => {
      const selected = b.dataset.case === caseId;
      b.setAttribute('aria-pressed', String(selected));
      b.classList.toggle('active', selected);
    });

    board.replaceChildren(el('p', 'Loading dossier…', 'small'));
    try {
      const response = await fetch(`/v1/dossiers/${encodeURIComponent(caseId)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error((payload.error || {}).message || 'not available');
      board.replaceChildren();
      window.LSA.renderBoard(payload.data, board);

      const captured = payload.data.captured || {};
      const footer = el('p', undefined, 'small');
      footer.append(el('b', `Captured ${(captured.at || '').slice(0, 10)}`));
      footer.append(el('span', ` · ${Math.round(captured.elapsed_seconds || 0)}s end to end · `));
      const raw = el('a', 'Download the raw JSON');
      raw.href = `/v1/dossiers/${encodeURIComponent(caseId)}`;
      raw.setAttribute('download', `${caseId}-dossier.json`);
      footer.append(raw);
      board.append(footer);

      if (push && window.location.hash !== `#${caseId}`) {
        history.replaceState(null, '', `#${caseId}`);
      }
      board.focus({ preventScroll: true });
    } catch (error) {
      board.replaceChildren(el('div', undefined, 'run-error'));
      board.firstChild.append(el('b', 'That dossier could not be loaded.'));
      board.firstChild.append(el('p', String(error.message || error)));
    }
  }

  (async () => {
    try {
      const response = await fetch('/v1/dossiers');
      const payload = await response.json();
      if (!response.ok) throw new Error((payload.error || {}).message || 'not captured');

      const rows = payload.data.dossiers || [];
      if (!rows.length) throw new Error('no dossiers captured');

      list.replaceChildren();
      buttons = rows.map((row) => {
        const button = el('button', undefined, 'dossier-pick');
        button.type = 'button';
        button.dataset.case = row.case_id;
        button.setAttribute('aria-pressed', 'false');

        button.append(el('b', row.case_id, 'dossier-id'));
        const OUTCOME = {
          identify: 'should reach a probable identity',
          candidates: 'should return ranked candidates only',
          abstain: 'should abstain',
          contradict: 'should contradict its supplied label',
        };
        button.append(el('span', row.title || OUTCOME[row.expected_outcome] || '', 'dossier-title'));
        const verdict = el('span', VERDICT_WORD[row.verdict] || row.verdict, 'dossier-verdict');
        verdict.dataset.verdict = row.verdict;
        button.append(verdict);
        const total = row.thresholds_total || 7;
        button.append(el('span', `${row.thresholds_passed} of ${total} thresholds · ${Math.round(row.elapsed_seconds)}s`, 'dossier-meta'));

        button.addEventListener('click', () => show(row.case_id));
        const item = el('li');
        item.append(button);
        list.append(item);
        return button;
      });

      if (note) {
        note.textContent = `${rows.length} dossiers captured ${(payload.data.captured_at || '').slice(0, 10)} from ${payload.data.service}. Development split only.`;
      }

      const wanted = decodeURIComponent(window.location.hash.replace('#', '')).toUpperCase();
      if (rows.some((row) => row.case_id === wanted)) show(wanted, { push: false });
    } catch (error) {
      const item = el('li');
      item.append(el('p', `No dossiers have been captured for this deployment (${error.message}).`, 'small'));
      list.replaceChildren(item);
    }
  })();
})();
