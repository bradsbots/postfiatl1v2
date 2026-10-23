"""The shadow runner binds the native L1 registry root from a signed archive."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from postfiat_rpc import tasknode_unl_policy as policy
from postfiat_rpc.tasknode_unl import main
from postfiat_rpc.tasknode_unl_schema import TaskNodeUnlError, canonical_json_bytes

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "tasknode_unl"
EXPECTED_JSON = FIXTURE_DIR / "expected-shadow-output.json"
# Root printed by `postfiat-node validator-registry-root` (binary 4085ac70…) for
# the six validators of the signed 1137 canary, and carried by its tip certificate.
NODE_ROOT_1137 = (
    "08a451e07aeaf9ada41a69e7c26dfd3fd86fce11c02f5567127c598b3cf775ac"
    "054b2add85295cc8c0d429bb6d2b9b1d"
)


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _documents(native: dict | None = None) -> dict[str, object]:
    manifest = _load("shadow-input.json")
    documents: dict[str, object] = {
        name: _load(manifest["files"][name]) for name in policy.SHADOW_INPUT_FILES
    }
    if native is not None:
        documents["native_registry"] = native
    return documents


def _native() -> dict:
    return _load("native-registry-1137.json")


def _snapshot_hash(payload: bytes) -> str:
    return hashlib.sha3_384(b"postfiat.snapshot.file.v1\0" + payload).hexdigest()


class NativeRegistryRootTests(unittest.TestCase):
    def test_python_root_equals_the_node_root_for_the_1137_registry(self) -> None:
        native = _native()
        self.assertEqual(policy.native_registry_root(native["validators"]), NODE_ROOT_1137)
        self.assertEqual(native["registry_root"], NODE_ROOT_1137)

    def test_native_root_is_accepted_recomputed_and_bound(self) -> None:
        report = policy.derive_shadow_report(_documents(_native()))

        self.assertEqual(report["native_registry"]["registry_root"], NODE_ROOT_1137)
        self.assertEqual(
            report["native_registry"]["validator_ids"],
            [f"validator-{index}" for index in range(6)],
        )
        self.assertEqual(report["native_registry"]["archive"]["height"], 1137)
        self.assertIn("native_registry", report["input_roots"])
        for candidate in report["candidates"]:
            self.assertEqual(candidate["evidence_packet"]["registry_root"], NODE_ROOT_1137)
            self.assertEqual(
                candidate["admission_decision"]["registry_delta_candidate"][
                    "previous_registry_root"
                ],
                NODE_ROOT_1137,
            )

    def test_wrong_native_root_is_refused(self) -> None:
        native = _native()
        native["registry_root"] = "0" * 96
        with self.assertRaisesRegex(TaskNodeUnlError, "native_registry_root_mismatch"):
            policy.derive_shadow_report(_documents(native))

    def test_changed_validator_key_is_refused(self) -> None:
        native = _native()
        native["validators"][2]["public_key_hex"] = "ab" * 32
        with self.assertRaisesRegex(TaskNodeUnlError, "native_registry_root_mismatch"):
            policy.derive_shadow_report(_documents(native))

    def test_certificate_root_must_equal_the_registry_root(self) -> None:
        native = _native()
        native["certificate_registry_root"] = "1" * 96
        with self.assertRaisesRegex(
            TaskNodeUnlError, "native_registry_certificate_root_mismatch"
        ):
            policy.derive_shadow_report(_documents(native))

    def test_native_kind_requires_a_96_hex_root(self) -> None:
        native = _native()
        native["registry_root"] = native["registry_root"][:64]
        with self.assertRaisesRegex(TaskNodeUnlError, "invalid_lower_hex"):
            policy.derive_shadow_report(_documents(native))

    def test_fork_content_hash_path_is_unchanged(self) -> None:
        report = policy.derive_shadow_report(_documents())
        self.assertEqual(
            json.loads(canonical_json_bytes(report)),
            json.loads(EXPECTED_JSON.read_text(encoding="utf-8")),
        )
        self.assertNotIn("native_registry", report)
        documents = _documents()
        documents["baseline_list"] = copy.deepcopy(documents["baseline_list"])
        documents["baseline_list"]["registry_root"] = NODE_ROOT_1137
        with self.assertRaisesRegex(TaskNodeUnlError, "invalid_lower_hex"):
            policy.derive_shadow_report(documents)


class NativeRegistryArchiveTests(unittest.TestCase):
    def _archive(self, root: Path, *, registry_tamper: bool = False) -> Path:
        native = _native()
        archive = root / "backup-signed"
        archive.mkdir()
        registry = {"validators": native["validators"]}
        governance = {
            "validator_registry_updates": [
                {"activation_height": 924, "new_registry_root": native["registry_root"]}
            ]
        }
        blocks = {
            "blocks": [
                {
                    "header": {
                        "height": native["archive"]["height"],
                        "certificate": {
                            "validators": [row["node_id"] for row in native["validators"]],
                            "registry_root": native["registry_root"],
                        },
                    }
                }
            ]
        }
        payloads = {
            "validator_registry.json": json.dumps(registry).encode(),
            "governance.json": json.dumps(governance).encode(),
            "blocks.json": json.dumps(blocks).encode(),
        }
        manifest_files = [
            {"name": name, "bytes": len(payload), "hash_hex": _snapshot_hash(payload)}
            for name, payload in payloads.items()
        ]
        if registry_tamper:
            registry["validators"] = list(reversed(registry["validators"]))
            payloads["validator_registry.json"] = json.dumps(registry).encode()
        for name, payload in payloads.items():
            (archive / name).write_bytes(payload)
        archive_identity = native["archive"]
        signed = {
            "manifest": {
                "chain_id": archive_identity["chain_id"],
                "genesis_hash": archive_identity["genesis_hash"],
                "block_height": archive_identity["height"],
                "block_tip_hash": archive_identity["block_hash"],
                "state_root": archive_identity["state_root"],
                "files": manifest_files,
            }
        }
        (archive / "snapshot.signed-manifest.json").write_text(json.dumps(signed))
        return archive

    def test_extract_reads_the_root_and_validator_set_from_the_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self._archive(Path(directory))
            document = policy.native_registry_from_archive(archive)
            self.assertEqual(document["registry_root"], NODE_ROOT_1137)
            self.assertEqual(document["validators"], _native()["validators"])
            self.assertEqual(
                document["archive"]["signed_manifest_sha256"],
                hashlib.sha256(
                    (archive / "snapshot.signed-manifest.json").read_bytes()
                ).hexdigest(),
            )

    def test_extract_refuses_a_file_the_manifest_does_not_bind(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self._archive(Path(directory), registry_tamper=True)
            with self.assertRaisesRegex(TaskNodeUnlError, "native_archive_file_unbound"):
                policy.native_registry_from_archive(archive)

    def test_cli_extracts_and_derives_with_the_native_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = self._archive(root)
            native_path = root / "native-registry.json"
            self.assertEqual(
                main(
                    [
                        "native-registry-extract",
                        "--archive-dir",
                        str(archive),
                        "--output",
                        str(native_path),
                    ]
                ),
                0,
            )
            inputs = root / "inputs"
            inputs.mkdir()
            manifest = _load("shadow-input.json")
            for name in manifest["files"].values():
                (inputs / name).write_bytes((FIXTURE_DIR / name).read_bytes())
            (inputs / "native-registry.json").write_bytes(native_path.read_bytes())
            manifest["files"]["native_registry"] = "native-registry.json"
            (inputs / "shadow-input.json").write_text(json.dumps(manifest))
            output = root / "shadow.json"
            self.assertEqual(
                main(["shadow-derive", "--input-dir", str(inputs), "--output", str(output)]),
                0,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["native_registry"]["registry_root"], NODE_ROOT_1137)


if __name__ == "__main__":
    unittest.main()
