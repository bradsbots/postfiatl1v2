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

Each run file's ``host`` record must name the ``--run`` owner and a run index of 1
or 2, distinct within the owner. One owner's two runs must share a provider host ID,
and the two owners' IDs must differ (spec §5). Any problem voids every run, so the round is an outage with zero flags.
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


def run_file_problems(runs: list[dict[str, Any]]) -> list[str]:
    """Spec §5: two distinct-owner hosts, two runs each, as the run files' ``host`` records state."""
    problems = []
    indexes: dict[str, list[Any]] = {}
    hosts: dict[str, set[str]] = {}
    for run in runs:
        name, host = run["path"], run.get("host")
        if not isinstance(host, dict):
            problems.append(f"{name}: no host record")
            continue
        if host.get("owner") != run["owner"]:
            problems.append(f"{name}: host.owner {host.get('owner')!r} is not the --run owner {run['owner']!r}")
        index = host.get("run_index")
        if type(index) is not int or not 1 <= index <= pipeline.RUNS_PER_OWNER:
            problems.append(f"{name}: run index {index!r} is not 1..{pipeline.RUNS_PER_OWNER}")
        elif index in indexes.setdefault(run["owner"], []):
            problems.append(f"{name}: run index {index} repeats for owner {run['owner']!r}")
        indexes.setdefault(run["owner"], []).append(index)
        host_id = host.get("provider_host_id")
        if not isinstance(host_id, str) or not host_id:
            problems.append(f"{name}: no provider host ID")
        else:
            hosts.setdefault(run["owner"], set()).add(host_id)
    owners = sorted(hosts)
    for owner in owners:
        if len(hosts[owner]) > 1:
            problems.append(f"owner {owner!r} ran on more than one provider host: {sorted(hosts[owner])}")
    for i, first in enumerate(owners):
        for second in owners[i + 1:]:
            for host_id in sorted(hosts[first] & hosts[second]):
                problems.append(f"owners {first!r} and {second!r} share provider host {host_id!r}")
    return problems


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
        runs.append({**json.loads(Path(path).read_text()), "owner": owner, "path": path})
    problems = run_file_problems(runs)
    flags, admissibility = pipeline.build_flags(
        round_info=round_info,
        candidates=candidates,
        packets=packets,
        runs=[] if problems else runs,
        expected_section=json.loads(args.section.read_text()),
    )
    pipeline.write_artifacts(args.out, flags, admissibility)
    summary = flags["admissibility_summary"]
    flagged = sum(op["identity_flag"] == "flag" for op in flags["operators"])
    print(json.dumps({"flags": flagged, "replay_unreliable": flags["replay_unreliable"],
                      "run_file_problems": problems, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
