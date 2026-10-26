#!/usr/bin/env python3
"""Run one fixed-batch identity flag pass against the local pinned SGLang server (``SHADOW_ONLY``).

The flag variant of ``identity-packet-replay-20260903/run_host.py``. Its execution
profile is unchanged: the same loopback SGLang endpoint, requests posted one batch
of 32 at a time with the whole batch in flight, a 3600 s request timeout, and
sampling taken from the request bodies (temperature 0, top-p 1, thinking off,
2,048 tokens). The server-side switches are those of that package's
``bootstrap_host.sh``. What changed:

- it refuses to start unless ``prompt_v1.txt`` and ``response_schema_v1.json``
  have the package's pinned SHA-256;
- it reads the request rows ``admissibility.py --requests-out`` writes, and refuses
  rows that are not exactly the flag pipeline's requests for their embedded packets;
- it writes ``<owner>-run<index>.json``, whose ``results`` rows carry ``slot``,
  ``request_sha256``, ``content`` and ``finish_reason`` as ``admissibility.py --run``
  reads them. Truncated or invalid replies are kept with their real ``finish_reason``.

    python3 run_host.py --requests requests.json --owner ownerA \\
        --provider-host-id 445596 --run-index 1 [--out-dir outputs]

The real backend is the 2026-09-03 runner's HTTP client. It is loaded from that file
only when a real run starts, so the package imports without the GPU host.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import importlib.util
import json
import platform
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Protocol, Sequence

import identity_flag_pipeline as pl

# Package pins (spec Appendix A; README pin table).
PROMPT_SHA256 = "e5a62a6db15443cea8dbb8b1c048309f10d4e7e87c4050b946cfb9941d443f19"
RESPONSE_SCHEMA_SHA256 = "2e383bc3057b1ce7f9a66f351286640470645893c57be8e2a8addc6825b8a609"
RUN_SCHEMA = "postfiat.identity_flag.run.v1"
LEGACY_RUNNER = pl.HERE.parent / "identity-packet-replay-20260903/run_host.py"
LEGACY_MODULE = "identity_packet_replay_20260903_run_host"
REQUEST_TIMEOUT_SECONDS = 3600  # 2026-09-03 run_host.py:142
OWNER_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class Refused(SystemExit):
    """The runner will not start: a pin, a request row or an argument is wrong."""


class Backend(Protocol):
    def complete(self, body: bytes) -> dict[str, Any]:
        """POST one request body; return ``{"content", "finish_reason", "usage"}``."""

    def host_facts(self) -> dict[str, Any]:
        """``{"gpu", "python", "server"}`` for the run file's ``host`` record."""


class SGLangBackend:
    """The 2026-09-03 runner's backend: its loopback URL and server-info read, the same POST."""

    def __init__(self) -> None:
        spec = importlib.util.spec_from_file_location(LEGACY_MODULE, LEGACY_RUNNER)
        self.legacy = importlib.util.module_from_spec(spec)
        sys.modules[LEGACY_MODULE] = self.legacy
        spec.loader.exec_module(self.legacy)
        self.url = self.legacy.URL
        if urllib.parse.urlparse(self.url).hostname != "127.0.0.1":
            raise Refused(f"endpoint {self.url} is not loopback")

    def complete(self, body: bytes) -> dict[str, Any]:
        request = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            document = json.load(response)
        choice = document["choices"][0]
        return {"content": choice["message"]["content"] or "", "finish_reason": choice.get("finish_reason"),
                "usage": document.get("usage")}

    def host_facts(self) -> dict[str, Any]:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,uuid", "--format=csv,noheader"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        return {"gpu": gpu, "python": platform.python_version(), "server": self.legacy.server_info()}


def verify_pins() -> None:
    if pl.file_sha256(pl.PROMPT_PATH) != PROMPT_SHA256:
        raise Refused("prompt_v1.txt SHA-256 does not match the package pin")
    if pl.response_schema_sha256() != RESPONSE_SCHEMA_SHA256:
        raise Refused("response_schema_v1.json SHA-256 does not match the package pin")


def verify_requests(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the embedded packets; refuse rows that are not the flag pipeline's requests for them."""
    if not rows or [row.get("slot") for row in rows] != list(range(len(rows))) or len(rows) % pl.BATCH_SIZE:
        raise Refused(f"request rows must be slots 0..n-1 in whole batches of {pl.BATCH_SIZE}")
    prompt = pl.PROMPT_PATH.read_text(encoding="utf-8")
    schema = pl.response_schema()
    packets = []
    try:
        for row in rows:
            if pl.sha256(pl.canonical(row["body"])) != row["request_sha256"]:
                raise Refused(f"slot {row['slot']}: request hash mismatch")
            if row["padding"]:
                continue
            system, user = row["body"]["messages"]
            if system["content"] != prompt:
                raise Refused(f"slot {row['slot']}: system prompt is not prompt_v1.txt")
            if row["body"]["response_format"]["json_schema"]["schema"] != schema:
                raise Refused(f"slot {row['slot']}: response schema is not response_schema_v1.json")
            text = user["content"]
            start = text.index(pl.BEGIN_MARK) + len(pl.BEGIN_MARK)
            packets.append({"validator_id": row["validator_id"], "network": row["network"],
                            "packet_sha256": row["packet_sha256"], "packet_text": text[start:text.rindex(pl.END_MARK)]})
        expected = pl.build_requests(packets)
    except (KeyError, TypeError, ValueError) as error:
        raise Refused(f"malformed request rows: {error}") from error
    if expected != list(rows):
        raise Refused("request rows are not the flag pipeline's requests for their packets")
    return packets


def run(
    rows: Sequence[dict[str, Any]],
    *,
    owner: str,
    run_index: int,
    provider_host_id: str,
    out_dir: Path,
    backend: Backend | None = None,
) -> Path:
    """Verify everything, then post every request and write ``<owner>-run<index>.json``."""
    if not OWNER_LABEL.fullmatch(owner):
        raise Refused(f"owner label {owner!r} must match {OWNER_LABEL.pattern}")
    if not 1 <= run_index <= pl.RUNS_PER_OWNER:
        raise Refused(f"run index must be 1..{pl.RUNS_PER_OWNER}")
    run_name = f"{owner}-run{run_index}"
    path = Path(out_dir) / f"{run_name}.json"
    if path.exists():
        raise Refused(f"{path} exists; a run file is never overwritten")
    verify_pins()
    packets = verify_requests(rows)
    backend = backend or SGLangBackend()

    def one(row: dict[str, Any]) -> dict[str, Any]:
        reply = backend.complete(pl.canonical(row["body"]).encode())
        content, finish_reason = reply["content"], reply["finish_reason"]
        return {
            "slot": row["slot"],
            "validator_id": row["validator_id"],
            "network": row["network"],
            "packet_sha256": row["packet_sha256"],
            "padding": row["padding"],
            "request_sha256": row["request_sha256"],
            "content": content,
            "content_sha256": pl.sha256(content) if isinstance(content, str) else None,
            "finish_reason": finish_reason,
            "slot_check": pl.check_response(row, content, finish_reason)[0],
            "usage": reply.get("usage"),
        }

    results: list[dict[str, Any]] = []
    started = time.time()
    for start in range(0, len(rows), pl.BATCH_SIZE):
        batch = rows[start:start + pl.BATCH_SIZE]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as executor:
            results.extend(executor.map(one, batch))
        print(f"batch {start // pl.BATCH_SIZE} done at {time.time() - started:.1f}s", flush=True)
    results.sort(key=lambda row: row["slot"])
    record = {
        "schema": RUN_SCHEMA,
        "run_name": run_name,
        "host": {"owner": owner, "provider_host_id": provider_host_id, "run_index": run_index,
                 **backend.host_facts()},
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "wall_seconds": round(time.time() - started, 1),
        "profile_sha256": pl.profile_sha256(),
        "prompt_sha256": PROMPT_SHA256,
        "response_schema_sha256": RESPONSE_SCHEMA_SHA256,
        "requests_sha256": pl.requests_sha256(rows),
        "packet_set_sha256": pl.packet_set_sha256(packets),
        "slot_checks": dict(sorted(collections.Counter(r["slot_check"] for r in results).items())),
        "aggregate_sha256": pl.sha256("".join(r["content_sha256"] or "" for r in results)),
        "results": results,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pl.canonical(record) + "\n")
    print(run_name, record["aggregate_sha256"], record["wall_seconds"], json.dumps(record["slot_checks"]))
    return path


def main(argv: list[str] | None = None, backend: Backend | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requests", type=Path, required=True, help="rows from admissibility.py --requests-out")
    parser.add_argument("--owner", required=True, help="the host owner's label, as later given to --run OWNER=PATH")
    parser.add_argument("--provider-host-id", required=True, help="the provider's host ID (spec §5: distinct per owner)")
    parser.add_argument("--run-index", type=int, required=True, choices=range(1, pl.RUNS_PER_OWNER + 1))
    parser.add_argument("--out-dir", type=Path, default=pl.HERE / "outputs")
    args = parser.parse_args(argv)
    run(json.loads(args.requests.read_text()), owner=args.owner, run_index=args.run_index,
        provider_host_id=args.provider_host_id, out_dir=args.out_dir, backend=backend)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
