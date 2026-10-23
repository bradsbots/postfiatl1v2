#!/usr/bin/env python3
"""Assemble and self-verify a redaction-safe storage-scaling evidence packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

REPO = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO / "python"
SPEC = REPO / "docs" / "architecture" / "storage-scaling-fix-spec.md"
ARTIFACT_SCHEMAS = {
    "source": "postfiat-storage-source-identity-v1",
    "replay": "postfiat-storage-scaling-replay-v1",
    "performance": "postfiat-storage-scaling-time-budgeted-six-validator-campaign-v4",
    "tamper": "postfiat-storage-scaling-tamper-matrix-v1",
    "migration": "postfiat-storage-scaling-six-clone-migration-v1",
    "redaction": "postfiat-storage-scaling-redaction-v1",
}
PREPARED_INPUT_MANIFEST_SCHEMA = "postfiat-storage-prepared-input-manifest-v1"
SENSITIVE = re.compile(
    r"private[-_ ]?key(?![A-Za-z0-9_])|secret|password|mnemonic|spending[-_ ]?key|"
    r"full[-_ ]?viewing[-_ ]?key|master[-_ ]?seed|rseed|ssh[-_ ]?cred",
    re.IGNORECASE,
)
REDACTION_MAX_SCANNED_BYTES = 16 * 1024 * 1024
LOCAL_PATH = re.compile(r"(?:/home/|/Users/|[A-Za-z]:\\\\Users\\\\)")
NONLOCAL_IPV4 = re.compile(
    r"(?<![0-9.])(?!127\.0\.0\.1\b)(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9.])"
)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reference(packet: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(packet).as_posix(),
        "sha256": sha256(path),
    }


def resolve_report_reference(report_path: Path, value: Any) -> Path:
    if not isinstance(value, dict):
        raise ValueError(f"report reference must be an object in {report_path}")
    raw = value.get("path")
    expected = value.get("sha256")
    if not isinstance(raw, str) or not isinstance(expected, str):
        raise ValueError(f"report reference is incomplete in {report_path}")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"report reference is unsafe in {report_path}: {raw}")
    source = report_path.parent.joinpath(*pure.parts).resolve()
    if sha256(source) != expected:
        raise ValueError(f"report reference digest mismatch: {source}")
    return source


def copy_file(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"source is not a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError(f"refusing to overwrite packet entry: {destination}")
    shutil.copyfile(source, destination)


def copy_run_report(source: Path, destination: Path) -> None:
    """Copy a campaign run report, replacing its host-local topology path.

    The runner records `config.topology_file` as an absolute path. Nothing
    verifies that path; the topology itself is bound by `topology_sha256`.
    """
    report = read_json(source)
    config = report.get("config")
    if not isinstance(config, dict) or not isinstance(config.get("topology_file"), str):
        copy_file(source, destination)
        return
    config["topology_file"] = "$TOPOLOGY_FILE"
    if destination.exists():
        raise ValueError(f"refusing to overwrite packet entry: {destination}")
    write_json(destination, report)


def resolve_campaign_file(
    campaign_root: Path,
    raw: Any,
    expected_sha256: Any,
    label: str,
) -> Path:
    if not isinstance(raw, str) or not isinstance(expected_sha256, str):
        raise ValueError(f"{label} omitted its bound file")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError(f"{label} path is unsafe")
    candidate = campaign_root.joinpath(*relative.parts)
    if candidate.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    source = candidate.resolve()
    if not source.is_relative_to(campaign_root):
        raise ValueError(f"{label} escaped campaign root")
    if not source.is_file():
        raise ValueError(f"{label} is not a regular file")
    if sha256(source) != expected_sha256:
        raise ValueError(f"{label} digest mismatch")
    return source


def copy_replay(packet: Path, source: Path) -> Path:
    report = read_json(source)
    if report.get("schema") != ARTIFACT_SCHEMAS["replay"]:
        raise ValueError("replay report schema mismatch")
    rewritten = []
    receipts = report.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("replay report omitted receipts")
    for value in receipts:
        receipt_source = resolve_report_reference(source, value)
        receipt = read_json(receipt_source)
        height = receipt.get("source_height")
        destination = packet / "replay" / f"height-{height}.json"
        copy_file(receipt_source, destination)
        rewritten.append(reference(packet, destination))
    report["receipts"] = rewritten
    destination = packet / "artifacts" / "replay.json"
    write_json(destination, report)
    return destination


LEGACY_REPLAY_REPORT_SCHEMA = "postfiat-storage-legacy-replay-v1"
SIGNED_ARCHIVE_RECEIPT_SCHEMA = "postfiat-storage-signed-archive-replay-receipt-v1"
REPLAY_FLAGS = (
    "exact_replay",
    "full_replay_passed",
    "logical_rebuild_identical",
    "canonical_export_identical",
)


def copy_verify_only(
    packet: Path,
    legacy_report_path: Path,
    legacy: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Copy the height-924 `--verify-only` output byte for byte and bind its sentinels."""
    sentinel = legacy.get("independent_verify_only")
    if not isinstance(sentinel, dict):
        raise ValueError("legacy height-924 report omitted its independent verify-only run")
    source = resolve_report_reference(legacy_report_path, sentinel.get("output"))
    output = read_json(source)
    tip = output.get("source_tip")
    if (
        output.get("schema") != "postfiat-storage-migration-report-v1"
        or output.get("verify_only") is not True
        or output.get("published") is not False
        or not isinstance(tip, dict)
        or tip.get("height") != 924
    ):
        raise ValueError("independent verify-only output is not a PASS")
    trees: dict[str, str] = {}
    for prefix in ("clone", "target"):
        before = sentinel.get(f"{prefix}_tree_sha256_before")
        if (
            not isinstance(before, str)
            or re.fullmatch(r"[0-9a-f]{64}", before) is None
            or sentinel.get(f"{prefix}_tree_sha256_after") != before
        ):
            raise ValueError("independent verify-only changed the clone or target tree")
        trees[f"{prefix}_tree_sha256_before"] = before
        trees[f"{prefix}_tree_sha256_after"] = before
    if (
        tip.get("block_hash") != receipt.get("tip_hash")
        or tip.get("state_root") != receipt.get("state_root")
        or output.get("migration_packet_root") != receipt.get("migration_packet_root")
        or output.get("logical_store_report") != receipt.get("logical_store_report")
        or output.get("canonical_export_receipt") != receipt.get("canonical_export_receipt")
    ):
        raise ValueError(
            "independent verify-only output disagrees with the height-924 receipt"
        )
    destination = packet / "replay" / "height-924-verify-only.json"
    copy_file(source, destination)
    return {"output": reference(packet, destination), **trees}


def copy_replacement_replay(
    packet: Path,
    legacy_report_path: Path,
    archive_receipt_path: Path,
    binary_digest: str,
) -> Path:
    """Bind the approved 1123 signed archive in place of the lost 915 archive.

    The 924 receipt comes from the legacy-source report; the signed-archive
    receipt and its step outputs are copied byte-for-byte in the harness layout.
    """
    sys.path.insert(0, str(PYTHON_ROOT))
    from postfiat_rpc.storage_scaling import QUARANTINE_REPLACEMENT

    legacy = read_json(legacy_report_path)
    archive = read_json(archive_receipt_path)
    if (
        legacy.get("schema") != LEGACY_REPLAY_REPORT_SCHEMA
        or legacy.get("verdict") != "PASS"
        or legacy.get("source_height") != 924
    ):
        raise ValueError("legacy height-924 replay report is not a PASS")
    if (
        archive.get("schema") != SIGNED_ARCHIVE_RECEIPT_SCHEMA
        or archive.get("verdict") != "PASS"
    ):
        raise ValueError("replacement archive receipt is not a signed-archive PASS")
    height = QUARANTINE_REPLACEMENT["replacement_height"]
    if (
        archive.get("source_height") != height
        or archive.get("signed_manifest_sha256")
        != QUARANTINE_REPLACEMENT["signed_manifest_sha256"]
    ):
        raise ValueError("replacement archive is not the approved height-915 replacement")
    for label, value in (("legacy height-924 replay", legacy), ("replacement archive", archive)):
        if value.get("node_binary_sha256") != binary_digest:
            raise ValueError(f"{label} binary differs from the packet binary")

    receipts = legacy.get("receipts")
    if not isinstance(receipts, list) or len(receipts) != 1:
        raise ValueError("legacy height-924 replay report must bind one receipt")
    receipt_source = resolve_report_reference(legacy_report_path, receipts[0])
    receipt = read_json(receipt_source)
    if receipt.get("source_height") != 924 or any(
        receipt.get(flag) is not True for flag in REPLAY_FLAGS
    ):
        raise ValueError("height-924 replay receipt is not an exact replay")
    receipt_destination = packet / "replay" / "height-924.json"
    copy_file(receipt_source, receipt_destination)
    verify_only = copy_verify_only(packet, legacy_report_path, legacy, receipt)

    base = packet / "replay" / f"signed-archive-{height}"
    archive_destination = base / "receipts" / archive_receipt_path.name
    steps = archive.get("steps")
    if not isinstance(steps, dict) or not steps:
        raise ValueError("replacement archive receipt omitted its steps")
    step_sources = [
        (resolve_report_reference(archive_receipt_path.parent, step), step)
        for step in steps.values()
    ]
    copy_file(archive_receipt_path, archive_destination)
    for source, step in step_sources:
        copy_file(source, base.joinpath(*PurePosixPath(step["path"]).parts))

    report = {
        "schema": ARTIFACT_SCHEMAS["replay"],
        "authenticated_history_height": 924,
        "exact_pre_activation_replay": True,
        "full_replay_passed": True,
        "logical_rebuild_identical": True,
        "canonical_export_identical": True,
        "tip_hash": legacy.get("tip_hash"),
        "state_root": legacy.get("state_root"),
        "ordered_history_accumulator": legacy.get("ordered_history_accumulator"),
        "receipts": [reference(packet, receipt_destination)],
        "independent_verify_only": verify_only,
        "quarantine_archive_replacement": {
            **QUARANTINE_REPLACEMENT,
            "receipt": reference(packet, archive_destination),
        },
        "source_revision": legacy.get("source_revision"),
        "node_binary_sha256": legacy.get("node_binary_sha256"),
        "node_binary_build": legacy.get("node_binary_build"),
    }
    destination = packet / "artifacts" / "replay.json"
    write_json(destination, report)
    return destination


def copy_prepared_input(
    packet: Path,
    campaign_root: Path,
    report: dict[str, Any],
) -> None:
    manifest_source = resolve_campaign_file(
        campaign_root,
        report.get("prepared_input_manifest"),
        report.get("prepared_input_manifest_sha256"),
        "performance prepared-input manifest",
    )
    manifest = read_json(manifest_source)
    expected_build = {
        "candidate": manifest.get("candidate"),
        "batch_builder": manifest.get("batch_builder"),
        "runner": manifest.get("runner"),
        "build": manifest.get("build"),
    }
    if manifest.get("prepared_by") is not None:
        expected_build["prepared_by"] = manifest.get("prepared_by")
    if (
        manifest.get("schema") != PREPARED_INPUT_MANIFEST_SCHEMA
        or report.get("prepared_input_build") != expected_build
    ):
        raise ValueError("performance prepared-input build binding is invalid")
    manifest_destination = packet / "performance" / "prepared-input" / "manifest.json"
    copy_file(manifest_source, manifest_destination)
    report["prepared_input_manifest"] = manifest_destination.relative_to(
        packet
    ).as_posix()
    report["prepared_input_manifest_sha256"] = sha256(manifest_destination)

    imported = report.get("prepared_input_import")
    manifest_advances = manifest.get("advances")
    imported_advances = imported.get("advances") if isinstance(imported, dict) else None
    if (
        not isinstance(manifest_advances, list)
        or not manifest_advances
        or not isinstance(imported_advances, list)
        or len(imported_advances) != len(manifest_advances)
    ):
        raise ValueError("performance prepared-input advance artifacts are incomplete")
    for index, (advance, imported_advance) in enumerate(
        zip(manifest_advances, imported_advances),
        start=1,
    ):
        if not isinstance(advance, dict) or not isinstance(imported_advance, dict):
            raise ValueError("performance prepared-input advance is malformed")
        if imported_advance.get("unit_id") != advance.get("unit_id"):
            raise ValueError("performance prepared-input advance identity differs")
        for field in ("receipt", "report"):
            manifest_reference = advance.get(field)
            if not isinstance(manifest_reference, dict):
                raise ValueError(
                    f"performance prepared-input advance {field} is unbound"
                )
            source = resolve_campaign_file(
                campaign_root,
                imported_advance.get(field),
                imported_advance.get(f"{field}_sha256"),
                f"performance prepared-input advance {index} {field}",
            )
            if sha256(source) != manifest_reference.get("sha256"):
                raise ValueError(
                    f"performance prepared-input advance {index} {field} differs"
                )
            destination = (
                packet
                / "performance"
                / "prepared-input"
                / "advances"
                / f"advance-{index:04}-{field}.json"
            )
            if field == "receipt":
                receipt = read_json(source)
                if not isinstance(receipt.get("signed_transfer_corpus"), str):
                    raise ValueError(
                        f"performance prepared-input advance {index} receipt "
                        "omitted its corpus path"
                    )
                receipt["signed_transfer_corpus"] = "$SIGNED_TRANSFER_CORPUS"
                write_json(destination, receipt)
            else:
                copy_run_report(source, destination)
            imported_advance[f"source_{field}_sha256"] = manifest_reference[
                "sha256"
            ]
            imported_advance[field] = destination.relative_to(packet).as_posix()
            imported_advance[f"{field}_sha256"] = sha256(destination)


def copy_performance(packet: Path, source: Path) -> Path:
    report = read_json(source)
    if (
        report.get("schema") != ARTIFACT_SCHEMAS["performance"]
        or report.get("status") != "PASS"
        or report.get("campaign_mode") != "release-qualification"
        or report.get("evidence_eligible") is not True
    ):
        raise ValueError("performance report is not an evidence-eligible PASS")
    campaign_root = source.parent.resolve()
    input_mode = report.get("input_mode")
    if input_mode == "prepared-input-manifest":
        copy_prepared_input(packet, campaign_root, report)
    elif input_mode is not None:
        raise ValueError("performance report input mode is unsupported")
    materials = report.get("materials_by_height")
    required_heights = [50, 5000]
    if (
        not isinstance(materials, list)
        or [entry.get("height") if isinstance(entry, dict) else None for entry in materials]
        != required_heights
    ):
        raise ValueError("performance report omitted the closed height-material set")
    corpora_by_height: dict[int, tuple[str, str]] = {}
    for entry in materials:
        if not isinstance(entry, dict):
            raise ValueError("performance height-material entry is malformed")
        height = int(entry["height"])
        if re.fullmatch(
            r"[0-9a-f]{64}",
            str(entry.get("prepared_fleet_sha256", "")),
        ) is None:
            raise ValueError(
                f"performance height-{height} prepared fleet digest is invalid"
            )
        if height == 50:
            if (
                not isinstance(entry.get("snapshot"), str)
                or re.fullmatch(
                    r"[0-9a-f]{64}", str(entry.get("snapshot_sha256", ""))
                )
                is None
                or entry.get("corpus_source_mode")
                != "authenticated-portable-snapshot-import"
                or entry.get("corpus_source_prepared_fleet_sha256") is not None
                or any(
                    entry.get(field) is not None
                    for field in (
                        "corpus_scratch_before_sha256",
                        "corpus_scratch_after_sha256",
                        "corpus_scratch_mutated",
                        "corpus_scratch_discarded",
                        "corpus_scratch_restored_sha256",
                    )
                )
            ):
                raise ValueError("performance height-50 snapshot binding is invalid")
        elif (
            entry.get("snapshot") is not None
            or entry.get("snapshot_sha256") is not None
            or entry.get("corpus_source_mode")
            != "disposable-canonical-prepared-fleet-clone"
            or entry.get("corpus_source_prepared_fleet_sha256")
            != entry.get("prepared_fleet_sha256")
            or re.fullmatch(
                r"[0-9a-f]{64}",
                str(entry.get("corpus_scratch_before_sha256", "")),
            )
            is None
            or re.fullmatch(
                r"[0-9a-f]{64}",
                str(entry.get("corpus_scratch_after_sha256", "")),
            )
            is None
            or entry.get("corpus_scratch_before_sha256")
            != entry.get("prepared_fleet_sha256")
            or entry.get("corpus_scratch_restored_sha256")
            != entry.get("prepared_fleet_sha256")
            or entry.get("corpus_scratch_mutated")
            is not (
                entry.get("corpus_scratch_before_sha256")
                != entry.get("corpus_scratch_after_sha256")
            )
            or entry.get("corpus_scratch_discarded") is not True
        ):
            raise ValueError(
                f"performance height-{height} prepared corpus binding is invalid"
            )
        entry.pop("prepared_fleet", None)
        corpus_source = resolve_campaign_file(
            campaign_root,
            entry.get("signed_transfer_corpus"),
            entry.get("signed_transfer_corpus_sha256"),
            f"performance height-{height} signed transfer corpus",
        )
        corpus_destination = packet / "performance" / "corpora" / f"height-{height}.json"
        copy_file(corpus_source, corpus_destination)
        corpus_path = corpus_destination.relative_to(packet).as_posix()
        corpus_digest = sha256(corpus_destination)
        entry["signed_transfer_corpus"] = corpus_path
        entry["signed_transfer_corpus_sha256"] = corpus_digest
        corpora_by_height[height] = (corpus_path, corpus_digest)

    lanes = report.get("lanes")
    required_lane_heights = {
        "selected-indexed": [50, 5000],
        "legacy-jsonl": [50],
    }
    if not isinstance(lanes, dict) or set(lanes) != set(required_lane_heights):
        raise ValueError("performance report omitted the time-budgeted lane set")
    for lane_name in ("selected-indexed", "legacy-jsonl"):
        lane = lanes[lane_name]
        if not isinstance(lane, dict) or not isinstance(lane.get("rows"), list):
            raise ValueError(f"performance lane {lane_name} omitted rows")
        if [
            row.get("height") if isinstance(row, dict) else None
            for row in lane["rows"]
        ] != required_lane_heights[lane_name]:
            raise ValueError("performance lane heights differ from the profile")
        for row in lane["rows"]:
            if not isinstance(row, dict) or not isinstance(row.get("windows"), list):
                raise ValueError("performance row is malformed")
            height = row.get("height")
            for window_index, window in enumerate(row["windows"], start=1):
                if not isinstance(window, dict):
                    raise ValueError("performance window is malformed")
                label = f"height-{height}-window-{window_index}"
                if window.get("label") != label:
                    raise ValueError("performance window label is not canonical")
                expected_corpus = corpora_by_height[int(height)]
                if window.get("signed_transfer_corpus_sha256") != expected_corpus[1]:
                    raise ValueError(
                        "performance window used a different signed transfer corpus"
                    )
                window["signed_transfer_corpus"] = expected_corpus[0]
                window["signed_transfer_corpus_sha256"] = expected_corpus[1]
                raw_source = resolve_campaign_file(
                    campaign_root,
                    window.get("normalized_report"),
                    window.get("normalized_report_sha256"),
                    "performance normalized report",
                )
                resource_source = resolve_campaign_file(
                    campaign_root,
                    window.get("resource_samples"),
                    window.get("resource_samples_sha256"),
                    "performance resource samples",
                )
                destination = (
                    packet / "performance" / "windows" / lane_name / f"{label}.json"
                )
                copy_run_report(raw_source, destination)
                window["source_normalized_report_sha256"] = sha256(raw_source)
                window["normalized_report"] = destination.relative_to(packet).as_posix()
                window["normalized_report_sha256"] = sha256(destination)
                resource_destination = (
                    packet / "performance" / "resources" / lane_name / f"{label}.json"
                )
                copy_file(resource_source, resource_destination)
                window["resource_samples"] = (
                    resource_destination.relative_to(packet).as_posix()
                )
                window["resource_samples_sha256"] = sha256(resource_destination)
                vote_lock_source = resolve_campaign_file(
                    campaign_root,
                    window.get("vote_lock_work_receipt"),
                    window.get("vote_lock_work_receipt_sha256"),
                    "performance vote-lock work receipt",
                )
                vote_lock_destination = (
                    packet
                    / "performance"
                    / "vote-lock-work"
                    / lane_name
                    / f"{label}.json"
                )
                copy_file(vote_lock_source, vote_lock_destination)
                window["vote_lock_work_receipt"] = (
                    vote_lock_destination.relative_to(packet).as_posix()
                )
                window["vote_lock_work_receipt_sha256"] = sha256(
                    vote_lock_destination
                )
                for field, directory, label_text in (
                    (
                        "certified_send_work_receipt",
                        "certified-send-work",
                        "performance certified-send work receipt",
                    ),
                    (
                        "round_coverage_receipt",
                        "round-coverage",
                        "performance round-coverage receipt",
                    ),
                ):
                    source = resolve_campaign_file(
                        campaign_root,
                        window.get(field),
                        window.get(f"{field}_sha256"),
                        label_text,
                    )
                    target = (
                        packet
                        / "performance"
                        / directory
                        / lane_name
                        / f"{label}.json"
                    )
                    copy_file(source, target)
                    window[field] = target.relative_to(packet).as_posix()
                    window[f"{field}_sha256"] = sha256(target)
    report["rows"] = lanes["selected-indexed"]["rows"]
    destination = packet / "artifacts" / "performance.json"
    write_json(destination, report)
    return destination


def copy_tamper(packet: Path, source: Path) -> Path:
    report = read_json(source)
    if report.get("schema") != ARTIFACT_SCHEMAS["tamper"]:
        raise ValueError("tamper report schema mismatch")
    cases = report.get("cases")
    if not isinstance(cases, list):
        raise ValueError("tamper report omitted cases")
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("tamper case is malformed")
        receipt_source = resolve_report_reference(source, case.get("receipt"))
        name = str(case.get("name", ""))
        destination = packet / "tamper" / f"{name}.json"
        receipt = read_json(receipt_source)
        test_receipts = receipt.get("test_receipts")
        if not isinstance(test_receipts, list) or not test_receipts:
            raise ValueError("tamper receipt omitted executable test evidence")
        for test_receipt in test_receipts:
            if not isinstance(test_receipt, dict):
                raise ValueError("tamper test receipt is malformed")
            for evidence_key in ("report", "manifest"):
                if evidence_key not in test_receipt:
                    continue
                evidence_source = resolve_report_reference(
                    source,
                    test_receipt[evidence_key],
                )
                evidence_destination = (
                    packet / "tamper" / "evidence" / evidence_source.name
                )
                if evidence_destination.exists():
                    if sha256(evidence_destination) != sha256(evidence_source):
                        raise ValueError("tamper evidence destination conflicts")
                else:
                    copy_file(evidence_source, evidence_destination)
                test_receipt[evidence_key] = reference(packet, evidence_destination)
        write_json(destination, receipt)
        case["receipt"] = reference(packet, destination)
    destination = packet / "artifacts" / "tamper.json"
    write_json(destination, report)
    return destination


def copy_direct(
    packet: Path,
    source: Path,
    label: str,
) -> Path:
    report = read_json(source)
    if report.get("schema") != ARTIFACT_SCHEMAS[label]:
        raise ValueError(f"{label} report schema mismatch")
    destination = packet / "artifacts" / f"{label}.json"
    write_json(destination, report)
    return destination


def git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def git_clean() -> bool:
    return (
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        == ""
    )


def validate_capture_time(value: str) -> None:
    if not value.endswith("Z"):
        raise ValueError("--captured-at must be UTC and end with Z")
    datetime.fromisoformat(value[:-1] + "+00:00")


def redaction_record(
    allowed_nonlocal: set[str],
    binary_paths: frozenset[str],
) -> dict[str, Any]:
    """State what the redaction scan covered, including what it left out."""
    sys.path.insert(0, str(PYTHON_ROOT))
    from postfiat_rpc.storage_scaling import REDACTION_BINARY_EXEMPTION_REASON

    return {
        "schema": ARTIFACT_SCHEMAS["redaction"],
        "passed": True,
        "allowed_nonlocal_ip_files": sorted(allowed_nonlocal),
        "unscanned_binary_paths": sorted(binary_paths),
        "unscanned_binary_reason": REDACTION_BINARY_EXEMPTION_REASON,
        "unscanned_files_over_bytes": REDACTION_MAX_SCANNED_BYTES,
    }


def scan_redaction(
    packet: Path,
    allowed_nonlocal: set[str],
    binary_paths: frozenset[str] = frozenset(),
) -> None:
    """Scan every evidence file; only ELF files at the bound binary roles are exempt.

    Release binaries embed build-host source paths (panic locations); they are
    copied byte for byte and bound by SHA-256 in `artifacts/source.json`.
    """
    for path in packet.rglob("*"):
        if not path.is_file() or path.stat().st_size > REDACTION_MAX_SCANNED_BYTES:
            continue
        relative = path.relative_to(packet).as_posix()
        if relative in binary_paths and path.read_bytes()[:4] == b"\x7fELF":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if SENSITIVE.search(text):
            raise ValueError(f"sensitive marker found in packet file: {relative}")
        if LOCAL_PATH.search(text):
            raise ValueError(f"host-local path found in packet file: {relative}")
        if relative not in allowed_nonlocal and NONLOCAL_IPV4.search(text):
            raise ValueError(f"non-loopback IPv4 found in packet file: {relative}")


def write_checksums(packet: Path) -> None:
    files = sorted(
        path
        for path in packet.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (packet / "SHA256SUMS.txt").write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(packet).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--node-bin", type=Path, required=True)
    parser.add_argument("--batch-builder-bin", type=Path, required=True)
    parser.add_argument("--rollback-node-bin", type=Path, required=True)
    parser.add_argument("--incompatible-node-bin", type=Path, required=True)
    parser.add_argument("--state-distinction", type=Path, required=True)
    parser.add_argument("--replay-report", type=Path, required=True)
    parser.add_argument(
        "--replacement-archive-receipt",
        type=Path,
        help="signed-archive receipt replacing the lost 915 archive; "
        "--replay-report is then the legacy height-924 report",
    )
    parser.add_argument("--performance-report", type=Path, required=True)
    parser.add_argument("--tamper-report", type=Path, required=True)
    parser.add_argument("--migration-report", type=Path, required=True)
    parser.add_argument(
        "--allow-nonlocal-ip-file",
        action="append",
        default=[],
    )
    args = parser.parse_args()

    raw_packet = args.output_dir.expanduser()
    raw_node_bin = args.node_bin.expanduser()
    raw_batch_builder_bin = args.batch_builder_bin.expanduser()
    raw_rollback_node_bin = args.rollback_node_bin.expanduser()
    raw_incompatible_node_bin = args.incompatible_node_bin.expanduser()
    if (
        raw_packet.is_symlink()
        or raw_node_bin.is_symlink()
        or raw_batch_builder_bin.is_symlink()
        or raw_rollback_node_bin.is_symlink()
        or raw_incompatible_node_bin.is_symlink()
    ):
        raise ValueError("packet output and release binary paths must not be symlinks")
    packet = raw_packet.resolve()
    if packet.exists():
        raise ValueError(f"refusing to overwrite packet: {packet}")
    validate_capture_time(args.captured_at)
    if re.fullmatch(r"[0-9a-f]{40}", args.source_revision) is None:
        raise ValueError("candidate source revision is invalid")
    assembly_revision = git_revision()
    if not git_clean():
        raise ValueError("packet assembly requires a clean checkout")
    node_bin = raw_node_bin.resolve()
    batch_builder_bin = raw_batch_builder_bin.resolve()
    rollback_node_bin = raw_rollback_node_bin.resolve()
    incompatible_node_bin = raw_incompatible_node_bin.resolve()
    if not node_bin.is_file() or node_bin.parent.name != "release":
        raise ValueError("--node-bin must identify a regular target/release binary")
    if (
        not batch_builder_bin.is_file()
        or batch_builder_bin.parent.name != "release"
        or batch_builder_bin.name != "postfiat-storage-corpus-batches"
    ):
        raise ValueError(
            "--batch-builder-bin must identify the regular release corpus batch builder"
        )
    if (
        not rollback_node_bin.is_file()
        or rollback_node_bin.parent.name != "release"
        or rollback_node_bin == node_bin
        or sha256(rollback_node_bin) == sha256(node_bin)
    ):
        raise ValueError(
            "--rollback-node-bin must identify a distinct regular target/release binary"
        )
    if (
        not incompatible_node_bin.is_file()
        or incompatible_node_bin.parent.name != "release"
        or incompatible_node_bin in {node_bin, rollback_node_bin}
        or sha256(incompatible_node_bin)
        in {sha256(node_bin), sha256(rollback_node_bin)}
    ):
        raise ValueError(
            "--incompatible-node-bin must identify a third regular target/release binary"
        )
    performance = read_json(args.performance_report.resolve())
    migration = read_json(args.migration_report.resolve())
    binary_digest = sha256(node_bin)
    batch_builder_digest = sha256(batch_builder_bin)
    incompatible_binary_digest = sha256(incompatible_node_bin)
    performance_lanes = performance.get("lanes")
    if (
        performance.get("source_revision") != args.source_revision
        or performance.get("node_binary_sha256") != binary_digest
        or performance.get("batch_builder_binary_sha256")
        != batch_builder_digest
        or not isinstance(performance_lanes, dict)
        or set(performance_lanes) != {
            "selected-indexed",
            "legacy-jsonl",
        }
        or any(
            not isinstance(lane, dict)
            or lane.get("source_revision") != args.source_revision
            or lane.get("node_binary_sha256") != binary_digest
            for lane in performance_lanes.values()
        )
    ):
        raise ValueError("performance report source or binary identity mismatch")
    incompatible = migration.get("incompatible_binary")
    if (
        migration.get("status") != "PASS"
        or migration.get("evidence_eligible") is not True
        or migration.get("source_worktree_clean") is not True
        or migration.get("source_revision") != args.source_revision
        or migration.get("node_binary_sha256") != binary_digest
        or not isinstance(incompatible, dict)
        or incompatible.get("sha256") != incompatible_binary_digest
    ):
        raise ValueError("migration report is not an evidence-eligible binary-bound PASS")

    packet.mkdir(parents=True)
    binary_destination = packet / "bin" / "postfiat-node"
    copy_file(node_bin, binary_destination)
    batch_builder_destination = packet / "bin" / "postfiat-storage-corpus-batches"
    copy_file(batch_builder_bin, batch_builder_destination)
    rollback_binary_destination = packet / "bin" / "postfiat-node-rollback"
    copy_file(rollback_node_bin, rollback_binary_destination)
    incompatible_binary_destination = packet / "bin" / "postfiat-node-incompatible"
    copy_file(incompatible_node_bin, incompatible_binary_destination)
    binaries = [
        {
            "path": binary_destination.relative_to(packet).as_posix(),
            "sha256": sha256(binary_destination),
        },
        {
            "path": batch_builder_destination.relative_to(packet).as_posix(),
            "sha256": sha256(batch_builder_destination),
        },
        {
            "path": rollback_binary_destination.relative_to(packet).as_posix(),
            "sha256": sha256(rollback_binary_destination),
        },
        {
            "path": incompatible_binary_destination.relative_to(packet).as_posix(),
            "sha256": sha256(incompatible_binary_destination),
        },
    ]
    source_report = {
        "schema": ARTIFACT_SCHEMAS["source"],
        "git_revision": args.source_revision,
        "assembly_revision": assembly_revision,
        "spec_sha3_384": hashlib.sha3_384(SPEC.read_bytes()).hexdigest(),
        "binaries": binaries,
        "clean_checkout": True,
        "build_profile": "release",
    }
    source_path = packet / "artifacts" / "source.json"
    write_json(source_path, source_report)

    artifact_paths = {
        "source": source_path,
        "replay": (
            copy_replacement_replay(
                packet,
                args.replay_report.resolve(),
                args.replacement_archive_receipt.resolve(),
                binary_digest,
            )
            if args.replacement_archive_receipt is not None
            else copy_replay(packet, args.replay_report.resolve())
        ),
        "performance": copy_performance(packet, args.performance_report.resolve()),
        "tamper": copy_tamper(packet, args.tamper_report.resolve()),
        "migration": copy_direct(
            packet,
            args.migration_report.resolve(),
            "migration",
        ),
    }
    allowed_nonlocal = set(args.allow_nonlocal_ip_file)
    binary_paths = frozenset(str(binary["path"]) for binary in binaries)
    redaction_path = packet / "artifacts" / "redaction.json"
    write_json(redaction_path, redaction_record(allowed_nonlocal, binary_paths))
    artifact_paths["redaction"] = redaction_path

    state_distinction = read_json(args.state_distinction.resolve())
    manifest = {
        "schema": "postfiat-storage-scaling-evidence-packet-v1",
        "status": "PASS",
        "captured_at": args.captured_at,
        "source": {
            "git_revision": args.source_revision,
            "assembly_revision": assembly_revision,
            "spec_sha3_384": source_report["spec_sha3_384"],
            "binaries": binaries,
        },
        "state_distinction": state_distinction,
        "artifacts": {
            label: reference(packet, path)
            for label, path in artifact_paths.items()
        },
    }
    write_json(packet / "storage-scaling-packet.json", manifest)
    scan_redaction(packet, allowed_nonlocal, binary_paths)
    write_checksums(packet)

    sys.path.insert(0, str(PYTHON_ROOT))
    from postfiat_rpc.storage_scaling import verify_packet

    verified = verify_packet(packet)
    print(json.dumps(verified.report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
