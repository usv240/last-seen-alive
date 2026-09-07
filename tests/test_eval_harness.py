from pathlib import Path

import pytest

from agentic_core.eval import EvalItemResult, run_eval


class Frozen:
    def verify(self, frozen_commit: str) -> None:
        assert frozen_commit == "abc123"


def test_held_out_item_cannot_be_rerun(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "fragment-01.bin").write_bytes(b"original material")
    answer_key = {"fragment-01": {"split": "held-out", "expected": "abstain"}}

    def system(path: Path, expected: object) -> EvalItemResult:
        return EvalItemResult(item_id=path.stem, outcome="abstained", latency_ms=1)

    kwargs = {
        "split": "held-out",
        "frozen_commit": "abc123",
        "verifier": Frozen(),
        "ledger_path": tmp_path / "ledger.json",
    }
    report = run_eval(system, corpus, answer_key, **kwargs)
    assert report.counts()["abstained"] == 1
    with pytest.raises(RuntimeError, match="TAINTED"):
        run_eval(system, corpus, answer_key, **kwargs)


def test_report_includes_hashes_failures_and_latency(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "fragment-01.bin").write_bytes(b"dev material")
    answer_key = {"fragment-01": {"split": "dev", "expected": "identify"}}
    report = run_eval(
        lambda path, expected: EvalItemResult(
            item_id=path.stem,
            outcome="false_confident",
            latency_ms=25,
            citation_decisive=2,
            citation_supported=1,
            partner_cost_usd=0.02,
            failure_note="Competing attribution was not disproved.",
        ),
        corpus,
        answer_key,
        split="dev",
        frozen_commit="working-tree",
        verifier=Frozen(),
        ledger_path=tmp_path / "ledger.json",
    ).to_dict()
    assert report["counts"]["false_confident"] == 1
    assert report["citation_precision"] == 0.5
    assert report["p95_latency_ms"] == 25
    assert len(report["corpus_sha256"]["fragment-01.bin"]) == 64



# --- the real corpus ------------------------------------------------------
#
# The held-out split is run exactly once and cannot be retried. Every one of
# these mismatches would otherwise have surfaced for the first time on that run.

from agentic_core.eval import EvaluationCorpus  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


def test_real_corpus_resolves_and_matches_its_manifest() -> None:
    corpus = EvaluationCorpus(EVAL_DIR)
    assert corpus.verify() == []
    assert corpus.ids_for("dev") == ["D01", "D02", "D03", "D04", "D05"]
    assert corpus.ids_for("held-out") == ["H01", "H02", "H03", "H04", "H05"]


def test_real_corpus_filenames_do_not_equal_case_ids() -> None:
    """Guards the assumption the harness used to make.

    If this ever becomes false the stem-matching fallback would start working by
    accident, and the explicit mapping would look unnecessary. It is not.
    """
    files = EvaluationCorpus(EVAL_DIR).files()
    assert files["D01"].stem == "fragment_D01" != "D01"


def test_harness_runs_the_real_development_split(tmp_path: Path) -> None:
    corpus = EvaluationCorpus(EVAL_DIR)
    seen: list[str] = []

    def system(path: Path, expected: object) -> EvalItemResult:
        case_id = path.stem.removeprefix("fragment_")
        seen.append(case_id)
        return EvalItemResult(item_id=case_id, outcome="abstained", latency_ms=1)

    report = run_eval(
        system,
        EVAL_DIR / "fragments-v2" / "dev",
        corpus.answer_key(),
        split="dev",
        frozen_commit="unused-for-dev",
        verifier=Frozen(),
        ledger_path=tmp_path / "ledger.json",
        item_files=corpus.files(),
    )
    assert seen == ["D01", "D02", "D03", "D04", "D05"]
    assert len(report.corpus_sha256) == 5


def test_harness_hashes_match_the_published_manifest(tmp_path: Path) -> None:
    """The report's hashes have to be the hashes the manifest publishes."""
    corpus = EvaluationCorpus(EVAL_DIR)
    report = run_eval(
        lambda path, expected: EvalItemResult(
            item_id=path.stem.removeprefix("fragment_"), outcome="abstained", latency_ms=1
        ),
        EVAL_DIR / "fragments-v2" / "dev",
        corpus.answer_key(),
        split="dev",
        frozen_commit="unused-for-dev",
        verifier=Frozen(),
        ledger_path=tmp_path / "ledger.json",
        item_files=corpus.files(),
    )
    for case_id in corpus.ids_for("dev"):
        filename = Path(corpus.manifest[case_id]["file"]).name
        assert report.corpus_sha256[filename] == corpus.manifest[case_id]["sha256"]
