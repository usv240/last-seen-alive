/* The investigation console.

   An investigation is slow: five Gemini agents and several live Parallel
   calls. Measured across the five development fragments with the credential
   attached, a run takes 225s to 430s, median 383s (eval/reports/
   arm-c-development.json). A spinner for six minutes tells the viewer nothing
   and reads as a hang. But the wait is also the single best opportunity this
   product has to explain itself, because what it is doing during those
   minutes *is* the argument for the product.

   So the wait shows the six named stages, which agent owns each one, and
   which Parallel surface it is calling. Stages advance on a timer, which
   means the display is an honest description of the pipeline's shape rather
   than a live trace — the API returns one response at the end, so there is
   no per-stage event to bind to. The elapsed clock is real, and the final
   state is replaced entirely by the response. Nothing here ever claims a
   stage produced a result.

   These durations were first written from a pre-credential estimate that
   totalled 100 seconds. Against the real measurement that was 4x optimistic,
   so the console walked to the last stage in under two minutes and then sat
   on it for four more — the exact hang-reading this file exists to prevent.
   The per-stage figures below are the original proportions rescaled to the
   measured median. They are a shape, not an instrument: only the clock and
   the final response report anything measured about *this* run. */

(() => {
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };

  const STAGES = [
    ['Visual Examiner', 'Gemini reads the frames and transcribes any visible text verbatim', 42],
    ['Phrase Hunter', 'Parallel Search hunts the rarest strings as literal quoted phrases', 77],
    ['Holdings Researcher', 'Parallel Task and FindAll check alternate titles and name the catalogues', 100],
    ['Skeptic', 'Parallel Search looks for evidence against its own candidates', 69],
    ['Evidence Compiler', 'Gemini restates the findings as typed, citable claims', 38],
    ['Verification', 'Parallel Extract re-opens every cited page, then the gate counts thresholds', 57],
  ];

  //: The measured spread of a full run, in seconds, across the development
  //: split. Shown before the clock starts so a long wait is an expectation
  //: rather than a surprise.
  const TYPICAL_LOW = 225;
  const TYPICAL_HIGH = 430;

  class RunConsole {
    constructor(host) {
      this.host = host;
      this.timers = [];
      this.start = 0;
    }

    _clear() {
      this.timers.forEach(clearTimeout);
      this.timers = [];
      if (this.tick) clearInterval(this.tick);
      this.tick = null;
    }

    idle(message) {
      this._clear();
      const box = el('div', undefined, 'run-empty');
      box.append(el('span', '⌕', 'glyph'));
      box.append(el('b', message || 'No investigation running'));
      box.append(el('p', `Choose a fragment, or upload your own, and the workflow will run here. A run takes ${Math.round(TYPICAL_LOW / 60)}-${Math.ceil(TYPICAL_HIGH / 60)} minutes against live sources. Nothing is sent until you press the button.`));
      this.host.replaceChildren(box);
    }

    begin(label) {
      this._clear();
      this.start = performance.now();

      const head = el('div', undefined, 'run-head');
      head.append(el('b', label, 'small'));
      this.clock = el('span', '0.0s', 'run-clock');
      head.append(this.clock);

      // Say the cost before charging it. Six minutes is a long time to watch a
      // clock you were not warned about, and a viewer who expects it reads a
      // slow stage as work rather than as a failure.
      const note = el('p', undefined, 'run-note');
      note.append(el('b', `Typically ${Math.round(TYPICAL_LOW / 60)}-${Math.ceil(TYPICAL_HIGH / 60)} minutes.`));
      note.append(el('span', ' Real archival research against live sources, not a cached answer. Leave this tab open; the dossier replaces this panel when it lands.'));

      const list = el('ol', undefined, 'stagelist');
      this.rows = STAGES.map(([name, detail], index) => {
        const row = el('li', undefined, 'stage');
        row.append(el('span', String(index + 1), 'stage-mark'));
        const body = el('div');
        body.append(el('b', name));
        body.append(el('span', detail));
        row.append(body);
        list.append(row);
        return row;
      });

      this.host.replaceChildren(head, note, list);

      // Advance through the stages on the pipeline's usual cadence. If the
      // response comes back sooner, `finish` cancels the rest; if it takes
      // longer, the last stage simply stays active rather than pretending
      // the run is complete.
      let elapsed = 0;
      STAGES.forEach(([, , seconds], index) => {
        this.timers.push(setTimeout(() => this._activate(index), elapsed * 1000));
        elapsed += seconds;
      });
      this._activate(0);

      this.tick = setInterval(() => {
        this.clock.textContent = ((performance.now() - this.start) / 1000).toFixed(1) + 's';
      }, 100);
    }

    _activate(index) {
      this.rows.forEach((row, position) => {
        row.classList.toggle('active', position === index);
        row.classList.toggle('done', position < index);
        if (position < index) row.querySelector('.stage-mark').textContent = '✓';
      });
    }

    /** Mark every stage complete and stop the clock at its real value. */
    finish() {
      this._clear();
      if (!this.rows) return 0;
      this.rows.forEach((row) => {
        row.classList.remove('active');
        row.classList.add('done');
        row.querySelector('.stage-mark').textContent = '✓';
      });
      const seconds = (performance.now() - this.start) / 1000;
      if (this.clock) this.clock.textContent = seconds.toFixed(1) + 's';
      return seconds;
    }

    outcome(payload) {
      const seconds = this.finish();
      const meta = payload.meta || {};
      const gate = meta.gate || {};
      const summary = el('dl', undefined, 'run-outcome');
      const rows = [
        ['Verdict', meta.verdict || 'unknown'],
        ['Thresholds passed', (gate.passed || []).length + ' of ' + Object.keys(gate.thresholds || {}).length],
        ['Parallel surfaces called', (meta.parallel_surfaces_used || []).join(', ') || 'none'],
        ['Elapsed', seconds.toFixed(1) + 's'],
      ];
      rows.forEach(([term, value]) => summary.append(el('dt', term), el('dd', String(value))));
      this.host.append(summary);
    }

    error(detail) {
      this._clear();
      const box = el('div', undefined, 'run-error');
      box.append(el('b', detail.message || 'The workflow did not run.'));
      if (detail.fix) box.append(el('p', detail.fix));
      if (detail.code === 'partner_credential_not_configured') {
        box.append(el('p', 'No result was fabricated. Parallel is the only open-web path in this product, so without it the workflow stops rather than guessing.'));
      }
      this.host.replaceChildren(box);
    }
  }

  window.LSA_RunConsole = RunConsole;
})();
