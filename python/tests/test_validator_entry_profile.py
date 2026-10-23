"""Shared-fixture tests for the Python mirror of the strict entry profile.

The Rust module's ``validator_entry_profile_tests.rs`` checks the same fixture
cases. Both sides must produce the canonical bytes of each case's expected
output; this side also checks their SHA-256. The module hashes the manifest can
pin are recorded in ``fixtures/modules.json``.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from postfiat_rpc import validator_entry_profile as vep  # noqa: E402

FIXTURES = REPO_ROOT / "benchmarks/ai-governance/validator-entry-profile-20261023/fixtures"
RUST_MODULE = REPO_ROOT / "crates/consensus_cobalt/src/validator_entry_profile.rs"
PY_MODULE = REPO_ROOT / "python/postfiat_rpc/validator_entry_profile.py"


def _cases() -> list[dict]:
    return json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))["cases"]


def _case(name: str) -> dict:
    return next(case for case in _cases() if case["name"] == name)


class ValidatorEntryProfileMirrorTest(unittest.TestCase):
    def test_mirror_reproduces_every_shared_fixture_byte_for_byte(self) -> None:
        cases = _cases()
        self.assertEqual(len(cases), 263)
        mismatches = []
        for case in cases:
            actual = vep.canonical_bytes(vep.run_case(case))
            expected = vep.canonical_bytes(case["expected"])
            if actual != expected or hashlib.sha256(actual).hexdigest() != case["expected_sha256"]:
                mismatches.append(case["name"])
        self.assertEqual(mismatches, [])

    def test_flagged_real_operator_is_eligible_after_four_clean_rounds(self) -> None:
        out = vep.run_case(_case("flagged_real_operator_eligible_after_four_clean_rounds"))
        self.assertEqual((out["profile"], out["seat"], out["clean_rounds"]), ("strict", "may_take_new_seat", 4))

    def test_flag_only_withholds_a_new_seat_and_never_removes_an_incumbent(self) -> None:
        self.assertEqual(vep.run_case(_case("flagged_entrant_withheld_before_the_strict_profile"))["seat"], "new_seat_withheld")
        self.assertEqual(vep.run_case(_case("flagged_incumbent_keeps_its_seat"))["seat"], "keeps_seat")

    def test_missing_or_invalid_flag_input_is_no_flag(self) -> None:
        for name in (
            "model_outage_no_artifact_resolves_to_no_flag",
            "resolve_pin_mismatch_gives_none",
            "resolve_wrong_schema_gives_none",
            "resolve_non_shadow_artifact_gives_none",
            "resolve_absent_operator_gives_none",
            "resolve_duplicate_operator_gives_none",
            "resolve_unknown_flag_value_gives_none",
        ):
            self.assertEqual(vep.run_case(_case(name)), {"flag": "none"}, name)
        out = vep.run_case(_case("no_flag_input_selects_the_standard_profile"))
        self.assertEqual((out["profile"], out["seat"]), ("standard", "may_take_new_seat"))

    def test_strict_profile_never_reads_the_flag(self) -> None:
        operator = _case("flagged_real_operator_eligible_after_four_clean_rounds")["operator"]
        parameters = _case("flagged_real_operator_eligible_after_four_clean_rounds")["parameters"]
        results = {vep.meets_strict_profile(parameters, {**operator, "flag": flag}) for flag in vep.FLAG_INPUTS}
        self.assertEqual(results, {True})

    def test_worked_example_and_round_28_counts(self) -> None:
        flags: Counter = Counter()
        seats: Counter = Counter()
        for case in _cases():
            out = vep.run_case(case)
            if case["group"] == "worked_example_20260903":
                flags[case["name"].split(":")[0]] += out["identity_flag"] == "flag"
            elif case["group"] == "round_28":
                seats[(case["name"].split(":")[0], out["seat"])] += 1
        self.assertEqual(flags["legitimacy_score_zero"], 13)
        self.assertEqual(flags["packet_not_established"], 0)
        self.assertEqual(seats[("entry_profile_v1", "keeps_seat")], 25)
        self.assertEqual(seats[("entry_profile_v1", "new_seat_withheld")], 36)
        self.assertEqual(seats[("interim_domain_only", "keeps_seat")], 25)
        self.assertEqual(seats[("interim_domain_only", "may_take_new_seat")], 24)
        self.assertEqual(seats[("interim_domain_only", "new_seat_withheld")], 12)

    def test_module_hashes_match_the_recorded_pins(self) -> None:
        pins = json.loads((FIXTURES / "modules.json").read_text(encoding="utf-8"))
        self.assertEqual(pins["schema"], vep.SCHEMA)
        self.assertEqual(pins["version"], vep.VERSION)
        self.assertEqual(hashlib.sha256(RUST_MODULE.read_bytes()).hexdigest(), pins["rust_module_sha256"])
        self.assertEqual(hashlib.sha256(PY_MODULE.read_bytes()).hexdigest(), pins["python_mirror_sha256"])


if __name__ == "__main__":
    unittest.main()
