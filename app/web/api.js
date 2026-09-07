/* The API page: mint a key, fire a real request from the browser, and keep the
   copy-paste snippets in step with whatever endpoint is selected. */

(() => {
  const { el, mintKey, readKey, renderBoard } = window.LSA;

  const out = document.querySelector('[data-out]');
  const statusLine = document.querySelector('[data-status]');
  const endpointSelect = document.querySelector('[data-endpoint]');
  const bodyWrap = document.querySelector('[data-body-wrap]');
  const bodyField = document.querySelector('[data-body]');
  const fileWrap = document.querySelector('[data-file-wrap]');
  const warn = document.querySelector('[data-warn]');
  const snippet = document.querySelector('[data-snippet]');
  const copyResponse = document.querySelector('[data-copy-response]');
  const showBoard = document.querySelector('[data-render-board]');
  const board = document.querySelector('[data-board]');

  const DEFAULT_BODY = {
    'POST /v1/identify': JSON.stringify({ sample_id: 'D02', depth: 'standard' }, null, 2),
  };

  let lastPayload = null;

  /* ---- key ---------------------------------------------------------- */
  const keyOutput = document.querySelector('[data-key-output]');
  const keyFacts = document.querySelector('[data-key-facts]');
  const copyKey = document.querySelector('[data-copy-key]');

  function showKey(key, data) {
    keyOutput.textContent = key;
    keyOutput.classList.add('has-key');
    copyKey.hidden = false;
    if (data) {
      keyFacts.hidden = false;
      keyFacts.replaceChildren(...[
        ['Tier', data.tier],
        ['Expires', new Date(data.expires_at).toLocaleDateString()],
        ['Daily limit', String(data.daily_limit)],
        ['Key id', data.key_id],
      ].flatMap(([term, value]) => [el('dt', term), el('dd', value)]));
    }
    renderSnippet();
  }

  document.addEventListener('lsa:key', (event) => showKey(readKey(), event.detail));

  document.querySelector('[data-mint]').addEventListener('click', async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    const original = button.textContent;
    button.textContent = 'Minting…';
    try {
      await mintKey(true);
    } catch (error) {
      keyOutput.textContent = String(error.message || error);
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  });

  copyKey.addEventListener('click', async () => {
    await navigator.clipboard.writeText(readKey() || '').catch(() => {});
    copyKey.textContent = 'Copied';
    setTimeout(() => { copyKey.textContent = 'Copy key'; }, 1500);
  });

  const existing = readKey();
  if (existing) showKey(existing, null);

  /* ---- endpoint form ------------------------------------------------- */
  function currentEndpoint() {
    const [method, path] = endpointSelect.value.split(' ');
    return { method, path };
  }

  function syncForm() {
    const { method, path } = currentEndpoint();
    const isUpload = path === '/v1/investigate';
    const hasBody = method === 'POST' && !isUpload;
    bodyWrap.hidden = !hasBody;
    fileWrap.hidden = !isUpload;
    warn.hidden = !(path === '/v1/identify' || isUpload);
    if (hasBody) bodyField.value = DEFAULT_BODY[endpointSelect.value] || '{}';
    renderSnippet();
  }

  endpointSelect.addEventListener('change', syncForm);
  bodyField.addEventListener('input', renderSnippet);

  /* ---- snippets ------------------------------------------------------- */
  let language = 'curl';
  document.querySelectorAll('[data-lang]').forEach((tab) => {
    tab.addEventListener('click', () => {
      language = tab.dataset.lang;
      document.querySelectorAll('[data-lang]').forEach((other) =>
        other.setAttribute('aria-selected', String(other === tab)));
      renderSnippet();
    });
  });

  function renderSnippet() {
    const { method, path } = currentEndpoint();
    const base = window.location.origin;
    const key = readKey() || '<YOUR_KEY>';
    const needsKey = ['/v1/identify', '/v1/investigate', '/v1/watch', '/v1/eval/latest'].includes(path);
    const body = bodyWrap.hidden ? null : bodyField.value.trim();
    const isUpload = path === '/v1/investigate';

    if (language === 'curl') {
      if (isUpload) {
        snippet.textContent = [
          `curl -X POST ${base}${path} \\`,
          `  -H "Authorization: Bearer ${key}" \\`,
          `  -F "fragment=@unidentified-reel.mp4" \\`,
          `  -F "provided_label=Those who pay" \\`,
          `  -F "depth=standard"`,
        ].join('\n');
        return;
      }
      const lines = [`curl -X ${method} ${base}${path} \\`];
      if (needsKey) lines.push(`  -H "Authorization: Bearer ${key}" \\`);
      if (body) {
        lines.push('  -H "Content-Type: application/json" \\');
        lines.push(`  -d '${body.replace(/\n\s*/g, '')}'`);
      } else {
        lines[lines.length - 1] = lines[lines.length - 1].replace(/ \\$/, '');
      }
      snippet.textContent = lines.join('\n');
      return;
    }

    if (language === 'python') {
      if (isUpload) {
        snippet.textContent = [
          'import httpx',
          '',
          `KEY = "${key}"`,
          '',
          'with open("unidentified-reel.mp4", "rb") as handle:',
          `    response = httpx.post(`,
          `        "${base}${path}",`,
          '        headers={"Authorization": f"Bearer {KEY}"},',
          '        files={"fragment": ("reel.mp4", handle, "video/mp4")},',
          '        data={"provided_label": "Those who pay", "depth": "standard"},',
          '        timeout=300,',
          '    )',
          '',
          'dossier = response.json()',
          'print(dossier["meta"]["verdict"])',
          'for claim in dossier["data"]["evidence"]["claims"]:',
          '    print(claim["stance"], claim["claim_text"])',
        ].join('\n');
        return;
      }
      const lines = ['import httpx', ''];
      if (needsKey) lines.push(`KEY = "${key}"`, '');
      lines.push('response = httpx.' + method.toLowerCase() + '(');
      lines.push(`    "${base}${path}",`);
      if (needsKey) lines.push('    headers={"Authorization": f"Bearer {KEY}"},');
      if (body) lines.push(`    json=${body.replace(/"/g, '"')},`);
      lines.push('    timeout=300,');
      lines.push(')');
      lines.push('print(response.json())');
      snippet.textContent = lines.join('\n');
      return;
    }

    if (isUpload) {
      snippet.textContent = [
        `const KEY = "${key}";`,
        '',
        'const body = new FormData();',
        'body.append("fragment", file);            // a File or Blob',
        'body.append("provided_label", "Those who pay");',
        'body.append("depth", "standard");',
        '',
        `const response = await fetch("${base}${path}", {`,
        '  method: "POST",',
        '  headers: { Authorization: `Bearer ${KEY}` },',
        '  body,',
        '});',
        'const dossier = await response.json();',
        'console.log(dossier.meta.verdict);',
      ].join('\n');
      return;
    }
    const lines = [];
    if (needsKey) lines.push(`const KEY = "${key}";`, '');
    lines.push(`const response = await fetch("${base}${path}", {`);
    lines.push(`  method: "${method}",`);
    const headers = [];
    if (needsKey) headers.push('Authorization: `Bearer ${KEY}`');
    if (body) headers.push('"Content-Type": "application/json"');
    if (headers.length) lines.push(`  headers: { ${headers.join(', ')} },`);
    if (body) lines.push(`  body: JSON.stringify(${body.replace(/\n\s*/g, ' ')}),`);
    lines.push('});');
    lines.push('const payload = await response.json();');
    snippet.textContent = lines.join('\n');
  }

  /* ---- send ------------------------------------------------------------ */
  document.querySelector('[data-play-form]').addEventListener('submit', async (event) => {
    event.preventDefault();
    const { method, path } = currentEndpoint();
    const send = document.querySelector('[data-send]');
    const needsKey = ['/v1/identify', '/v1/investigate', '/v1/watch', '/v1/eval/latest'].includes(path);
    const isUpload = path === '/v1/investigate';

    if (isUpload && !document.querySelector('[data-file]').files?.[0]) {
      statusLine.textContent = 'Choose a file first.';
      return;
    }

    send.disabled = true;
    send.textContent = 'Sending…';
    statusLine.textContent = `${method} ${path} …`;
    out.textContent = 'Waiting for the live service…';
    copyResponse.hidden = true;
    showBoard.hidden = true;
    board.hidden = true;
    const started = performance.now();

    try {
      const headers = {};
      if (needsKey) headers.authorization = `Bearer ${await mintKey(false)}`;
      let requestBody;
      if (isUpload) {
        requestBody = new FormData();
        requestBody.append('fragment', document.querySelector('[data-file]').files[0]);
        const label = document.querySelector('[data-label]').value.trim();
        if (label) requestBody.append('provided_label', label);
        requestBody.append('depth', 'standard');
      } else if (!bodyWrap.hidden) {
        headers['content-type'] = 'application/json';
        requestBody = bodyField.value;
      }

      const response = await fetch(path, { method, headers, body: requestBody });
      const elapsed = ((performance.now() - started) / 1000).toFixed(1);
      const payload = await response.json();
      lastPayload = payload;
      statusLine.textContent = `${response.status} ${response.statusText} · ${elapsed}s`;
      statusLine.className = `play-status ${response.ok ? 'ok' : 'bad'}`;
      out.textContent = JSON.stringify(payload, null, 2);
      copyResponse.hidden = false;
      showBoard.hidden = !(response.ok && payload?.data?.gate);
    } catch (error) {
      statusLine.textContent = 'Request failed';
      statusLine.className = 'play-status bad';
      out.textContent = String(error.message || error);
    } finally {
      send.disabled = false;
      send.textContent = 'Send request';
    }
  });

  copyResponse.addEventListener('click', async () => {
    await navigator.clipboard.writeText(out.textContent).catch(() => {});
    copyResponse.textContent = 'Copied';
    setTimeout(() => { copyResponse.textContent = 'Copy response'; }, 1500);
  });

  showBoard.addEventListener('click', () => {
    if (lastPayload) renderBoard(lastPayload, board);
  });

  syncForm();
})();
