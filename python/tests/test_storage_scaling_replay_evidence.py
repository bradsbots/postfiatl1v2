from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "benchmarks" / "storage-scaling" / "run_replay_evidence.py"


def _load_harness() -> Any:
    spec = importlib.util.spec_from_file_location(
        "postfiat_storage_replay_evidence_tests",
        HARNESS_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load storage replay evidence harness")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HARNESS = _load_harness()
REVISION = "86706699f646405743385beabf609c6771a518a3"
HEIGHT = 1123
TIP = "b" * 96
ROOT = "c" * 96
PUBLISHER = "pf4ebb800c5a985cfca61e3833c40ea60b6767644a"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FakeNode:
    """Answers the four node commands of the signed-archive path."""

    def __init__(self, *, tip: str = TIP, root: str = ROOT, verified: bool = True) -> None:
        self.tip = tip
        self.root = root
        self.verified = verified
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> dict[str, Any]:
        self.commands.append(command)
        name = command[1]
        identity = {
            "chain_id": HARNESS.CONTROLLED_CHAIN_ID,
            "genesis_hash": HARNESS.CONTROLLED_GENESIS_HASH,
            "protocol_version": 1,
        }
        if name == "snapshot-import-signed-finalized-checkpoint":
            return {
                **identity,
                "block_height": HEIGHT,
                "data_dir": command[command.index("--data-dir") + 1],
                "snapshot_dir": command[command.index("--snapshot-dir") + 1],
                "trusted_publisher_key_file": command[
                    command.index("--trusted-publisher-key-file") + 1
                ],
            }
        if name == "status":
            return {
                **identity,
                "block_height": HEIGHT,
                "block_tip_hash": self.tip,
                "state_root": self.root,
                "build_git_revision": REVISION[:8],
                "build_profile": "release",
                "storage": {
                    "commitment_version": "postfiat.replicated_state.v2",
                    "scheduled_activation_height": 930,
                },
            }
        if name == "verify-finalized-checkpoint":
            return {
                **identity,
                "verified": self.verified,
                "checkpoint_height": HEIGHT,
                "checkpoint_block_hash": self.tip,
                "checkpoint_state_root": self.root,
            }
        if name == "verify-state":
            return {
                **identity,
                "verified": self.verified,
                "block_log": {
                    "verified": self.verified,
                    "block_count": HEIGHT,
                    "tip_hash": self.tip,
                    "state_root": self.root,
                },
            }
        raise AssertionError(f"unexpected node command {name}")


class SignedArchiveReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.archive = self.root / "archive"
        _write_json(
            self.archive / "snapshot.signed-manifest.json",
            {
                "schema": "postfiat.signed_snapshot_manifest.v1",
                "publisher": PUBLISHER,
                "algorithm_id": "ML-DSA-65",
                "signature_hex": "aa",
                "manifest": {
                    "chain_id": HARNESS.CONTROLLED_CHAIN_ID,
                    "genesis_hash": HARNESS.CONTROLLED_GENESIS_HASH,
                    "node_id": "validator-1",
                    "block_height": HEIGHT,
                    "block_tip_hash": TIP,
                    "state_root": ROOT,
                },
            },
        )
        (self.archive / "blocks.json").write_text("[]\n", encoding="utf-8")
        self.trusted = self.root / "keys" / "snapshot-publisher.public.json"
        _write_json(
            self.trusted,
            {"schema": "postfiat.snapshot_publisher_key.v1", "publisher": PUBLISHER},
        )
        self.node_bin = self.root / "release" / "postfiat-node"
        self.node_bin.parent.mkdir()
        self.node_bin.write_bytes(b"node")
        self.output = self.root / "out"

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _replay(self, node: FakeNode, **overrides: Any) -> dict[str, str]:
        arguments: dict[str, Any] = {
            "node_bin": self.node_bin,
            "archive": self.archive,
            "trusted_publisher_file": self.trusted,
            "expected_height": HEIGHT,
            "expected_tip": TIP,
            "expected_root": ROOT,
            "output": self.output,
            "revision": REVISION,
            "harness_revision": "f" * 40,
        }
        arguments.update(overrides)
        with mock.patch.object(HARNESS, "run_json", node):
            return HARNESS.signed_archive_replay(**arguments)

    def test_signed_archive_replay_writes_matching_receipt(self) -> None:
        before = HARNESS.tree_sha256(self.archive)
        node = FakeNode()
        reference = self._replay(node)

        self.assertEqual(
            [command[1] for command in node.commands],
            [
                "snapshot-import-signed-finalized-checkpoint",
                "status",
                "verify-finalized-checkpoint",
                "verify-state",
            ],
        )
        imported = node.commands[0]
        snapshot_dir = Path(imported[imported.index("--snapshot-dir") + 1])
        self.assertNotEqual(snapshot_dir.resolve(), self.archive.resolve())
        self.assertEqual(imported[imported.index("--node-id") + 1], "validator-1")
        self.assertEqual(HARNESS.tree_sha256(self.archive), before)

        receipt_path = self.output / "receipts" / f"height-{HEIGHT}.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(reference["sha256"], hashlib.sha256(receipt_path.read_bytes()).hexdigest())
        self.assertEqual(receipt["schema"], "postfiat-storage-signed-archive-replay-receipt-v1")
        self.assertEqual(receipt["verdict"], "PASS")
        self.assertEqual(receipt["source_height"], HEIGHT)
        self.assertEqual((receipt["tip_hash"], receipt["state_root"]), (TIP, ROOT))
        self.assertEqual(receipt["source_tree_sha256"], before)
        self.assertEqual(receipt["source_tree_sha256_after"], before)
        self.assertEqual(
            receipt["signed_manifest_sha256"],
            HARNESS.sha256(self.archive / "snapshot.signed-manifest.json"),
        )
        self.assertEqual(receipt["trusted_publisher_file_sha256"], HARNESS.sha256(self.trusted))
        self.assertEqual(receipt["node_binary_sha256"], HARNESS.sha256(self.node_bin))
        self.assertEqual(receipt["matched"], {"height": True, "tip": True, "root": True})
        self.assertEqual(
            sorted(receipt["steps"]),
            sorted(
                [
                    "snapshot-import-signed-finalized-checkpoint",
                    "status",
                    "verify-finalized-checkpoint",
                    "verify-state",
                ]
            ),
        )
        for step in receipt["steps"].values():
            self.assertEqual(step["sha256"], HARNESS.sha256(self.output / step["path"]))
        self.assertEqual(receipt["source_revision"], REVISION)
        self.assertEqual(receipt["harness_revision"], "f" * 40)
        self.assertFalse(receipt["network_contacted"])

    def test_signed_archive_outputs_carry_no_host_paths(self) -> None:
        home = self.root / "home"
        home.mkdir()
        with mock.patch.object(tempfile, "tempdir", str(home)), mock.patch.object(
            Path, "home", lambda: home
        ):
            self._replay(FakeNode())
        self.assertEqual(
            _files_containing(self.output, str(self.root), skip=HARNESS.LOCAL_PATHS_FILE), []
        )
        step = json.loads(
            (self.output / "steps" / "snapshot-import-signed-finalized-checkpoint.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(step["data_dir"], "<scratch>/data")
        self.assertEqual(step["snapshot_dir"], "<scratch>/archive")
        self.assertEqual(step["trusted_publisher_key_file"], "<trusted-publisher-file>")
        local = json.loads((self.output / HARNESS.LOCAL_PATHS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(local["roots"]["<source>"], str(self.archive.resolve()))
        self.assertTrue(local["roots"]["<scratch>"].startswith(str(home)))

    def test_refuses_unsigned_archive(self) -> None:
        (self.archive / "snapshot.signed-manifest.json").unlink()
        node = FakeNode()
        with self.assertRaisesRegex(ValueError, "not a signed archive"):
            self._replay(node)
        self.assertEqual(node.commands, [])
        self.assertFalse(self.output.exists())

    def test_refuses_expected_values_that_differ_from_the_signed_manifest(self) -> None:
        node = FakeNode()
        with self.assertRaisesRegex(ValueError, "expected root does not match"):
            self._replay(node, expected_root="d" * 96)
        self.assertEqual(node.commands, [])
        self.assertFalse(self.output.exists())

    def test_refuses_untrusted_publisher(self) -> None:
        _write_json(
            self.trusted,
            {"schema": "postfiat.snapshot_publisher_key.v1", "publisher": "pf" + "0" * 40},
        )
        node = FakeNode()
        with self.assertRaisesRegex(ValueError, "publisher"):
            self._replay(node)
        self.assertEqual(node.commands, [])

    def test_refuses_replay_that_reaches_a_different_root(self) -> None:
        node = FakeNode(root="e" * 96)
        with self.assertRaisesRegex(RuntimeError, "state root"):
            self._replay(node)
        self.assertFalse((self.output / "receipts" / f"height-{HEIGHT}.json").exists())

    def test_refuses_unverified_full_replay(self) -> None:
        node = FakeNode(verified=False)
        with self.assertRaisesRegex(RuntimeError, "not verified"):
            self._replay(node)
        self.assertFalse((self.output / "receipts" / f"height-{HEIGHT}.json").exists())

    def test_pair_mode_still_requires_both_quarantine_sources(self) -> None:
        with mock.patch("sys.argv", ["run_replay_evidence.py", "--node-bin", "x"]):
            with self.assertRaises(SystemExit) as raised, mock.patch("sys.stderr"):
                HARNESS.main()
        self.assertEqual(raised.exception.code, 2)


LEGACY_HEIGHT = 924
LEGACY_TIP = "1" * 96
LEGACY_ROOT = "2" * 96
RECORDED_ROOTS = {
    "blocks_root": "3" * 96,
    "receipts_root": "4" * 96,
    "archive_root": "5" * 96,
    "ordered_batches_root": "6" * 96,
    "ordered_history_accumulator": "7" * 96,
    "current_state_root": "8" * 96,
}


def _legacy_manifest(roots: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": "postfiat-storage-migration-manifest-v2",
        "chain_id": HARNESS.CONTROLLED_CHAIN_ID,
        "genesis_hash": HARNESS.CONTROLLED_GENESIS_HASH,
        "source_tip": {
            "height": LEGACY_HEIGHT,
            "block_hash": LEGACY_TIP,
            "state_root": LEGACY_ROOT,
        },
        "block_count": LEGACY_HEIGHT,
        "receipt_count": 972,
        "archive_count": LEGACY_HEIGHT,
        "ordered_batch_count": LEGACY_HEIGHT,
        **roots,
        "logical_store_report": {"finalized_height": LEGACY_HEIGHT},
        "migration_packet_root": "",
        "node_state_root": "",
    }


def _files_containing(root: Path, needle: str, *, skip: str) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != skip and needle in path.read_text(encoding="utf-8")
    )


class FakeLegacyNode:
    """Answers the legacy pair-mode commands for one pre-activation source."""

    def __init__(
        self,
        *,
        commitment: str = "postfiat.replicated_state.v1",
        roots: dict[str, str] | None = None,
        verify_only_writes: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.extra = extra or {}
        self.commitment = commitment
        self.roots = roots or RECORDED_ROOTS
        self.verify_only_writes = verify_only_writes
        self.commands: list[list[str]] = []
        self.packet_root = ""

    def _rebuild(self, command: list[str]) -> dict[str, Any]:
        output = Path(command[command.index("--output-dir") + 1])
        export = output / "canonical-history.jsonl"
        receipt = {
            "schema": "postfiat-transactional-canonical-export-receipt-v1",
            "finalized_height": LEGACY_HEIGHT,
            "record_count": 4714,
            "records_sha3_384": "9" * 96,
        }
        verify_only = "--verify-only" in command
        if not verify_only:
            output.mkdir(parents=True)
            export.write_text("{}\n", encoding="utf-8")
            manifest = _legacy_manifest(self.roots)
            manifest["logical_store_report"]["store_dir"] = str(output)
            manifest["migration_packet_root"] = HARNESS.migration_packet_root(manifest)
            self.packet_root = manifest["migration_packet_root"]
            path = output / "storage-migration-manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            digest = hashlib.sha3_384(path.read_bytes()).hexdigest()
            (output / "storage-migration-manifest.sha3-384").write_text(
                f"{digest}  storage-migration-manifest.json\n", encoding="utf-8"
            )
        elif self.verify_only_writes and len(
            [c for c in self.commands if "--verify-only" in c]
        ) > 1:
            (output / "stray").write_text("x", encoding="utf-8")
        return {
            "schema": "postfiat-storage-migration-report-v1",
            "published": not verify_only,
            "verify_only": verify_only,
            "migration_packet_root": self.packet_root,
            "canonical_export_file": str(export),
            "canonical_export_receipt": receipt,
            "manifest_file": str(output / "storage-migration-manifest.json"),
            "output_dir": str(output),
            **self.extra,
        }

    def __call__(self, command: list[str]) -> dict[str, Any]:
        self.commands.append(command)
        name = command[1]
        if name == "status":
            return {
                "chain_id": HARNESS.CONTROLLED_CHAIN_ID,
                "genesis_hash": HARNESS.CONTROLLED_GENESIS_HASH,
                "protocol_version": 1,
                "block_height": LEGACY_HEIGHT,
                "block_tip_hash": LEGACY_TIP,
                "state_root": LEGACY_ROOT,
                "build_git_revision": REVISION[:8],
                "build_profile": "release",
                "storage": {"commitment_version": self.commitment},
            }
        if name == "storage-rebuild-transactional":
            return self._rebuild(command)
        raise AssertionError(f"unexpected node command {name}")


class LegacySourceReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.source = self.root / "validator-0"
        tip = {
            "schema": "postfiat-chain-tip-v1",
            "chain_id": HARNESS.CONTROLLED_CHAIN_ID,
            "genesis_hash": HARNESS.CONTROLLED_GENESIS_HASH,
            "height": LEGACY_HEIGHT,
            "block_hash": LEGACY_TIP,
            "state_root": LEGACY_ROOT,
        }
        self.source.mkdir()
        (self.source / "chain_tip.json").write_text(
            json.dumps(tip, indent=2) + "\npftmac1:" + "0" * 96 + "\n", encoding="utf-8"
        )
        (self.source / "blocks.json").write_text("[]\n", encoding="utf-8")
        self.recorded = self.root / "recorded" / "storage-migration-manifest.json"
        _write_json(self.recorded, _legacy_manifest(RECORDED_ROOTS))
        self.node_bin = self.root / "release" / "postfiat-node"
        self.node_bin.parent.mkdir()
        self.node_bin.write_bytes(b"node")
        self.output = self.root / "out"

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _replay(self, node: FakeLegacyNode, **overrides: Any) -> dict[str, str]:
        arguments: dict[str, Any] = {
            "node_bin": self.node_bin,
            "source": self.source,
            "expected_height": LEGACY_HEIGHT,
            "expected_tip": LEGACY_TIP,
            "expected_root": LEGACY_ROOT,
            "recorded_manifest": self.recorded,
            "output": self.output,
            "revision": REVISION,
            "harness_revision": "f" * 40,
        }
        arguments.update(overrides)
        with mock.patch.object(HARNESS, "run_json", node), mock.patch.object(
            HARNESS, "run_checked", lambda command: None
        ):
            return HARNESS.legacy_source_replay(**arguments)

    def test_legacy_source_replay_matches_recorded_values(self) -> None:
        before = HARNESS.tree_sha256(self.source)
        node = FakeLegacyNode()
        reference = self._replay(node)

        self.assertEqual(
            [command[1] for command in node.commands],
            ["status"] + ["storage-rebuild-transactional"] * 3,
        )
        self.assertEqual(sum("--verify-only" in c for c in node.commands), 2)
        data_dir = Path(node.commands[0][node.commands[0].index("--data-dir") + 1])
        self.assertNotEqual(data_dir.resolve(), self.source.resolve())
        self.assertEqual(HARNESS.tree_sha256(self.source), before)

        report_path = self.output / reference["path"]
        self.assertEqual(reference["sha256"], HARNESS.sha256(report_path))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["schema"], "postfiat-storage-legacy-replay-v1")
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(
            (report["source_height"], report["tip_hash"], report["state_root"]),
            (LEGACY_HEIGHT, LEGACY_TIP, LEGACY_ROOT),
        )
        self.assertEqual(report["source_tree_sha256"], before)
        self.assertEqual(report["source_tree_sha256_after"], before)
        verify = report["independent_verify_only"]
        self.assertEqual(verify["target_tree_sha256_before"], verify["target_tree_sha256_after"])
        self.assertEqual(verify["clone_tree_sha256_before"], verify["clone_tree_sha256_after"])
        self.assertEqual(
            verify["output"]["sha256"], HARNESS.sha256(self.output / verify["output"]["path"])
        )
        self.assertEqual(report["recorded_manifest_sha256"], HARNESS.sha256(self.recorded))
        self.assertTrue(all(report["matched"].values()))
        self.assertIn("blocks_root", report["matched"])
        receipt_ref = report["receipts"][0]
        receipt = json.loads((self.output / receipt_ref["path"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema"], "postfiat-storage-replay-receipt-v1")
        self.assertEqual(receipt["commitment_mode"], "legacy_below_storage_activation")
        self.assertEqual(receipt["source_tree_sha256"], before)
        self.assertEqual(report["harness_revision"], "f" * 40)
        self.assertFalse(report["network_contacted"])

    def test_legacy_outputs_carry_no_host_paths(self) -> None:
        home = self.root / "home"
        home.mkdir()
        with mock.patch.object(tempfile, "tempdir", str(home)), mock.patch.object(
            Path, "home", lambda: home
        ):
            self._replay(FakeLegacyNode())
        self.assertEqual(
            _files_containing(self.output, str(self.root), skip=HARNESS.LOCAL_PATHS_FILE), []
        )
        verify = json.loads((self.output / "verify-only.json").read_text(encoding="utf-8"))
        self.assertEqual(
            verify["canonical_export_file"], "<scratch>/transactional-924/canonical-history.jsonl"
        )
        self.assertEqual(verify["output_dir"], "<scratch>/transactional-924")
        receipt = json.loads(
            (self.output / "receipts" / "height-924.json").read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["logical_store_report"]["store_dir"], "<scratch>/transactional-924")
        local = json.loads((self.output / HARNESS.LOCAL_PATHS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(local["roots"]["<source>"], str(self.source.resolve()))
        self.assertTrue(local["roots"]["<scratch>"].startswith(str(home)))
        report = json.loads((self.output / "replay-report.json").read_text(encoding="utf-8"))
        self.assertNotIn(HARNESS.LOCAL_PATHS_FILE, json.dumps(report))

    def test_legacy_refuses_an_output_path_outside_the_declared_roots(self) -> None:
        node = FakeLegacyNode(extra={"log_file": "/var/log/postfiat/node.log"})
        with self.assertRaisesRegex(RuntimeError, "host path"):
            self._replay(node)
        self.assertFalse((self.output / "replay-report.json").exists())

    def test_pair_mode_receipt_carries_no_host_paths(self) -> None:
        home = self.root / "home"
        scratch = home / "scratch"
        scratch.mkdir(parents=True)
        receipt_path = self.output / "receipts" / "height-924.json"
        with mock.patch.object(HARNESS, "run_json", FakeLegacyNode()), mock.patch.object(
            HARNESS, "run_checked", lambda command: None
        ), mock.patch.object(Path, "home", lambda: home):
            HARNESS.replay_source(
                node_bin=self.node_bin,
                source=self.source,
                height=LEGACY_HEIGHT,
                source_kind="authenticated_history",
                scratch=scratch,
                receipt_path=receipt_path,
                revision=REVISION,
                source_tree_digest=HARNESS.tree_sha256(self.source),
            )
        text = receipt_path.read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), text)
        receipt = json.loads(text)
        self.assertEqual(receipt["logical_store_report"]["store_dir"], "<scratch>/transactional-924")

    def test_legacy_refuses_source_past_storage_activation(self) -> None:
        _write_json(self.source / "transactional_generation.json", {"generation": 1})
        node = FakeLegacyNode()
        with self.assertRaisesRegex(ValueError, "past storage activation"):
            self._replay(node)
        self.assertEqual(node.commands, [])
        self.assertFalse(self.output.exists())

    def test_legacy_refuses_post_activation_commitment(self) -> None:
        node = FakeLegacyNode(commitment="postfiat.replicated_state.v2")
        with self.assertRaisesRegex(RuntimeError, "below storage activation"):
            self._replay(node)
        self.assertFalse((self.output / "replay-report.json").exists())

    def test_legacy_refuses_expected_values_that_differ_from_the_chain_tip(self) -> None:
        node = FakeLegacyNode()
        with self.assertRaisesRegex(ValueError, "expected tip does not match"):
            self._replay(node, expected_tip="d" * 96)
        self.assertEqual(node.commands, [])
        self.assertFalse(self.output.exists())

    def test_legacy_refuses_replay_that_differs_from_the_recorded_manifest(self) -> None:
        node = FakeLegacyNode(roots={**RECORDED_ROOTS, "blocks_root": "e" * 96})
        with self.assertRaisesRegex(RuntimeError, "blocks_root differs"):
            self._replay(node)
        self.assertFalse((self.output / "replay-report.json").exists())

    def test_legacy_refuses_verify_only_that_changes_the_target(self) -> None:
        node = FakeLegacyNode(verify_only_writes=True)
        with self.assertRaisesRegex(RuntimeError, "changed during the independent --verify-only"):
            self._replay(node)
        self.assertFalse((self.output / "replay-report.json").exists())


if __name__ == "__main__":
    unittest.main()
