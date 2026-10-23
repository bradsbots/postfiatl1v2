#!/usr/bin/env python3
"""Build the offline fixtures of the identity flag skeleton from committed data.

Sources (all in this repository, no network):

- ``validator-identity-packets-20260901/index.json``: the 55 frozen packets;
- ``identity-packet-replay-20260903/outputs/primary-run1.json``: the
  legitimacy scores of 2026-09-03 (stand-in 1 of spec §4.1);
- ``validator-entry-profile-20261023/fixtures/cases.json``: round 28's 61
  operators with ``domain_verified`` and ``incumbent``;
- ``dunl-subscorer-shadow-20260901/rounds-manifest.json``: round 28's pinned files.

Usage: ``python3 build_fixtures.py`` (writes) or ``--check`` (exit 1 on drift).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AI = HERE.parent
CORPUS = AI / "validator-identity-packets-20260901"
FIXTURES = HERE / "fixtures"


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _packets() -> dict[str, dict]:
    return {row["validator_id"]: row for row in json.loads((CORPUS / "index.json").read_text())}


def worked_example() -> dict:
    packets = _packets()
    run = json.loads((AI / "identity-packet-replay-20260903/outputs/primary-run1.json").read_text())
    scores = {r["validator_id"]: r["parsed"]["score"] for r in run["results"] if not r["padding"]}
    rows = []
    for vid in sorted(packets):
        row = packets[vid]
        rows.append({
            "validator_id": vid,
            "network": row["network"],
            "packet_path": row["packet_path"],
            "packet_sha256": row["packet_sha256"],
            "legitimacy_score": scores[vid],
            "not_established": row["canonical_entity"] is None,
            # Spec §11 point 3 (decided 2026-10-23): absent evidence counts as not verified.
            "domain_verified": row["domain_verification_status"] is True,
        })
    return {
        "schema": "postfiat.identity_flag.fixture.worked_example.v1",
        "source": {
            "index_sha256": hashlib.sha256((CORPUS / "index.json").read_bytes()).hexdigest(),
            "primary_run1_aggregate_sha256": run["aggregate_sha256"],
        },
        "expected_flags": {"legitimacy_score_zero": 13, "packet_not_established": 0},
        "validators": rows,
    }


def round_28() -> dict:
    cases = json.loads((AI / "validator-entry-profile-20261023/fixtures/cases.json").read_text())
    operators = {c["operator"]["validator_id"]: c["operator"] for c in cases["cases"] if c["group"] == "round_28"}
    packets = _packets()
    manifest = json.loads((AI / "dunl-subscorer-shadow-20260901/rounds-manifest.json").read_text())
    rows = []
    for vid in sorted(operators):
        packet = packets.get(vid)
        rows.append({
            "validator_id": vid,
            "incumbent": operators[vid]["incumbent"],
            "domain_verified": operators[vid]["domain_verified"],
            "network": packet["network"] if packet else None,
            "packet_path": packet["packet_path"] if packet else None,
            "packet_sha256": packet["packet_sha256"] if packet else None,
        })
    return {
        "schema": "postfiat.identity_flag.fixture.round.v1",
        "round": {
            "network": "testnet",
            "round_number": 28,
            # SHA-256 of the canonical JSON of round 28's nine pinned files.
            "input_package_hash": hashlib.sha256(canonical(manifest["rounds"]["28"]).encode()).hexdigest(),
        },
        "candidates": rows,
    }


def build() -> dict[str, str]:
    return {
        "worked_example_20260903.json": json.dumps(worked_example(), indent=1, sort_keys=True) + "\n",
        "round_28_candidates.json": json.dumps(round_28(), indent=1, sort_keys=True) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    drift = False
    for name, text in build().items():
        path = FIXTURES / name
        if args.check:
            if not path.exists() or path.read_text() != text:
                print(f"drift: {name}", file=sys.stderr)
                drift = True
        else:
            FIXTURES.mkdir(exist_ok=True)
            path.write_text(text)
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
