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

  document.querySelector('[data-demo-form]').addEventListener('submit', async (event) => {
    event.preventDefault(); const events = document.querySelector('[data-run-events]');
    events.innerHTML = '<li>Submitting the selected fragment…</li>';
    try {
      const response = await fetch('/v1/identify', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({sample_id:new FormData(event.currentTarget).get('sample_id')})});
      const payload = await response.json();
      events.innerHTML = response.ok ? `<li>Verdict: <strong>${payload.meta.verdict}</strong></li><li>Passed: ${payload.meta.gate.passed.join(', ') || 'none'}</li><li>Failed: ${payload.meta.gate.failed.join(', ') || 'none'}</li>` : `<li>${payload.error.message}</li>`;
    } catch (_) { events.innerHTML = '<li>The demo endpoint is unavailable. No result was fabricated.</li>'; }
  });
})();

