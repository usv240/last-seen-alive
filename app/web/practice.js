/* The practitioner objection register, rendered from /v1/practice.

   Rendered from the endpoint rather than written into the HTML so the page
   cannot drift from the data the tests assert against. The unmet entries are
   rendered first and marked, because a register whose failures are buried at the
   bottom is doing the opposite of what it claims to do. */

(() => {
  const host = document.querySelector('[data-practice-register]');
  const tallyHost = document.querySelector('[data-practice-tally]');
  if (!host) return;

  const el = window.LSA ? window.LSA.el : (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };

  const STATUS_WORD = {
    met: 'Answered',
    partially_met: 'Partly answered',
    not_met: 'Unanswered',
  };

  const KIND_WORD = {
    peer_reviewed_study: 'Peer-reviewed study',
    professional_standard: 'Professional standard',
    national_archive_practice: 'National archive practice',
  };

  function entryCard(entry) {
    const card = el('article', undefined, 'card obj');
    card.dataset.status = entry.status;

    const head = el('div', undefined, 'obj-head');
    head.append(el('b', entry.id, 'obj-id'));
    const status = el('span', STATUS_WORD[entry.status] || entry.status, 'obj-status');
    status.dataset.status = entry.status;
    head.append(status);
    card.append(head);

    card.append(el('h3', entry.demand));

    const quote = el('blockquote', undefined, 'obj-quote');
    quote.append(el('p', `“${entry.quote}”`));
    const cite = el('cite');
    const link = el('a', entry.source.citation);
    link.href = entry.source.url;
    link.rel = 'noopener';
    cite.append(link);
    cite.append(el('span', ` — ${KIND_WORD[entry.source.kind] || entry.source.kind}`, 'obj-kind'));
    quote.append(cite);
    card.append(quote);

    card.append(el('p', entry.how_this_system_answers));

    if (entry.what_would_close_it) {
      const close = el('p', undefined, 'obj-close');
      close.append(el('b', 'What would close it: '));
      close.append(el('span', entry.what_would_close_it));
      card.append(close);
    }

    if ((entry.evidence || []).length) {
      const evidence = el('p', undefined, 'obj-evidence');
      evidence.append(el('b', 'Where to check: '));
      entry.evidence.forEach((item, index) => {
        if (index) evidence.append(el('span', ' · '));
        if (item.startsWith('/')) {
          const anchor = el('a', item);
          anchor.href = item;
          evidence.append(anchor);
        } else {
          evidence.append(el('code', item));
        }
      });
      card.append(evidence);
    }

    return card;
  }

  (async () => {
    try {
      const response = await fetch('/v1/practice');
      const payload = await response.json();
      if (!response.ok) throw new Error('unavailable');
      const data = payload.data;

      if (tallyHost) {
        const metrics = [
          [String(data.tally.met), 'answered'],
          [String(data.tally.not_met + data.tally.partially_met), 'unanswered'],
          [String(new Set(data.entries.map((e) => e.source.key)).size), 'sources cited'],
          ['0', 'archivists consulted'],
        ];
        tallyHost.replaceChildren();
        metrics.forEach(([value, label], index) => {
          const metric = el('div', undefined, index === 3 ? 'metric warn' : 'metric');
          metric.append(el('strong', value));
          metric.append(el('span', label));
          tallyHost.append(metric);
        });
      }

      const unmet = data.entries.filter((e) => e.status !== 'met');
      const met = data.entries.filter((e) => e.status === 'met');

      host.replaceChildren();

      const disclaimer = el('div', undefined, 'card lede-card');
      disclaimer.append(el('p', data.disclaimer));
      host.append(disclaimer);

      if (unmet.length) {
        host.append(el('p', 'Unanswered', 'subhead'));
        unmet.forEach((entry) => host.append(entryCard(entry)));
      }
      host.append(el('p', 'Answered', 'subhead'));
      met.forEach((entry) => host.append(entryCard(entry)));
    } catch (error) {
      host.replaceChildren(el('p', 'The register could not be loaded.', 'small'));
    }
  })();
})();
