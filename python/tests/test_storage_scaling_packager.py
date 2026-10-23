from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
PACKAGER_PATH = REPO / "benchmarks" / "storage-scaling" / "package_packet.py"


def _load_packager() -> Any:
    spec = importlib.util.spec_from_file_location(
        "postfiat_storage_scaling_packager_tests",
        PACKAGER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load storage-scaling packet assembler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACKAGER = _load_packager()
LANE_HEIGHTS = {
    "selected-indexed": [50, 5000],
    "legacy-jsonl": [50],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _campaign(root: Path, *, label: str = "height-50-window-1") -> Path:
    corpora: dict[int, tuple[Path, str]] = {}
    for height in (50, 5000):
        corpus = root / "corpora" / f"height-{height}.json"
        _write_json(
            corpus,
            {
                "schema": "postfiat-tx-latency-signed-transfer-corpus-v1",
                "transfers": [{"height": height}],
            },
        )
        corpora[height] = (corpus, _sha256(corpus))

    lanes: dict[str, object] = {}
    for lane, heights in LANE_HEIGHTS.items():
        rows = []
        for height in heights:
            normalized = root / "raw" / lane / f"height-{height}.normalized.json"
            resources = root / "raw" / lane / f"height-{height}.resources.json"
            _write_json(normalized, {"lane": lane, "height": height, "kind": "normalized"})
            _write_json(resources, {"lane": lane, "height": height, "kind": "resources"})
            vote_lock = (
                root / "raw" / lane / f"height-{height}.vote-lock-work.json"
            )
            _write_json(
                vote_lock,
                {
                    "schema": "postfiat-storage-vote-lock-work-gate-v1",
                    "passed": True,
                },
            )
            certified_send = (
                root / "raw" / lane / f"height-{height}.certified-send-work.json"
            )
            _write_json(
                certified_send,
                {
                    "schema": "postfiat-storage-certified-send-work-gate-v1",
                    "passed": True,
                },
            )
            round_coverage = (
                root / "raw" / lane / f"height-{height}.round-coverage.json"
            )
            _write_json(
                round_coverage,
                {
                    "schema": "postfiat-storage-round-coverage-gate-v1",
                    "passed": True,
                },
            )
            window_label = (
                label
                if lane == "selected-indexed" and height == 50
                else f"height-{height}-window-1"
            )
            rows.append(
                {
                    "height": height,
                    "windows": [
                        {
                            "label": window_label,
                            "signed_transfer_corpus": corpora[height][0]
                            .relative_to(root)
                            .as_posix(),
                            "signed_transfer_corpus_sha256": corpora[height][1],
                            "normalized_report": normalized.relative_to(root).as_posix(),
                            "normalized_report_sha256": _sha256(normalized),
                            "resource_samples": resources.relative_to(root).as_posix(),
                            "resource_samples_sha256": _sha256(resources),
                            "vote_lock_work_receipt": (
                                vote_lock.relative_to(root).as_posix()
                            ),
                            "vote_lock_work_receipt_sha256": _sha256(vote_lock),
                            "certified_send_work_receipt": (
                                certified_send.relative_to(root).as_posix()
                            ),
                            "certified_send_work_receipt_sha256": _sha256(
                                certified_send
                            ),
                            "round_coverage_receipt": (
                                round_coverage.relative_to(root).as_posix()
                            ),
                            "round_coverage_receipt_sha256": _sha256(
                                round_coverage
                            ),
                        }
                    ],
                }
            )
        lanes[lane] = {"rows": rows}

    report = {
        "schema": PACKAGER.ARTIFACT_SCHEMAS["performance"],
        "status": "PASS",
        "campaign_mode": "release-qualification",
        "evidence_eligible": True,
        "materials_by_height": [
            {
                "height": height,
                "snapshot": (
                    f"canonical/snapshots/height-{height}.snapshot"
                    if height == 50
                    else None
                ),
                "snapshot_sha256": f"{height:064x}" if height == 50 else None,
                "prepared_fleet": f"prepared-fleets/height-{height}",
                "prepared_fleet_sha256": f"{height + 1:064x}",
                "corpus_source_mode": (
                    "authenticated-portable-snapshot-import"
                    if height == 50
                    else "disposable-canonical-prepared-fleet-clone"
                ),
                "corpus_source_prepared_fleet_sha256": (
                    None if height == 50 else f"{height + 1:064x}"
                ),
                "corpus_scratch_before_sha256": (
                    None if height == 50 else f"{height + 1:064x}"
                ),
                "corpus_scratch_after_sha256": (
                    None if height == 50 else f"{height + 3:064x}"
                ),
                "corpus_scratch_mutated": None if height == 50 else True,
                "corpus_scratch_discarded": None if height == 50 else True,
                "corpus_scratch_restored_sha256": (
                    None if height == 50 else f"{height + 1:064x}"
                ),
                "signed_transfer_corpus": corpus.relative_to(root).as_posix(),
                "signed_transfer_corpus_sha256": digest,
                "transfer_count": 50,
                "first_sequence": 1,
                "last_sequence": 50,
            }
            for height, (corpus, digest) in corpora.items()
        ],
        "lanes": lanes,
    }
    path = root / "campaign-report.json"
    _write_json(path, report)
    return path


class StorageScalingPackagerTests(unittest.TestCase):
    def test_copy_performance_copies_each_bound_resource_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            campaign.mkdir()
            source = _campaign(campaign)
            packet = root / "packet"

            destination = PACKAGER.copy_performance(packet, source)

            copied = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(
                copied["rows"],
                copied["lanes"]["selected-indexed"]["rows"],
            )
            corpora = {
                entry["height"]: entry
                for entry in copied["materials_by_height"]
            }
            self.assertEqual(set(corpora), {50, 5000})
            for entry in corpora.values():
                self.assertNotIn("prepared_fleet", entry)
                self.assertRegex(entry["prepared_fleet_sha256"], r"^[0-9a-f]{64}$")
                corpus = packet / entry["signed_transfer_corpus"]
                self.assertTrue(corpus.is_file())
                self.assertEqual(
                    _sha256(corpus),
                    entry["signed_transfer_corpus_sha256"],
                )
            for lane, heights in LANE_HEIGHTS.items():
                for row in copied["lanes"][lane]["rows"]:
                    height = row["height"]
                    self.assertIn(height, heights)
                    window = row["windows"][0]
                    normalized = packet / window["normalized_report"]
                    resources = packet / window["resource_samples"]
                    vote_lock = packet / window["vote_lock_work_receipt"]
                    certified_send = packet / window["certified_send_work_receipt"]
                    round_coverage = packet / window["round_coverage_receipt"]
                    self.assertTrue(normalized.is_file())
                    self.assertTrue(resources.is_file())
                    self.assertTrue(vote_lock.is_file())
                    self.assertTrue(certified_send.is_file())
                    self.assertTrue(round_coverage.is_file())
                    self.assertEqual(
                        _sha256(normalized),
                        window["normalized_report_sha256"],
                    )
                    self.assertEqual(
                        _sha256(resources),
                        window["resource_samples_sha256"],
                    )
                    self.assertEqual(
                        _sha256(vote_lock),
                        window["vote_lock_work_receipt_sha256"],
                    )
                    self.assertEqual(
                        _sha256(certified_send),
                        window["certified_send_work_receipt_sha256"],
                    )
                    self.assertEqual(
                        _sha256(round_coverage),
                        window["round_coverage_receipt_sha256"],
                    )
                    self.assertEqual(
                        window["signed_transfer_corpus"],
                        corpora[height]["signed_transfer_corpus"],
                    )
                    self.assertEqual(
                        window["signed_transfer_corpus_sha256"],
                        corpora[height]["signed_transfer_corpus_sha256"],
                    )

    def test_copy_performance_rejects_noncanonical_destination_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            campaign.mkdir()
            source = _campaign(campaign, label="../escape")
            packet = root / "packet"

            with self.assertRaisesRegex(ValueError, "label is not canonical"):
                PACKAGER.copy_performance(packet, source)
            self.assertFalse((root / "escape.json").exists())

    def test_copy_performance_includes_prepared_input_build_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            campaign.mkdir()
            source = _campaign(campaign)
            report = json.loads(source.read_text(encoding="utf-8"))
            advance_receipt = campaign / "prepared-input" / "advance-receipt.json"
            advance_report = campaign / "prepared-input" / "advance-report.json"
            _write_json(
                advance_receipt,
                {
                    "kind": "receipt",
                    "signed_transfer_corpus": "/host-local/corpus.json",
                },
            )
            _write_json(
                advance_report,
                {"kind": "report", "config": {"topology_file": "/home/x/topology.json"}},
            )
            manifest = {
                "schema": PACKAGER.PREPARED_INPUT_MANIFEST_SCHEMA,
                "candidate": {"source_revision": "a" * 40},
                "batch_builder": {"binary_sha256": "b" * 64},
                "runner": {"source_revision": "c" * 40},
                "build": {"final_height": 5000},
                "advances": [
                    {
                        "unit_id": "canonical/advance-1-to-5000",
                        "receipt": {"path": "unused", "sha256": _sha256(advance_receipt)},
                        "report": {"path": "unused", "sha256": _sha256(advance_report)},
                    }
                ],
            }
            manifest_path = campaign / "prepared-input" / "manifest.json"
            _write_json(manifest_path, manifest)
            report.update(
                {
                    "input_mode": "prepared-input-manifest",
                    "prepared_input_manifest": manifest_path.relative_to(
                        campaign
                    ).as_posix(),
                    "prepared_input_manifest_sha256": _sha256(manifest_path),
                    "prepared_input_build": {
                        key: manifest[key]
                        for key in ("candidate", "batch_builder", "runner", "build")
                    },
                    "prepared_input_import": {
                        "advances": [
                            {
                                "unit_id": "canonical/advance-1-to-5000",
                                "receipt": advance_receipt.relative_to(
                                    campaign
                                ).as_posix(),
                                "receipt_sha256": _sha256(advance_receipt),
                                "report": advance_report.relative_to(
                                    campaign
                                ).as_posix(),
                                "report_sha256": _sha256(advance_report),
                            }
                        ]
                    },
                }
            )
            _write_json(source, report)
            packet = root / "packet"

            destination = PACKAGER.copy_performance(packet, source)

            copied = json.loads(destination.read_text(encoding="utf-8"))
            copied_manifest = packet / copied["prepared_input_manifest"]
            self.assertEqual(_sha256(copied_manifest), _sha256(manifest_path))
            imported = copied["prepared_input_import"]["advances"][0]
            self.assertTrue((packet / imported["receipt"]).is_file())
            self.assertTrue((packet / imported["report"]).is_file())
            self.assertEqual(
                imported["source_receipt_sha256"],
                manifest["advances"][0]["receipt"]["sha256"],
            )
            copied_receipt = json.loads(
                (packet / imported["receipt"]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                copied_receipt["signed_transfer_corpus"],
                "$SIGNED_TRANSFER_CORPUS",
            )
            copied_report = json.loads(
                (packet / imported["report"]).read_text(encoding="utf-8")
            )
            self.assertEqual(copied_report["config"]["topology_file"], "$TOPOLOGY_FILE")
            self.assertEqual(
                imported["source_report_sha256"],
                manifest["advances"][0]["report"]["sha256"],
            )

    def test_copy_performance_redacts_window_topology_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            campaign.mkdir()
            source = _campaign(campaign)
            report = json.loads(source.read_text(encoding="utf-8"))
            window = report["lanes"]["selected-indexed"]["rows"][0]["windows"][0]
            normalized = campaign / window["normalized_report"]
            value = json.loads(normalized.read_text(encoding="utf-8"))
            value["config"] = {"topology_file": "/home/x/topology.json", "validators": 6}
            _write_json(normalized, value)
            window["normalized_report_sha256"] = _sha256(normalized)
            _write_json(source, report)
            packet = root / "packet"

            destination = PACKAGER.copy_performance(packet, source)

            copied = json.loads(destination.read_text(encoding="utf-8"))
            copied_window = copied["lanes"]["selected-indexed"]["rows"][0]["windows"][0]
            copied_path = packet / copied_window["normalized_report"]
            self.assertEqual(copied_window["normalized_report_sha256"], _sha256(copied_path))
            self.assertEqual(
                copied_window["source_normalized_report_sha256"], _sha256(normalized)
            )
            self.assertNotEqual(
                copied_window["source_normalized_report_sha256"],
                copied_window["normalized_report_sha256"],
            )
            verbatim = copied["lanes"]["legacy-jsonl"]["rows"][0]["windows"][0]
            self.assertEqual(
                verbatim["source_normalized_report_sha256"],
                verbatim["normalized_report_sha256"],
            )
            self.assertEqual(
                json.loads(copied_path.read_text(encoding="utf-8"))["config"],
                {"topology_file": "$TOPOLOGY_FILE", "validators": 6},
            )
            PACKAGER.scan_redaction(packet, set())

    def test_copy_performance_rejects_high_height_portable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            campaign.mkdir()
            source = _campaign(campaign)
            report = json.loads(source.read_text(encoding="utf-8"))
            high = report["materials_by_height"][1]
            high["snapshot"] = "canonical/snapshots/height-5000.snapshot"
            high["snapshot_sha256"] = "f" * 64
            _write_json(source, report)

            with self.assertRaisesRegex(ValueError, "prepared corpus binding"):
                PACKAGER.copy_performance(root / "packet", source)

    def test_copy_performance_rejects_scratch_not_cloned_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            campaign.mkdir()
            source = _campaign(campaign)
            report = json.loads(source.read_text(encoding="utf-8"))
            report["materials_by_height"][1][
                "corpus_scratch_before_sha256"
            ] = "f" * 64
            _write_json(source, report)

            with self.assertRaisesRegex(ValueError, "prepared corpus binding"):
                PACKAGER.copy_performance(root / "packet", source)

    def test_scan_redaction_scans_a_non_elf_file_in_a_binary_role(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            packet = Path(temporary)
            binary = packet / "bin" / "postfiat-storage-corpus-batches"
            binary.parent.mkdir()
            binary.write_bytes(b"#!/bin/sh\n# /home/builder/notes\n")
            with self.assertRaisesRegex(ValueError, "host-local path"):
                PACKAGER.scan_redaction(
                    packet, set(), frozenset({"bin/postfiat-storage-corpus-batches"})
                )

    def test_redaction_record_names_the_unscanned_binaries(self) -> None:
        roles = frozenset({"bin/postfiat-node", "bin/postfiat-storage-corpus-batches"})
        record = PACKAGER.redaction_record({"10.0.0.1.json"}, roles)
        self.assertEqual(record["unscanned_binary_paths"], sorted(roles))
        self.assertEqual(record["allowed_nonlocal_ip_files"], ["10.0.0.1.json"])
        self.assertEqual(record["unscanned_files_over_bytes"], 16 * 1024 * 1024)
        self.assertIn("ELF", record["unscanned_binary_reason"])

    def test_scan_redaction_skips_only_bound_release_binaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            packet = Path(temporary)
            binary = packet / "bin" / "postfiat-storage-corpus-batches"
            binary.parent.mkdir()
            binary.write_bytes(b"\x7fELF/home/builder/.cargo/registry/src/lib.rs")
            PACKAGER.scan_redaction(
                packet, set(), frozenset({"bin/postfiat-storage-corpus-batches"})
            )
            with self.assertRaisesRegex(ValueError, "host-local path"):
                PACKAGER.scan_redaction(packet, set())

    def test_resolve_campaign_file_rejects_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            campaign.mkdir()
            outside = root / "outside.json"
            _write_json(outside, {"outside": True})

            with self.assertRaisesRegex(ValueError, "path is unsafe"):
                PACKAGER.resolve_campaign_file(
                    campaign,
                    "../outside.json",
                    _sha256(outside),
                    "test artifact",
                )


REPLACEMENT_MANIFEST_SHA256 = (
    "d957141e68a29f8cf690aec9f9193ec0631fede0fad95a2329f4cf3a8b21189a"
)
BINARY = "e" * 64


VERIFY_ONLY_IDENTITY = {
    "migration_packet_root": "4" * 96,
    "logical_store_report": {"backend": "redb", "finalized_height": 924},
    "canonical_export_receipt": {"finalized_height": 924, "record_count": 1},
}


def _replacement_inputs(
    root: Path,
    *,
    verify_only: bool = True,
    verify_only_mutation: Any = None,
) -> tuple[Path, Path]:
    """Harness outputs: the 924 legacy report and the 1123 signed-archive receipt."""
    build = {"git_revision": "86706699", "profile": "release"}
    legacy_dir = root / "legacy-924"
    receipt_924 = legacy_dir / "receipts" / "height-924.json"
    _write_json(
        receipt_924,
        {
            "schema": "postfiat-storage-replay-receipt-v1",
            "source_height": 924,
            "exact_replay": True,
            "full_replay_passed": True,
            "logical_rebuild_identical": True,
            "canonical_export_identical": True,
            "node_binary_sha256": BINARY,
            "tip_hash": "1" * 96,
            "state_root": "2" * 96,
            **VERIFY_ONLY_IDENTITY,
        },
    )
    sentinel: dict[str, object] = {}
    if verify_only:
        output: dict[str, object] = {
            "schema": "postfiat-storage-migration-report-v1",
            "verify_only": True,
            "published": False,
            "source_tip": {"height": 924, "block_hash": "1" * 96, "state_root": "2" * 96},
            **VERIFY_ONLY_IDENTITY,
        }
        if verify_only_mutation is not None:
            verify_only_mutation(output)
        _write_json(legacy_dir / "verify-only.json", output)
        sentinel = {
            "independent_verify_only": {
                "output": {
                    "path": "verify-only.json",
                    "sha256": _sha256(legacy_dir / "verify-only.json"),
                },
                "clone_tree_sha256_before": "5" * 64,
                "clone_tree_sha256_after": "5" * 64,
                "target_tree_sha256_before": "6" * 64,
                "target_tree_sha256_after": "6" * 64,
            }
        }
    _write_json(
        legacy_dir / "replay-report.json",
        {
            "schema": "postfiat-storage-legacy-replay-v1",
            "verdict": "PASS",
            "source_height": 924,
            "tip_hash": "1" * 96,
            "state_root": "2" * 96,
            "ordered_history_accumulator": "3" * 96,
            "receipts": [
                {"path": "receipts/height-924.json", "sha256": _sha256(receipt_924)}
            ],
            "source_revision": "86706699" + "0" * 32,
            "node_binary_sha256": BINARY,
            "node_binary_build": build,
            **sentinel,
        },
    )
    archive_dir = root / "signed-1123"
    steps = {}
    for name in ("status", "verify-state"):
        path = archive_dir / "steps" / f"{name}.json"
        _write_json(path, {"step": name})
        steps[name] = {"path": f"steps/{name}.json", "sha256": _sha256(path)}
    receipt_1123 = archive_dir / "receipts" / "height-1123.json"
    _write_json(
        receipt_1123,
        {
            "schema": "postfiat-storage-signed-archive-replay-receipt-v1",
            "verdict": "PASS",
            "source_height": 1123,
            "signed_manifest_sha256": REPLACEMENT_MANIFEST_SHA256,
            "steps": steps,
            "node_binary_sha256": BINARY,
        },
    )
    return legacy_dir / "replay-report.json", receipt_1123


class ReplacementReplayPackagingTests(unittest.TestCase):
    def test_copy_replacement_replay_binds_signed_archive_and_924_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy, archive = _replacement_inputs(root)
            packet = root / "packet"
            destination = PACKAGER.copy_replacement_replay(packet, legacy, archive, BINARY)

            replay = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(replay["schema"], "postfiat-storage-scaling-replay-v1")
            self.assertNotIn("quarantine_archive_blocks", replay)
            self.assertEqual(replay["authenticated_history_height"], 924)
            self.assertEqual(replay["tip_hash"], "1" * 96)
            self.assertEqual(
                replay["receipts"],
                [
                    {
                        "path": "replay/height-924.json",
                        "sha256": _sha256(legacy.parent / "receipts" / "height-924.json"),
                    }
                ],
            )
            replacement = replay["quarantine_archive_replacement"]
            self.assertEqual(replacement["replaced_height"], 915)
            self.assertEqual(replacement["replacement_height"], 1123)
            self.assertEqual(replacement["signed_manifest_sha256"], REPLACEMENT_MANIFEST_SHA256)
            self.assertEqual(
                replacement["receipt"],
                {
                    "path": "replay/signed-archive-1123/receipts/height-1123.json",
                    "sha256": _sha256(archive),
                },
            )
            for name in ("status", "verify-state"):
                copied = packet / "replay" / "signed-archive-1123" / "steps" / f"{name}.json"
                self.assertEqual(
                    _sha256(copied), _sha256(archive.parent.parent / "steps" / f"{name}.json")
                )

    def test_copy_replacement_replay_binds_verify_only_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy, archive = _replacement_inputs(root)
            packet = root / "packet"
            destination = PACKAGER.copy_replacement_replay(packet, legacy, archive, BINARY)

            replay = json.loads(destination.read_text(encoding="utf-8"))
            bound = replay["independent_verify_only"]
            source = legacy.parent / "verify-only.json"
            self.assertEqual(
                bound["output"],
                {"path": "replay/height-924-verify-only.json", "sha256": _sha256(source)},
            )
            self.assertEqual(
                _sha256(packet / "replay" / "height-924-verify-only.json"), _sha256(source)
            )
            self.assertEqual(bound["clone_tree_sha256_after"], "5" * 64)
            self.assertEqual(bound["target_tree_sha256_after"], "6" * 64)

    def test_copy_replacement_replay_requires_verify_only_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy, archive = _replacement_inputs(root, verify_only=False)
            with self.assertRaisesRegex(ValueError, "independent verify-only"):
                PACKAGER.copy_replacement_replay(root / "packet", legacy, archive, BINARY)

    def test_copy_replacement_replay_rejects_verify_only_identity_split(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def other_root(output: dict[str, object]) -> None:
                output["migration_packet_root"] = "7" * 96

            legacy, archive = _replacement_inputs(root, verify_only_mutation=other_root)
            with self.assertRaisesRegex(ValueError, "disagrees with the height-924 receipt"):
                PACKAGER.copy_replacement_replay(root / "packet", legacy, archive, BINARY)

    def test_copy_replacement_replay_rejects_another_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy, archive = _replacement_inputs(root)
            with self.assertRaisesRegex(ValueError, "binary differs from the packet binary"):
                PACKAGER.copy_replacement_replay(root / "packet", legacy, archive, "f" * 64)

    def test_copy_replacement_replay_rejects_changed_step_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy, archive = _replacement_inputs(root)
            _write_json(archive.parent.parent / "steps" / "verify-state.json", {"step": "x"})
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                PACKAGER.copy_replacement_replay(root / "packet", legacy, archive, BINARY)

    def test_copy_replacement_replay_rejects_unapproved_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy, archive = _replacement_inputs(root)
            receipt = json.loads(archive.read_text(encoding="utf-8"))
            del receipt["signed_manifest_sha256"]
            _write_json(archive, receipt)
            with self.assertRaisesRegex(ValueError, "not the approved height-915 replacement"):
                PACKAGER.copy_replacement_replay(root / "packet", legacy, archive, BINARY)


if __name__ == "__main__":
    unittest.main()
