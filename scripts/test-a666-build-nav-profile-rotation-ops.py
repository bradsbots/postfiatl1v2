#!/usr/bin/env python3
"""Regression tests for the immutable A666 public-profile rotation builder."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROGRAM = Path(__file__).with_name("a666-build-nav-profile-rotation-ops.py")
ISSUER = "pffcb93d9f87a843a8aa34e1adf241f5d58143e81b"
ASSET_ID = (
    "521c6c630bb48d4a37ab4a7bd4900dd2caa2d9e99499e452da3c7ce75b3d74b6"
    "2d20e18555642bec32174498cbee5e2c"
)
PROFILE_ID = (
    "bfb599f2bf7b9fa7541c1205df3e80dc8249f296dd930a8a932e7e1d15f37b5f"
    "c6030c2f9c4097dd458afc8690a4be92"
)


def derived_profile(*, allow_controlled_sources: bool = False) -> dict[str, object]:
    operation = {
        "registrant": ISSUER,
        "verifier_kind": "sp1-nav-reserve-v1",
        "source_class": "manifest-driven-a666-public-reserves-v1",
        "max_snapshot_age_blocks": 900,
        "challenge_window_blocks": 1,
        "max_epoch_gap_blocks": 128,
        "settle_deadline_blocks": 256,
        "min_challenge_bond": 0,
        "min_attestations": 0,
        "tolerance_bp": 0,
        "public_values_schema": "postfiat.nav_reserve_public_values.v1",
        "allow_controlled_sources": allow_controlled_sources,
        "source_manifest_hash": (
            "122a4327e049bfe3e4361e73efc9b11ea724fe6191fc2d2a0f25518ebc253a6"
            "3a5edfa27ebad25d13455c3d45179382d"
        ),
        "valuation_policy_hash": (
            "350eaee0a1ca12ba51637781ba52661b8685f868657a7c5e7d07c31b2899869c"
        ),
        "valuation_unit_id": (
            "c67872c31caa85cbe6dd287a1e060f0f5cfc0e9f3c5bd85a7569897fd0cefb03"
            "1583b7afc001e7d1afa492e9abf77d60"
        ),
        "sp1_program_vkey": (
            "0x00d28f47f2bd541eb5dba2336d735a6c8132eed9c4c07ce5d13339b3344339bf"
        ),
        "sp1_proof_encoding": "groth16",
        "max_proof_bytes": 4096,
        "max_public_values_bytes": 584,
        "max_observation_span_blocks": 8,
    }
    return {
        "schema": "postfiat.reserve_derived_profile.v1",
        "operation": operation,
        "profile": {
            **operation,
            "profile_id": PROFILE_ID,
            "registered_by": ISSUER,
        },
    }


class ProfileRotationBuilderTests(unittest.TestCase):
    def run_builder(
        self,
        profile: dict[str, object],
        *,
        create_key: bool = True,
        expected_profile_id: str = PROFILE_ID,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        profile_path = root / "derived-profile.json"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        key_path = root / "issuer-key.json"
        if create_key:
            key_path.write_text("fixture", encoding="utf-8")
        output = root / "output"
        result = subprocess.run(
            [
                sys.executable,
                str(PROGRAM),
                "--derived-profile",
                str(profile_path),
                "--expected-profile-id",
                expected_profile_id,
                "--issuer-key-file",
                str(key_path),
                "--output-dir",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        return result, output

    def test_builds_register_then_rebind_for_same_a666(self) -> None:
        result, output = self.run_builder(derived_profile())
        self.assertEqual(result.returncode, 0, result.stderr)
        register = json.loads((output / "01-nav-profile-register.ops.json").read_text())
        rebind = json.loads((output / "02-nav-asset-rebind.ops.json").read_text())
        register_operation = register["operations"][0]["operation"]
        rebind_operation = rebind["operations"][0]["operation"]
        self.assertEqual(register_operation["operation"], "nav_profile_register")
        self.assertFalse(register_operation["allow_controlled_sources"])
        self.assertEqual(rebind_operation["operation"], "nav_asset_register")
        self.assertEqual(rebind_operation["asset_id"], ASSET_ID)
        self.assertEqual(rebind_operation["proof_profile"], PROFILE_ID)

    def test_controlled_sources_are_rejected(self) -> None:
        result, _ = self.run_builder(derived_profile(allow_controlled_sources=True))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reject controlled reserve sources", result.stderr)

    def test_missing_issuer_key_is_rejected(self) -> None:
        result, _ = self.run_builder(derived_profile(), create_key=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issuer key file is unavailable", result.stderr)

    def test_unpinned_profile_id_is_rejected(self) -> None:
        result, _ = self.run_builder(
            derived_profile(), expected_profile_id="00" * 48
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixed public successor ID", result.stderr)

    def test_malformed_expected_profile_id_is_rejected(self) -> None:
        result, _ = self.run_builder(derived_profile(), expected_profile_id="not-a-profile")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected profile ID is malformed", result.stderr)

    def test_profile_and_registration_must_match(self) -> None:
        profile = derived_profile()
        profile["profile"]["valuation_policy_hash"] = "77" * 32
        result, _ = self.run_builder(profile)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valuation_policy_hash differs", result.stderr)

    def test_bridge_profile_fields_must_match_registration(self) -> None:
        profile = derived_profile()
        profile["operation"]["bridge_observer_min_confirmations"] = 12
        result, _ = self.run_builder(profile)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bridge_observer_min_confirmations differs", result.stderr)

    def test_profile_id_is_recomputed_from_canonical_preimage(self) -> None:
        profile = derived_profile()
        profile["operation"]["max_snapshot_age_blocks"] = 901
        profile["profile"]["max_snapshot_age_blocks"] = 901
        result, _ = self.run_builder(profile)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical registration preimage", result.stderr)


if __name__ == "__main__":
    unittest.main()
