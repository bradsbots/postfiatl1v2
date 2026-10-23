#!/usr/bin/env python3
"""Write one round's ``flags.json`` and ``admissibility.json`` (``SHADOW_ONLY``).

Offline: reads a round file (the ``fixtures/round_28_candidates.json`` shape),
the frozen packet corpus, the round manifest's flag section and four run files
(two owners, two runs each). It never calls a model.

    python3 admissibility.py --round fixtures/round_28_candidates.json \\
        --section section.json --run ownerA=a1.json --run ownerA=a2.json \\
        --run ownerB=b1.json --run ownerB=b2.json --out out/

``--requests-out requests.json`` writes the request rows for the host runner
instead (no runs needed).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import identity_flag_pipeline as pipeline

DEFAULT_CORPUS = pipeline.HERE.parent / "validator-identity-packets-20260901"


def load_round(path: Path, corpus: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(path.read_text())
    candidates = [{"validator_id": c["validator_id"], "domain_verified": c["domain_verified"]}
                  for c in data["candidates"]]
    packets = []
    for row in data["candidates"]:
        if row.get("packet_path"):
            packets.append({
                "validator_id": row["validator_id"],
                "network": row["network"],
                "packet_sha256": row["packet_sha256"],
                "packet_text": (corpus / row["packet_path"]).read_text(encoding="utf-8"),
            })
    return data["round"], candidates, packets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--round", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--section", type=Path, help="the round manifest's flag section (JSON)")
    parser.add_argument("--run", action="append", default=[], metavar="OWNER=PATH")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--requests-out", type=Path)
    args = parser.parse_args(argv)
    round_info, candidates, packets = load_round(args.round, args.corpus)
    if args.requests_out:
        args.requests_out.write_text(json.dumps(pipeline.build_requests(packets), indent=1, sort_keys=True) + "\n")
        return 0
    if not args.section or not args.out:
        parser.error("--section and --out are required unless --requests-out is given")
    runs = []
    for spec in args.run:
        owner, _, path = spec.partition("=")
        runs.append({"owner": owner, **json.loads(Path(path).read_text())})
    flags, admissibility = pipeline.build_flags(
        round_info=round_info,
        candidates=candidates,
        packets=packets,
        runs=runs,
        expected_section=json.loads(args.section.read_text()),
    )
    pipeline.write_artifacts(args.out, flags, admissibility)
    summary = flags["admissibility_summary"]
    flagged = sum(op["identity_flag"] == "flag" for op in flags["operators"])
    print(json.dumps({"flags": flagged, "replay_unreliable": flags["replay_unreliable"], **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
