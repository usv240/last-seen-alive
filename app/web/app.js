/* Landing-page behaviour: preset picker with inline playback and download,
   bring-your-own upload, and the judge key button. Everything here calls the
   same public API a third party would. */

(() => {
  const { el, mintKey, authedFetch, renderBoard, showWorkedExample } = window.LSA;
  const events = document.querySelector('[data-run-events]');
  const board = document.querySelector('[data-board]');
  const runConsole = new window.LSA_RunConsole(events);
  runConsole.idle();

  /* ---- tabs ---------------------------------------------------------- */
  const panes = { preset: document.querySelector('#pane-preset'), upload: document.querySelector('#pane-upload') };
  document.querySelectorAll('[data-tab]').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('[data-tab]').forEach((other) => {
        const active = other === tab;
        other.setAttribute('aria-selected', String(active));
        panes[other.dataset.tab].hidden = !active;
      });
    });
  });

  /* ---- preset picker -------------------------------------------------- */
  const select = document.querySelector('[data-preset-select]');
  const note = document.querySelector('[data-preset-note]');
  const video = document.querySelector('[data-preset-video]');
  const download = document.querySelector('[data-preset-download]');
  let presets = [];

  function showPreset(caseId) {
    const preset = presets.find((p) => p.case_id === caseId);
    if (!preset) return;
    note.replaceChildren(
      el('b', preset.headline),
      document.createTextNode(' ' + preset.challenge),
    );
    video.src = preset.media_url;
    video.load();
    download.href = preset.download_url;
    download.textContent = `Download ${preset.case_id} · ${(preset.bytes / 1048576).toFixed(1)} MB`;
  }

  (async () => {
    try {
      const response = await fetch('/v1/presets?split=dev');
      presets = (await response.json()).data.presets;
      select.replaceChildren(...presets.map((p) => {
        const option = el('option', `${p.case_id} · ${p.tier_name} · expects ${p.expected_outcome_name.toLowerCase()}`);
        option.value = p.case_id;
        return option;
      }));
      select.value = 'D02';
      showPreset(select.value);
    } catch (_) {
      select.replaceChildren(el('option', 'Demo set unavailable'));
    }
  })();

  select.addEventListener('change', () => showPreset(select.value));

  /* ---- shared run handling -------------------------------------------- */
  async function run(label, fetcher) {
    board.hidden = true;
    runConsole.begin(label);
    try {
      const response = await fetcher();
      const payload = await response.json();
      if (!response.ok) {
        runConsole.error(payload.error || payload.detail || {});
        return;
      }
      runConsole.outcome(payload);
      renderBoard(payload, board);
    } catch (_) {
      runConsole.error({
        message: 'The endpoint is unreachable from this browser.',
        fix: 'Check your connection and try again. No result was fabricated.',
      });
    }
  }

  document.querySelector('[data-demo-form]').addEventListener('submit', (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    run(`${form.get('sample_id')} · ${form.get('depth') === 'deep' ? 'deep' : 'standard'} mode`,
      () => authedFetch('/v1/identify', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        sample_id: form.get('sample_id'),
        depth: form.get('depth') === 'deep' ? 'deep' : 'standard',
      }),
    }));
  });

  /* ---- bring your own -------------------------------------------------- */
  const fileInput = document.querySelector('#own');
  const preview = document.querySelector('[data-upload-preview]');
  fileInput.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    if (!file || !file.type.startsWith('video/')) { preview.hidden = true; return; }
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  });

  document.querySelector('[data-upload-form]').addEventListener('submit', (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const file = form.querySelector('#own').files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append('fragment', file);
    const label = form.querySelector('#label').value.trim();
    if (label) body.append('provided_label', label);
    body.append('depth', form.querySelector('[name="depth"]').checked ? 'deep' : 'standard');
    run(file.name, () => authedFetch('/v1/investigate', { method: 'POST', body }));
  });

  /* ---- worked example ---------------------------------------------------
     The evidence board is the product, and until a Parallel credential is
     attached nobody can see one. This shows the real output shape, generated
     by the real gate, behind a banner that cannot be mistaken for a run. */
  document.querySelector('[data-show-example]')?.addEventListener('click', (event) => {
    showWorkedExample(board, event.currentTarget);
  });

  /* ---- judge key -------------------------------------------------------- */
  document.querySelector('[data-mint-judge-key]').addEventListener('click', async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = 'Minting…';
    try {
      const key = await mintKey(true);
      await navigator.clipboard.writeText(key).catch(() => {});
      button.textContent = `Copied · ${key.slice(0, 16)}…`;
    } catch (_) {
      button.textContent = 'Key unavailable';
    } finally {
      button.disabled = false;
    }
  });
})();
