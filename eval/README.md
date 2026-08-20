# Last Seen Alive — Ten-Fragment Evaluation v2

This is a deliberately adversarial feasibility set for one question: can the system identify an obscure historical moving-image fragment when the evidence supports it—and refuse a verdict when it does not?

The set contains ten visually reviewed, 50-second public-domain fragments. Five are development cases and five are sealed holdouts. It is balanced by expected behavior, not by ten easy identifications:

| Tier | Count | Required behavior |
|---|---:|---|
| A — rare intertitle | 3 | identify when the evidence gate passes |
| B — distinctive visual | 2 | identify when the evidence gate passes |
| C — ambiguity trap | 2 | return ranked candidates, never a verdict |
| D — insufficient evidence | 2 | abstain |
| E — historical misattribution | 1 | contradict the supplied label with evidence |

`manifest-v2.json` is public. `answer-key-v2/ground-truth.json` must be inaccessible to the research process and sealed before the holdout run. The manifest deliberately exposes the tier and desired decision class because this benchmark measures calibrated behavior; it never exposes the true identity.

Build with:

```powershell
.\build_dataset_v2.ps1 -Force
```

The builder downloads five adjacent ten-second segments per case from the Library of Congress, joins them, removes container metadata and chapters, removes audio, and produces anonymous H.264 MP4 files. One source has an identity footer baked into the scan; the builder crops that footer and records the transform. Offsets were chosen only after contact-sheet review.

The Tier E case is not synthetic. The Library of Congress record for *Through the breakers* says it was formerly supplied as *Those who pay*. The fragment is presented with that former label, and the required behavior is to surface—not inherit—the contradiction.

Do not run the holdout during development. Freeze code, prompts, thresholds, model version, tool budgets, dependency lock, and commit hash first; tag that commit `eval-freeze`. Then run each held-out case once through the taint-ledger-protected harness and publish failures as well as successes.
