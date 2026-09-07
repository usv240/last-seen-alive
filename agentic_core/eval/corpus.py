"""Load the real evaluation corpus into the shape `run_eval` expects.

There were three impedance mismatches between the corpus on disk and the
harness, and every one of them would have surfaced for the first time during the
single held-out run — the run that by design cannot be repeated:

  1. `manifest.json` and `ground_truth.json` are **lists** of records keyed by
     `case_id`; `run_eval` wants a mapping of item id to record.
  2. The files are named `fragment_D01.mp4` for case `D01`, so resolving by file
     stem finds nothing.
  3. The manifest calls the sealed split `holdout`; the harness and the taint
     ledger call it `held-out`.

Doing the translation here, with a test that runs against the actual files,
means the adapter is exercised long before eval day rather than on it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: Harness split names, keyed by the name used in the manifest.
SPLIT_NAMES = {"dev": "dev", "holdout": "held-out"}


def _read(path: Path) -> list[dict[str, Any]]:
    # The corpus files were written by PowerShell and carry a UTF-8 BOM.
    return json.loads(path.read_text(encoding="utf-8-sig"))


class EvaluationCorpus:
    """The manifest, the answer key and the media, resolved and cross-checked."""

    def __init__(self, eval_dir: Path) -> None:
        self.eval_dir = eval_dir
        self.manifest = {row["case_id"]: row for row in _read(eval_dir / "manifest.json")}
        answer_path = eval_dir / "answer_key" / "ground_truth.json"
        self.answer_key_raw = (
            {row["case_id"]: row for row in _read(answer_path)} if answer_path.exists() else {}
        )

    def files(self) -> dict[str, Path]:
        """Item id to media file, taken from the manifest rather than guessed."""
        return {
            case_id: self.eval_dir / row["file"] for case_id, row in self.manifest.items()
        }

    def answer_key(self) -> dict[str, dict[str, Any]]:
        """Answer-key records keyed by item id, with harness split names.

        Falls back to the public manifest when the sealed answer key is absent,
        so the harness can still be wired up and tested without it.
        """
        source = self.answer_key_raw or self.manifest
        return {
            case_id: {**row, "split": SPLIT_NAMES.get(row["split"], row["split"])}
            for case_id, row in source.items()
        }

    def verify(self) -> list[str]:
        """Report every reason this corpus could not be evaluated. Empty is good."""
        problems: list[str] = []
        files = self.files()
        for case_id, row in self.manifest.items():
            path = files[case_id]
            if not path.exists():
                problems.append(f"{case_id}: media file missing at {row['file']}")
                continue
            if path.stat().st_size != row["bytes"]:
                problems.append(
                    f"{case_id}: size {path.stat().st_size} does not match manifest {row['bytes']}"
                )
        if self.answer_key_raw:
            missing = sorted(set(self.manifest) - set(self.answer_key_raw))
            if missing:
                problems.append(f"answer key does not cover: {missing}")
            extra = sorted(set(self.answer_key_raw) - set(self.manifest))
            if extra:
                problems.append(f"answer key covers cases not in the manifest: {extra}")
        for case_id, row in self.manifest.items():
            if row["split"] not in SPLIT_NAMES:
                problems.append(f"{case_id}: unknown split {row['split']!r}")
        return problems

    def ids_for(self, split: str) -> list[str]:
        """Item ids in a split, named as the harness names them."""
        return sorted(
            case_id
            for case_id, row in self.manifest.items()
            if SPLIT_NAMES.get(row["split"]) == split
        )
