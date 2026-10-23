"""Regression tests for the fetcher's manifest handling and exit codes.

No network and no fork clone: the replay harness is a stub, and the
manifest/rounds paths are pointed at a temporary directory. Run from this
directory: ``python3 -m unittest test_fetch_rounds``.

Defects under test:

- a partial re-run (``--rounds 12``) rewrote ``rounds-manifest.json`` with
  only the fetched rounds, destroying the committed pins of every other
  round; the manifest now merges with its previous content;
- a failed fetch of ``outputs/validator_scores.json`` (required by the
  evaluation) was recorded in the manifest but still exited 0;
- v12-era rounds (manifest pins ``code.diversity_formula``) were fetched
  without ``inputs/diversity_inputs.json`` and ``outputs/final_scores.json``,
  which ``shadow_eval.py --scorer-version 3`` needs; they are now fetched,
  pinned, and required exactly when the round pins the diversity formula.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fetch_rounds  # noqa: E402


def _stub_harness(payload, status: int = 0) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        SERVICE_URLS={"testnet": "https://scoring-testnet.postfiat.org"},
        fetch_round=lambda network, round_number, out_dir: status,
        _fetch_json=lambda url: payload,
    )


BASE = "https://scoring-testnet.postfiat.org/api/scoring/rounds"
DIVERSITY_CODE = {"diversity_formula": {"inputs": "inputs/diversity_inputs.json"}}


def _route_harness(routes: dict, code: dict) -> types.SimpleNamespace:
    """A harness whose fetch writes the round manifest and serves by URL."""

    def fetch_round(network, round_number, out_dir):
        manifest = out_dir / f"{network}-r{round_number}" / "runtime" / "execution_manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"code": code}))
        return 0

    return types.SimpleNamespace(
        SERVICE_URLS={"testnet": "https://scoring-testnet.postfiat.org"},
        fetch_round=fetch_round,
        _fetch_json=routes.get,
    )


class FetchRoundsManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="fetch-rounds-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self._saved = (
            fetch_rounds.MANIFEST_PATH,
            fetch_rounds.ROUNDS_DIR,
            fetch_rounds._load_harness,
        )
        self.addCleanup(self._restore)
        fetch_rounds.MANIFEST_PATH = tmp / "rounds-manifest.json"
        fetch_rounds.ROUNDS_DIR = tmp / "rounds"

    def _restore(self) -> None:
        (
            fetch_rounds.MANIFEST_PATH,
            fetch_rounds.ROUNDS_DIR,
            fetch_rounds._load_harness,
        ) = self._saved

    @staticmethod
    def _fetch(rounds: list[int], payload, status: int = 0) -> int:
        fetch_rounds._load_harness = lambda: _stub_harness(payload, status)
        with contextlib.redirect_stdout(io.StringIO()):
            return fetch_rounds.fetch(rounds)

    def _manifest(self) -> dict:
        return json.loads(fetch_rounds.MANIFEST_PATH.read_text())

    def test_partial_rerun_preserves_unfetched_round_pins(self) -> None:
        fetch_rounds.MANIFEST_PATH.write_text(
            json.dumps(
                {
                    "network": "testnet",
                    "service": "https://scoring-testnet.postfiat.org",
                    "harness": "stub",
                    "rounds": {
                        "12": {"old.json": {"sha256": "aa", "bytes": 1}},
                        "13": {"kept.json": {"sha256": "bb", "bytes": 2}},
                    },
                    "failures": [
                        {"round": 12, "file": "stale.json", "reason": "old"},
                        {"round": 13, "file": "kept.json", "reason": "kept"},
                    ],
                }
            )
        )
        code = self._fetch([12], payload={"validator_scores": []})
        self.assertEqual(code, 0)
        manifest = self._manifest()
        # Round 13's pins and failure survive; round 12's stale ones do not.
        self.assertEqual(
            manifest["rounds"]["13"], {"kept.json": {"sha256": "bb", "bytes": 2}}
        )
        self.assertIn("outputs/validator_scores.json", manifest["rounds"]["12"])
        self.assertNotIn("old.json", manifest["rounds"]["12"])
        self.assertEqual(
            manifest["failures"],
            [{"round": 13, "file": "kept.json", "reason": "kept"}],
        )

    def test_missing_required_artifact_fails_the_run(self) -> None:
        code = self._fetch([12], payload=None)
        self.assertEqual(code, 1)
        self.assertEqual(
            self._manifest()["failures"],
            [
                {
                    "round": 12,
                    "file": "outputs/validator_scores.json",
                    "reason": "fetch failed",
                }
            ],
        )

    def _fetch_routes(self, routes: dict, code: dict) -> int:
        fetch_rounds._load_harness = lambda: _route_harness(routes, code)
        with contextlib.redirect_stdout(io.StringIO()):
            return fetch_rounds.fetch([28])

    def test_v12_round_fetches_and_pins_diversity_inputs_and_final_scores(self) -> None:
        diversity = {"resolved_endpoints": 1, "validators": []}
        finals = {"scores": []}
        code = self._fetch_routes(
            {
                f"{BASE}/28/outputs/validator_scores.json": {"validator_scores": []},
                f"{BASE}/28/input/inputs/diversity_inputs.json": diversity,
                f"{BASE}/28/outputs/final_scores.json": finals,
            },
            DIVERSITY_CODE,
        )
        self.assertEqual(code, 0)
        round_dir = fetch_rounds.ROUNDS_DIR / "testnet-r28"
        pins = self._manifest()["rounds"]["28"]
        for rel_path, payload in (
            ("inputs/diversity_inputs.json", diversity),
            ("outputs/final_scores.json", finals),
        ):
            path = round_dir / rel_path
            self.assertEqual(json.loads(path.read_text()), payload)
            self.assertEqual(
                pins[rel_path],
                {
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                },
            )
        self.assertEqual(self._manifest()["failures"], [])

    def test_v12_round_without_diversity_inputs_fails_the_run(self) -> None:
        code = self._fetch_routes(
            {
                f"{BASE}/28/outputs/validator_scores.json": {"validator_scores": []},
                f"{BASE}/28/outputs/final_scores.json": {"scores": []},
            },
            DIVERSITY_CODE,
        )
        self.assertEqual(code, 1)
        self.assertEqual(
            self._manifest()["failures"],
            [{"round": 28, "file": "inputs/diversity_inputs.json", "reason": "fetch failed"}],
        )

    def test_v12_round_without_final_scores_fails_the_run(self) -> None:
        code = self._fetch_routes(
            {
                f"{BASE}/28/outputs/validator_scores.json": {"validator_scores": []},
                f"{BASE}/28/input/inputs/diversity_inputs.json": {"validators": []},
            },
            DIVERSITY_CODE,
        )
        self.assertEqual(code, 1)
        self.assertEqual(
            self._manifest()["failures"],
            [{"round": 28, "file": "outputs/final_scores.json", "reason": "fetch failed"}],
        )

    def test_pre_formula_round_may_lack_the_v12_files(self) -> None:
        code = self._fetch_routes(
            {f"{BASE}/28/outputs/validator_scores.json": {"validator_scores": []}},
            {"score_formula": {}},
        )
        self.assertEqual(code, 0)
        self.assertEqual(self._manifest()["failures"], [])
        self.assertNotIn("inputs/diversity_inputs.json", self._manifest()["rounds"]["28"])

    def test_manifest_round_order_is_numeric_not_fetch_order(self) -> None:
        code = self._fetch([13, 9, 12], payload={"validator_scores": []})
        self.assertEqual(code, 0)
        self.assertEqual(list(self._manifest()["rounds"]), ["9", "12", "13"])


if __name__ == "__main__":
    unittest.main()
