"""Vote reliability window: the SCT-08 native reliability fact.

Reads the per-height vote records (``postfiat.block_vote_record.v1``) that the
proposer of each certified batch round keeps in
``<data-dir>/block-vote-records/height-<20-digit height>.json``. Each validator
holds only the heights it proposed, so a window combines the record
directories of all validators. Per validator the window gives the heights it
was asked for a vote, its accepted, refused (by reason class) and unanswered
votes, its answers after the quorum, and ``uptime_window_bps`` as the
2026-10-23 decision in docs/review/sct08-evidence-campaign-20261023.md defines
it: accepted votes divided by the finalized heights in the window, times
10,000, rounded down. The fact counts only when every height of the window has
a record that lists the validator; otherwise it is "not available".

The command only reads files; it never opens a socket or writes a record.

    PYTHONPATH=python python3 -m postfiat_rpc.vote_reliability \\
        --records DIR [--records DIR ...] --from-height H --to-height H [--table]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

RECORD_SCHEMA = "postfiat.block_vote_record.v1"
REPORT_SCHEMA = "postfiat.vote_reliability_window.v1"
RECORD_DIR = "block-vote-records"
NOT_AVAILABLE = "not available"
BPS = 10_000
MAX_RECORD_BYTES = 256 * 1024
MAX_RECORD_ENTRIES = 1024
MAX_REFUSAL_CLASS_CHARS = 64
MAX_WINDOW_HEIGHTS = 1_000_000
RECORD_FILE = re.compile(r"^height-(\d+)\.json$")
OUTCOMES = ("accepted", "refused", "no_answer")


class VoteRecordError(ValueError):
    """A record directory or record that cannot be read as a vote record."""


class VoteRecordConflict(VoteRecordError):
    """Two records for one height disagree (for example two proposers)."""

    def __init__(self, conflicts: list[dict[str, Any]]) -> None:
        heights = ", ".join(str(conflict["height"]) for conflict in conflicts)
        super().__init__(f"conflicting vote records for height(s) {heights}")
        self.conflicts = conflicts


def record_directories(path: str | Path) -> list[Path]:
    """The record directories under one ``--records`` argument.

    The argument may be a record directory (holding ``height-*.json``), a
    validator data directory (holding ``block-vote-records/``), or a parent
    folder whose subdirectories are either.
    """

    root = Path(path).expanduser()
    if not root.is_dir():
        raise VoteRecordError(f"records path `{root}` is not a directory")

    def direct(candidate: Path) -> Path | None:
        if (candidate / RECORD_DIR).is_dir():
            return candidate / RECORD_DIR
        if any(RECORD_FILE.match(entry.name) for entry in candidate.iterdir() if entry.is_file()):
            return candidate
        return None

    found = direct(root)
    if found is not None:
        return [found]
    nested = [d for d in (direct(child) for child in sorted(root.iterdir()) if child.is_dir()) if d is not None]
    if not nested:
        raise VoteRecordError(f"no vote record directory under `{root}`")
    return nested


def _validate_record(record: Any, height: int, path: Path) -> dict[str, Any]:
    def fail(reason: str) -> VoteRecordError:
        return VoteRecordError(f"`{path}`: {reason}")

    if not isinstance(record, dict) or record.get("schema") != RECORD_SCHEMA:
        raise fail(f"not a {RECORD_SCHEMA} record")
    if record.get("block_height") != height:
        raise fail("block_height does not match the file name")
    for field in ("chain_id", "block_hash", "proposer"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise fail(f"missing {field}")
    entries = record.get("entries")
    if not isinstance(entries, list) or not 0 < len(entries) <= MAX_RECORD_ENTRIES:
        raise fail("entry count is out of range")
    previous = None
    for entry in entries:
        if not isinstance(entry, dict):
            raise fail("entry is not an object")
        validator = entry.get("validator")
        outcome = entry.get("outcome")
        late = entry.get("answered_after_quorum")
        vote_id = entry.get("vote_id")
        refusal = entry.get("refusal_class")
        if not isinstance(validator, str) or not validator.strip():
            raise fail("entry without a validator")
        if previous is not None and not previous < validator:
            raise fail("entries must be sorted by unique validator id")
        previous = validator
        consistent = isinstance(late, bool) and (
            (outcome == "accepted" and isinstance(vote_id, str) and vote_id != "" and refusal is None)
            or (
                outcome == "refused"
                and vote_id is None
                and isinstance(refusal, str)
                and 0 < len(refusal) <= MAX_REFUSAL_CLASS_CHARS
            )
            or (outcome == "no_answer" and vote_id is None and refusal is None and late is False)
        )
        if not consistent:
            raise fail(f"entry for `{validator}` is inconsistent")
    if not any(entry["validator"] == record["proposer"] for entry in entries):
        raise fail("record omits the proposer")
    return record


def _read_records(directories: Iterable[Path], from_height: int, to_height: int) -> dict[int, list[tuple[Path, dict]]]:
    by_height: dict[int, list[tuple[Path, dict]]] = {}
    for directory in directories:
        for path in sorted(directory.iterdir()):
            match = RECORD_FILE.match(path.name)
            if not match or not path.is_file():
                continue
            height = int(match.group(1))
            if not from_height <= height <= to_height:
                continue
            if path.stat().st_size > MAX_RECORD_BYTES:
                raise VoteRecordError(f"`{path}`: record is larger than {MAX_RECORD_BYTES} bytes")
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise VoteRecordError(f"`{path}`: {error}") from error
            by_height.setdefault(height, []).append((path, _validate_record(record, height, path)))
    return by_height


def _ranges(heights: Sequence[int]) -> list[str]:
    """Heights as compact ranges: [3, 4, 5, 9] -> ["3-5", "9"]."""

    spans: list[str] = []
    start = previous = None
    for height in sorted(heights):
        if start is None:
            start = previous = height
        elif height == previous + 1:
            previous = height
        else:
            spans.append(str(start) if start == previous else f"{start}-{previous}")
            start = previous = height
    if start is not None:
        spans.append(str(start) if start == previous else f"{start}-{previous}")
    return spans


def derive_reliability(
    record_paths: Sequence[str | Path],
    from_height: int,
    to_height: int,
    validators: Sequence[str] | None = None,
) -> dict[str, Any]:
    """The reliability window report over ``from_height..=to_height``.

    Raises :class:`VoteRecordConflict` when two records for one height
    disagree, and :class:`VoteRecordError` for an unreadable or inconsistent
    record or an invalid window.
    """

    if from_height < 1 or from_height > to_height:
        raise VoteRecordError("the window needs 1 <= --from-height <= --to-height")
    window_heights = to_height - from_height + 1
    if window_heights > MAX_WINDOW_HEIGHTS:
        raise VoteRecordError(f"the window is limited to {MAX_WINDOW_HEIGHTS} heights")
    if not record_paths:
        raise VoteRecordError("give at least one --records directory")

    directories: list[Path] = []
    for path in record_paths:
        for directory in record_directories(path):
            if directory.resolve() not in {d.resolve() for d in directories}:
                directories.append(directory)

    by_height = _read_records(directories, from_height, to_height)
    conflicts = []
    records: dict[int, dict[str, Any]] = {}
    for height, copies in sorted(by_height.items()):
        distinct = {json.dumps(record, sort_keys=True) for _, record in copies}
        if len(distinct) > 1:
            conflicts.append(
                {
                    "height": height,
                    "records": [
                        {"path": str(path), "proposer": record["proposer"], "block_hash": record["block_hash"]}
                        for path, record in copies
                    ],
                }
            )
            continue
        records[height] = copies[0][1]
    if conflicts:
        raise VoteRecordConflict(conflicts)
    chain_ids = sorted({record["chain_id"] for record in records.values()})
    if len(chain_ids) > 1:
        raise VoteRecordError(f"records from more than one chain: {', '.join(chain_ids)}")

    missing_heights = [h for h in range(from_height, to_height + 1) if h not in records]
    names = set(validators or ())
    for record in records.values():
        names.update(entry["validator"] for entry in record["entries"])

    rows = []
    for name in sorted(names):
        counts = {outcome: 0 for outcome in OUTCOMES}
        refused_by_class: dict[str, int] = {}
        late = 0
        without_entry = []
        for height in range(from_height, to_height + 1):
            record = records.get(height)
            if record is None:
                continue
            entry = next((e for e in record["entries"] if e["validator"] == name), None)
            if entry is None:
                without_entry.append(height)
                continue
            counts[entry["outcome"]] += 1
            if entry["outcome"] == "refused":
                refused_by_class[entry["refusal_class"]] = refused_by_class.get(entry["refusal_class"], 0) + 1
            if entry["answered_after_quorum"]:
                late += 1
        available = not missing_heights and not without_entry
        rows.append(
            {
                "validator": name,
                "heights_requested": sum(counts.values()),
                "accepted": counts["accepted"],
                "refused": counts["refused"],
                "refused_by_class": dict(sorted(refused_by_class.items())),
                "no_answer": counts["no_answer"],
                "answered_after_quorum": late,
                "heights_without_entry": _ranges(without_entry),
                "uptime_window_bps": counts["accepted"] * BPS // window_heights if available else NOT_AVAILABLE,
            }
        )

    return {
        "schema": REPORT_SCHEMA,
        "from_height": from_height,
        "to_height": to_height,
        "window_heights": window_heights,
        "chain_id": chain_ids[0] if chain_ids else None,
        "record_directories": [str(directory) for directory in directories],
        "heights_with_record": len(records),
        "heights_without_record": _ranges(missing_heights),
        "status": "available" if not missing_heights else "not_available",
        "measure": "uptime_window_bps = accepted votes * 10000 // finalized heights in the window",
        "validators": rows,
    }


def render_table(report: dict[str, Any]) -> str:
    header = ("validator", "requested", "accepted", "refused", "no_answer", "late", "uptime_window_bps")
    lines = [
        f"heights {report['from_height']}-{report['to_height']} ({report['window_heights']}), "
        f"records for {report['heights_with_record']}, status {report['status']}",
    ]
    if report["heights_without_record"]:
        lines.append(f"heights without a record: {', '.join(report['heights_without_record'])}")
    rows = [
        (
            row["validator"],
            str(row["heights_requested"]),
            str(row["accepted"]),
            str(row["refused"]),
            str(row["no_answer"]),
            str(row["answered_after_quorum"]),
            str(row["uptime_window_bps"]),
        )
        for row in report["validators"]
    ]
    widths = [max(len(cells[i]) for cells in [header, *rows]) for i in range(len(header))]
    lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(header)).rstrip())
    lines.extend("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip() for cells in rows)
    for row in report["validators"]:
        if row["refused_by_class"]:
            classes = ", ".join(f"{name} {count}" for name, count in row["refused_by_class"].items())
            lines.append(f"{row['validator']} refused: {classes}")
        if row["heights_without_entry"]:
            lines.append(f"{row['validator']} not asked at: {', '.join(row['heights_without_entry'])}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m postfiat_rpc.vote_reliability",
        description="Derive uptime_window_bps per validator from the per-height vote records (read only).",
    )
    parser.add_argument(
        "--records",
        action="append",
        required=True,
        metavar="DIR",
        help="a record directory, a validator data directory, or a parent folder of them; repeat per validator",
    )
    parser.add_argument("--from-height", type=int, required=True)
    parser.add_argument("--to-height", type=int, required=True)
    parser.add_argument(
        "--validators",
        help="comma-separated validator ids that must appear; one without records is not available",
    )
    parser.add_argument("--table", action="store_true", help="print a table instead of JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validators = [name.strip() for name in args.validators.split(",") if name.strip()] if args.validators else None
    try:
        report = derive_reliability(args.records, args.from_height, args.to_height, validators)
    except VoteRecordConflict as error:
        print(
            json.dumps(
                {"schema": REPORT_SCHEMA, "status": "refused_conflicting_records", "conflicts": error.conflicts},
                indent=2,
                sort_keys=True,
            )
        )
        print(f"vote-reliability-refused: {error}", file=sys.stderr)
        return 1
    except (OSError, VoteRecordError) as error:
        print(f"vote-reliability-failed: {error}", file=sys.stderr)
        return 1
    if args.table:
        print(render_table(report), end="")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
