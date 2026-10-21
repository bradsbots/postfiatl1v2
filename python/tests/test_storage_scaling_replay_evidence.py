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
            return {**identity, "block_height": HEIGHT}
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


if __name__ == "__main__":
    unittest.main()
