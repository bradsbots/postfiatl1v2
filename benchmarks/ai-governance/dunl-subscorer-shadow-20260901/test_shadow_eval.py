"""Regression tests for the shadow evaluation's fail-loud guards.

These tests need the read-only ``dynamic-unl-scoring`` fork clone (whose
pinned module files ``shadow_eval`` loads) and the fetched ``rounds/``
data (gitignored); they skip only when one of those is genuinely absent
from the host. They need no third-party dependencies — ``shadow_eval``
loads the pinned fork files directly, exactly as the evaluation itself
runs — so they execute under a bare ``python3``. Run from this
directory: ``python3 -m unittest test_shadow_eval``.

Guards under test, each of which previously produced a plausible but wrong
number instead of failing:

- cutoff flips were computed against the hardcoded 40 even when the round
  pinned a different ``score_cutoff``;
- the pinned fork modules were never verified against the round's
  content-hash pins, so a drifted fork clone silently changed the numbers
  (the UNL-reproduction control does not catch formula drift);
- a validator present in the frozen entries but missing from the published
  model scores (or vice versa) was silently dropped from every metric, as
  was any duplicate-key collapse.

``test_loader_is_dependency_free`` additionally pins the property that
the guard suite must never skip for a missing optional dependency: the
fork loading path must not touch pydantic at all.

``test_round_16_reproduces_committed_results`` pins the round-16 report to
the committed ``results.json`` and ``results-v2.json`` entries, proving
later harness changes moved no v1/v2 number.

The v3 tests build a synthetic prompt-v12 round from round 16 (diversity
section, ``inputs/diversity_inputs.json``, ``outputs/final_scores.json``,
25 seats, one validator failing the minimum safe version), with the
published outputs computed by the pinned fork modules themselves, and
check that the harness reads the diversity section, cross-checks the
published final scores, takes the seat count from the manifest, and
refuses a fork clone behind its ``origin/main``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND_16 = HERE / "rounds" / "testnet-r16"
FORK_ROOT = Path.home() / "repos" / "dynamic-unl-scoring"

sys.path.insert(0, str(HERE))

if FORK_ROOT.exists():
    import shadow_eval
    import subscorer
    import subscorer_v3
else:  # only a genuinely absent fork clone may skip this suite
    shadow_eval = None


@unittest.skipIf(shadow_eval is None, f"fork clone not found at {FORK_ROOT}")
@unittest.skipUnless(ROUND_16.exists(), "frozen rounds not fetched (rounds/ is gitignored)")
class ShadowEvalGuardTest(unittest.TestCase):
    def test_loader_is_dependency_free(self) -> None:
        # The evaluation and this guard suite must run under a bare
        # interpreter: loading shadow_eval must not import pydantic (the
        # fork package's optional dependency), and the pinned files whose
        # logic actually runs must be the real fork files.
        self.assertNotIn("pydantic", sys.modules)
        for name, path in shadow_eval._PINNED_MODULE_FILES.items():
            self.assertTrue(path.is_file(), f"{name}: {path} missing")
        self.assertEqual(
            Path(sys.modules["scoring_service.services.unl_selector"].__file__),
            shadow_eval._PINNED_MODULE_FILES[
                "scoring_service.services.unl_selector"
            ],
        )

    def _round_copy(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="shadow-eval-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        dst = tmp / "testnet-r16"
        shutil.copytree(ROUND_16, dst)
        return dst

    @staticmethod
    def _edit_manifest(round_dir: Path, edit) -> None:
        path = round_dir / "runtime" / "execution_manifest.json"
        manifest = json.loads(path.read_text())
        edit(manifest)
        path.write_text(json.dumps(manifest))

    def test_cutoff_pin_mismatch_fails_loudly(self) -> None:
        round_dir = self._round_copy()
        self._edit_manifest(
            round_dir,
            lambda m: m["code"]["selector"]["parameters"].__setitem__(
                "score_cutoff", 60
            ),
        )
        with self.assertRaisesRegex(ValueError, "score_cutoff 60"):
            shadow_eval.evaluate_round(round_dir)

    def test_fork_module_drift_fails_loudly(self) -> None:
        round_dir = self._round_copy()
        self._edit_manifest(
            round_dir,
            lambda m: m["code"]["score_formula"].__setitem__(
                "content_sha256", "0" * 64
            ),
        )
        with self.assertRaisesRegex(ValueError, "score_formula"):
            shadow_eval.evaluate_round(round_dir)

    def test_missing_model_score_fails_loudly(self) -> None:
        round_dir = self._round_copy()
        path = round_dir / "outputs" / "validator_scores.json"
        data = json.loads(path.read_text())
        del data["validator_scores"][7]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "validator sets differ"):
            shadow_eval.evaluate_round(round_dir)

    def test_duplicate_validator_id_fails_loudly(self) -> None:
        round_dir = self._round_copy()
        path = round_dir / "inputs" / "model_request.json"
        request = json.loads(path.read_text())
        content = request["messages"][-1]["content"]
        entries = subscorer.extract_validator_entries(request)
        index = content.find(subscorer.VALIDATOR_DATA_MARKER)
        request["messages"][-1]["content"] = (
            content[:index]
            + subscorer.VALIDATOR_DATA_MARKER
            + "\n"
            + json.dumps(entries + [entries[0]])
        )
        path.write_text(json.dumps(request))
        with self.assertRaisesRegex(ValueError, "duplicate validator_id"):
            shadow_eval.evaluate_round(round_dir)

    def test_round_16_reproduces_committed_results(self) -> None:
        for scorer_version, results_name in ((1, "results.json"), (2, "results-v2.json")):
            committed = {
                r["round"]: r
                for r in json.loads((HERE / results_name).read_text())["rounds"]
            }["testnet-r16"]
            report = shadow_eval.evaluate_round(ROUND_16, scorer_version)
            self.assertEqual(report, committed)


DIVERSITY_MODULE = "scoring_service.services.diversity_formula"


@unittest.skipIf(shadow_eval is None, f"fork clone not found at {FORK_ROOT}")
@unittest.skipUnless(ROUND_16.exists(), "frozen rounds not fetched (rounds/ is gitignored)")
class ShadowEvalV3Test(unittest.TestCase):
    """The v3 harness on a synthetic prompt-v12 round (25 seats, formula v1)."""

    FLAGGED = 0  # index of the validator failing the minimum safe version

    def _make_v12_round(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="shadow-eval-v3-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        round_dir = tmp / "testnet-r16"
        shutil.copytree(ROUND_16, round_dir)
        load = lambda rel: json.loads((round_dir / rel).read_text())  # noqa: E731
        dump = lambda rel, data: (round_dir / rel).write_text(json.dumps(data))  # noqa: E731

        request = load("inputs/model_request.json")
        entries = subscorer.extract_validator_entries(request)
        for index, entry in enumerate(entries):
            entry["fails_minimum_safe_version"] = index == self.FLAGGED
        content = request["messages"][-1]["content"]
        marker = content.find(subscorer.VALIDATOR_DATA_MARKER)
        request["messages"][-1]["content"] = (
            content[:marker] + subscorer.VALIDATOR_DATA_MARKER + "\n" + json.dumps(entries)
        )
        dump("inputs/model_request.json", request)

        model = {v["master_key"]: v for v in load("outputs/validator_scores.json")["validator_scores"]}
        keys = sorted(model)
        validators = [
            {
                "master_key": mk,
                "country_validators": 1 + i % 6,
                "provider_validators": None if i % 9 == 0 else 1 + i % 4,
            }
            for i, mk in enumerate(keys)
        ]
        inputs = {
            "resolved_endpoints": sum(v["provider_validators"] is not None for v in validators),
            "validators": validators,
        }
        dump("inputs/diversity_inputs.json", inputs)

        formula = sys.modules[DIVERSITY_MODULE]
        manifest = load("runtime/execution_manifest.json")
        code = manifest["code"]
        code["prompt"]["version"] = "v12"
        code["selector"]["parameters"]["max_size"] = 25
        code["diversity_formula"] = {
            "module": DIVERSITY_MODULE,
            "content_sha256": hashlib.sha256(Path(formula.__file__).read_bytes()).hexdigest(),
            "version": formula.DIVERSITY_FORMULA_VERSION,
            "parameters": formula.diversity_formula_parameters(),
            "inputs": "inputs/diversity_inputs.json",
        }
        dump("runtime/execution_manifest.json", manifest)

        # Published outputs, computed by the pinned fork modules.
        diversity = {
            v["master_key"]: formula.compute_diversity(
                v["country_validators"], v["provider_validators"], inputs["resolved_endpoints"]
            )
            for v in validators
        }
        finals = {
            mk: shadow_eval.compute_final_score(
                model[mk]["consensus"], model[mk]["reliability"], model[mk]["software"],
                diversity[mk], model[mk]["identity"],
            )
            for mk in keys
        }
        previous = load("inputs/previous_unl.json")["previous_unl"]
        unl = shadow_eval._select(finals, previous, code["selector"]["parameters"])
        dump("outputs/selected_unl.json", {"unl": unl, "alternates": []})
        dump("outputs/final_scores.json", {
            "formula": {"version": 1},
            "diversity_formula": {"version": formula.DIVERSITY_FORMULA_VERSION},
            "scores": [
                {
                    "master_key": mk,
                    "model_score": model[mk]["score"],
                    "final_score": finals[mk],
                    "model_diversity": model[mk]["diversity"],
                    "diversity": diversity[mk],
                }
                for mk in keys
            ],
        })
        self.diversity, self.unl, self.entries = diversity, unl, entries
        return round_dir

    @staticmethod
    def _edit_json(round_dir: Path, rel: str, edit) -> None:
        path = round_dir / rel
        data = json.loads(path.read_text())
        edit(data)
        path.write_text(json.dumps(data))

    def test_v12_round_reads_the_diversity_section(self) -> None:
        round_dir = self._make_v12_round()
        report = shadow_eval.evaluate_round(round_dir, 3)
        self.assertTrue(report["baseline_reproduces_published_unl"])
        self.assertEqual(report["diversity_source"], "code.diversity_formula")
        self.assertTrue(report["final_scores_match_published"])
        self.assertEqual(report["subscorer_v3_sha256"], hashlib.sha256(
            Path(subscorer_v3.__file__).read_bytes()).hexdigest())
        # The candidate's diversity is the fork formula's, not the model's.
        for case in report["cutoff_boundary_cases"]:
            self.assertEqual(
                case["deterministic_subscores"]["diversity"], self.diversity[case["master_key"]]
            )

    def test_minimum_safe_version_failure_reaches_the_candidate(self) -> None:
        round_dir = self._make_v12_round()
        validator_map = json.loads((round_dir / "inputs" / "validator_map.json").read_text())
        flagged = validator_map[self.entries[self.FLAGGED]["validator_id"]]["master_key"]
        scores = shadow_eval.candidate_subscores(round_dir, 3)
        self.assertEqual(scores[flagged]["software"], 0)

    def test_seat_count_comes_from_the_manifest(self) -> None:
        round_dir = self._make_v12_round()
        report = shadow_eval.evaluate_round(round_dir, 3)
        self.assertEqual(report["selector_parameters"]["max_size"], 25)
        self.assertEqual(report["published_unl_size"], 25)
        self.assertLessEqual(report["deterministic_unl_size"], 25)
        self.assertEqual(report["acceptance"]["unl_overlap_min"], 24)
        self.assertEqual(
            report["acceptance"]["unl_overlap_ok"], report["unl_overlap"] >= 24
        )
        self._edit_json(
            round_dir, "runtime/execution_manifest.json",
            lambda m: m["code"]["selector"]["parameters"].__setitem__("max_size", 20),
        )
        with self.assertRaisesRegex(ValueError, "max_size 20"):
            shadow_eval.evaluate_round(round_dir, 3)

    def test_diversity_pin_drift_fails_loudly(self) -> None:
        round_dir = self._make_v12_round()
        self._edit_json(
            round_dir, "runtime/execution_manifest.json",
            lambda m: m["code"]["diversity_formula"].__setitem__("content_sha256", "0" * 64),
        )
        with self.assertRaisesRegex(ValueError, "diversity_formula"):
            shadow_eval.evaluate_round(round_dir, 3)

    def test_diversity_parameter_drift_fails_loudly(self) -> None:
        round_dir = self._make_v12_round()
        self._edit_json(
            round_dir, "runtime/execution_manifest.json",
            lambda m: m["code"]["diversity_formula"]["parameters"].__setitem__("axis_penalty", 120),
        )
        with self.assertRaisesRegex(ValueError, "diversity_formula parameters"):
            shadow_eval.evaluate_round(round_dir, 3)

    def test_published_final_score_disagreement_fails_loudly(self) -> None:
        round_dir = self._make_v12_round()
        self._edit_json(
            round_dir, "outputs/final_scores.json",
            lambda d: d["scores"][3].__setitem__("final_score", d["scores"][3]["final_score"] + 1),
        )
        with self.assertRaisesRegex(ValueError, "final_scores"):
            shadow_eval.evaluate_round(round_dir, 3)

    def test_missing_diversity_input_fails_loudly(self) -> None:
        round_dir = self._make_v12_round()
        self._edit_json(round_dir, "inputs/diversity_inputs.json", lambda d: d["validators"].pop())
        with self.assertRaisesRegex(ValueError, "diversity inputs"):
            shadow_eval.evaluate_round(round_dir, 3)

    def test_pre_formula_round_keeps_the_published_model_diversity(self) -> None:
        report = shadow_eval.evaluate_round(ROUND_16, 3)
        self.assertEqual(report["diversity_source"], "model")
        self.assertEqual(report["dimension_deltas"]["diversity"], {"mean_abs": 0, "max_abs": 0})
        self.assertTrue(report["baseline_reproduces_published_unl"])


@unittest.skipIf(shadow_eval is None, f"fork clone not found at {FORK_ROOT}")
class ForkCloneCurrencyTest(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    def test_clone_behind_origin_main_is_refused(self) -> None:
        repo = Path(tempfile.mkdtemp(prefix="fork-clone-"))
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        self._git(repo, "init", "-q", "-b", "main")
        for message in ("one", "two"):
            self._git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit",
                      "-q", "--allow-empty", "-m", message)
        self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        self._git(repo, "reset", "-q", "--hard", "HEAD~1")
        state = shadow_eval.fork_checkout_state(repo)
        self.assertEqual(state["behind_origin_main"], 1)
        with self.assertRaisesRegex(ValueError, "behind origin/main"):
            shadow_eval.require_current_fork(state)
        self._git(repo, "reset", "-q", "--hard", "origin/main")
        shadow_eval.require_current_fork(shadow_eval.fork_checkout_state(repo))

    def test_loaded_fork_clone_is_at_its_origin_main(self) -> None:
        state = shadow_eval.fork_checkout_state(FORK_ROOT)
        self.assertEqual(state["commit"], state["origin_main"])


if __name__ == "__main__":
    unittest.main()
