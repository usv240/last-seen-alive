/* Demo-set page: render each fragment as a watchable, downloadable card, and
   run the development cases through the public API. */

(() => {
  const { el, authedFetch, renderBoard } = window.LSA;
  const board = document.querySelector('[data-board]');

  function card(preset) {
    const article = el('article', undefined, `presetcard ${preset.runnable ? '' : 'sealed'}`);

    const top = el('div', undefined, 'presetcard-top');
    top.append(el('span', preset.case_id, 'preset-id'));
    top.append(el('span', preset.tier_name, 'badge-mini'));
    top.append(el('span', preset.expected_outcome_name, `badge-mini outcome-${preset.expected_outcome}`));
    if (!preset.runnable) top.append(el('span', 'SEALED', 'badge-mini sealed'));
    article.append(top);

    article.append(el('h3', preset.headline));
    article.append(el('p', preset.challenge, 'presetcard-challenge'));

    if (preset.runnable) {
      const video = el('video', undefined, 'preset-video');
      video.controls = true;
      video.preload = 'metadata';
      video.playsInline = true;
      video.muted = true;
      video.src = preset.media_url;
      article.append(video);
    } else {
      const locked = el('div', undefined, 'preset-locked');
      locked.append(el('span', '🔒'));
      locked.append(el('span', 'Media endpoint returns 423 by design'));
      article.append(locked);
    }

    const why = el('p', undefined, 'presetcard-why');
    why.append(el('b', 'Why this case exists: '));
    why.append(document.createTextNode(preset.why_it_matters));
    article.append(why);

    if (preset.provided_label) {
      const label = el('p', undefined, 'presetcard-label');
      label.append(el('b', 'Arrives labelled: '));
      label.append(el('q', preset.provided_label));
      article.append(label);
    }

    const meta = el('dl', undefined, 'presetmeta');
    [
      ['Duration', `${preset.duration_seconds}s`],
      ['Size', `${(preset.bytes / 1048576).toFixed(1)} MB`],
      ['Type', preset.media_type],
      ['SHA-256', preset.sha256.slice(0, 16) + '…'],
    ].forEach(([term, value]) => {
      meta.append(el('dt', term), el('dd', value));
    });
    article.append(meta);

    const transforms = el('details', undefined, 'presettransforms');
    transforms.append(el('summary', `${preset.transforms.length} transforms applied`));
    const list = el('ul');
    preset.transforms.forEach((t) => list.append(el('li', t)));
    transforms.append(list);
    article.append(transforms);

    const actions = el('div', undefined, 'row-actions');
    if (preset.runnable) {
      const run = el('button', 'Investigate', 'primary-button');
      run.addEventListener('click', () => investigate(preset, run));
      actions.append(run);
      const dl = el('a', 'Download', 'link-button');
      dl.href = preset.download_url;
      dl.setAttribute('download', '');
      actions.append(dl);
    } else {
      const attempt = el('a', 'Try the sealed endpoint', 'link-button');
      attempt.href = `/v1/presets/${preset.case_id}/media`;
      attempt.target = '_blank';
      attempt.rel = 'noreferrer';
      actions.append(attempt);
    }
    const detail = el('a', 'JSON', 'link-button');
    detail.href = `/v1/presets/${preset.case_id}`;
    detail.target = '_blank';
    detail.rel = 'noreferrer';
    actions.append(detail);
    article.append(actions);

    article.append(el('p', preset.credit, 'presetcard-credit'));
    return article;
  }

  async function investigate(preset, button) {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Investigating…';
    board.hidden = false;
    board.classList.remove('is-example');
    board.replaceChildren();

    // The console lives inside the board here, so the six stages are what the
    // reader watches while the run is in flight and the dossier replaces them
    // when it lands.
    const panel = el('section', undefined, 'card run-panel');
    board.append(panel);
    board.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const runConsole = new window.LSA_RunConsole(panel);
    runConsole.begin(`${preset.case_id} · ${preset.headline}`);

    try {
      const response = await authedFetch('/v1/identify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ sample_id: preset.case_id }),
      });
      const payload = await response.json();
      if (!response.ok) {
        runConsole.error(payload.error || {});
        return;
      }
      runConsole.finish();
      renderBoard(payload, board);
    } catch (_) {
      runConsole.error({
        message: 'The endpoint is unreachable from this browser.',
        fix: 'Check your connection and try again. No result was fabricated.',
      });
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  }

  (async () => {
    let data;
    try {
      data = (await (await fetch('/v1/presets')).json()).data;
    } catch (_) {
      document.querySelectorAll('[data-preset-grid]').forEach((grid) =>
        grid.replaceChildren(el('p', 'The demo set could not be loaded.', 'nosrc')));
      return;
    }

    const strip = document.querySelector('[data-corpus-strip]');
    if (strip) {
      const corpus = data.corpus;
      strip.replaceChildren(...[
        ['Cases', String(corpus.cases)],
        ['Runnable', String(corpus.development)],
        ['Sealed', String(corpus.holdout)],
        ['Held-out run', corpus.holdout_run.replace('_', ' ')],
      ].map(([term, value]) => {
        const wrap = el('div');
        wrap.append(el('dt', term), el('dd', value));
        return wrap;
      }));
    }

    document.querySelectorAll('[data-preset-grid]').forEach((grid) => {
      const split = grid.dataset.split;
      const rows = data.presets.filter((p) => p.split === split);
      grid.replaceChildren(...rows.map(card));
    });
  })();
})();
