#!/usr/bin/env python3
"""Produce exact height-915 and height-924 storage replay receipts offline.

The supplied data directories are treated as immutable sources. Each replay is
performed on a disposable copy, rebuilt into the selected transactional store,
and independently verified against the authenticated legacy source. No network
or fleet endpoint is contacted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
REQUIRED_SOURCES = {
    915: "quarantine_archive",
    924: "authenticated_history",
}
CONTROLLED_CHAIN_ID = "postfiat-wan-devnet-2"
CONTROLLED_GENESIS_HASH = (
    "ce22ca8c932da0998b484483a09647138a30e0bf44408dd49a8d6d452787ad255"
    "21aff3ed334da07e150a7233a3e90a9"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_regular_tree(root: Path, label: str) -> None:
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"{label} is not a regular directory")
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError(f"{label} contains a symlink or special entry: {path}")


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_dir():
            digest.update(b"D")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            continue
        digest.update(b"F")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def migration_packet_root(manifest: dict[str, Any]) -> str:
    canonical = dict(manifest)
    canonical["migration_packet_root"] = ""
    canonical["node_state_root"] = ""
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha3_384()
    digest.update(b"postfiat.storage_migration.packet.v2")
    digest.update(b"\x00")
    digest.update(encoded)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path.name}")
    return value


LOCAL_PATHS_FILE = "local-paths.private.json"


class PathRedactor:
    """Writes evidence JSON with every host path replaced by a labelled root.

    A path under a declared root becomes ``<label>/relative/path`` (for example
    ``<scratch>/transactional-924``); a declared file becomes its label. Any
    other absolute path, or the home directory, refuses the write. The absolute
    roots go only to ``LOCAL_PATHS_FILE``, which no report references.
    """

    def __init__(self) -> None:
        self.roots: dict[str, Path] = {}
        self.files: dict[str, Path] = {}

    def root(self, label: str, path: Path) -> "PathRedactor":
        self.roots[label] = path
        return self

    def file(self, label: str, path: Path) -> "PathRedactor":
        self.files[label] = path
        return self

    def _replacements(self) -> list[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for label, path in self.files.items():
            for variant in {str(path), str(path.resolve())}:
                pairs.add((variant, f"<{label}>"))
        for label, path in self.roots.items():
            for variant in {str(path), str(path.resolve())}:
                pairs.add((variant, f"<{label}>"))
        return sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)

    def redact(self, value: Any, field: str = "") -> Any:
        if isinstance(value, dict):
            return {key: self.redact(item, f"{field}.{key}") for key, item in value.items()}
        if isinstance(value, list):
            return [self.redact(item, f"{field}[]") for item in value]
        if not isinstance(value, str):
            return value
        for absolute, label in self._replacements():
            value = value.replace(absolute, label)
        home = str(Path.home())
        if value.startswith("/") or (home not in {"", "/"} and home in value):
            raise RuntimeError(f"evidence output would carry a host path at {field.lstrip('.')}")
        return value

    def write(self, path: Path, value: Any) -> None:
        write_json(path, self.redact(value))

    def write_local_paths(self, output: Path) -> None:
        write_json(
            output / LOCAL_PATHS_FILE,
            {
                "schema": "postfiat-storage-replay-local-paths-v1",
                "note": "Host-local paths of this run; never bind this file into a packet.",
                "roots": {f"<{label}>": str(path) for label, path in self.roots.items()},
                "files": {f"<{label}>": str(path) for label, path in self.files.items()},
            },
        )


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


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        message = detail[0] if detail else "no diagnostic emitted"
        raise RuntimeError(
            f"{Path(command[0]).name} {command[1]} failed: {message}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"{Path(command[0]).name} {command[1]} did not emit JSON"
        ) from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{Path(command[0]).name} {command[1]} emitted non-object JSON")
    return value


def run_checked(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        message = detail[0] if detail else "no diagnostic emitted"
        raise RuntimeError(
            f"{Path(command[0]).name} {command[1]} failed: {message}"
        )


def replay_source(
    *,
    node_bin: Path,
    source: Path,
    height: int,
    source_kind: str,
    scratch: Path,
    receipt_path: Path,
    revision: str,
    source_tree_digest: str,
    redactor: PathRedactor | None = None,
) -> dict[str, str]:
    if redactor is None:
        redactor = PathRedactor().root("scratch", scratch).root("source", source).file(
            "node-bin", node_bin
        )
    clone = scratch / f"source-{height}"
    rebuild = scratch / f"transactional-{height}"
    shutil.copytree(source, clone, copy_function=shutil.copy2)

    status = run_json(
        [
            str(node_bin),
            "status",
            "--data-dir",
            str(clone),
            "--expect-height",
            str(height),
        ]
    )
    if status.get("block_height") != height:
        raise RuntimeError(f"{source_kind} source is not at exact height {height}")
    if status.get("build_git_revision") != revision[:8]:
        raise RuntimeError(
            f"{source_kind} replay binary is not built from the requested source"
        )
    if status.get("build_profile") != "release":
        raise RuntimeError(f"{source_kind} replay binary is not a release build")
    if status.get("chain_id") != CONTROLLED_CHAIN_ID:
        raise RuntimeError(f"{source_kind} source is not the controlled chain")
    if status.get("genesis_hash") != CONTROLLED_GENESIS_HASH:
        raise RuntimeError(f"{source_kind} source is not the controlled genesis")
    storage = status.get("storage")
    if not isinstance(storage, dict):
        raise RuntimeError(f"{source_kind} source omitted storage status")
    if storage.get("commitment_version") != "postfiat.replicated_state.v1":
        raise RuntimeError(f"{source_kind} source is not below storage activation")

    for command in (
        "verify-state",
        "verify-blocks",
        "verify-governance",
        "verify-bridge",
        "verify-mempool",
        "verify-shielded",
    ):
        run_checked([str(node_bin), command, "--data-dir", str(clone)])

    tip_hash = str(status.get("block_tip_hash", ""))
    state_root = str(status.get("state_root", ""))
    if len(tip_hash) != 96 or len(state_root) != 96:
        raise RuntimeError(f"{source_kind} source identities are malformed")

    rebuilt = run_json(
        [
            str(node_bin),
            "storage-rebuild-transactional",
            "--data-dir",
            str(clone),
            "--output-dir",
            str(rebuild),
            "--expected-tip",
            tip_hash,
            "--expected-state-root",
            state_root,
            "--offline-confirmed",
        ]
    )
    verified = run_json(
        [
            str(node_bin),
            "storage-rebuild-transactional",
            "--data-dir",
            str(clone),
            "--output-dir",
            str(rebuild),
            "--expected-tip",
            tip_hash,
            "--expected-state-root",
            state_root,
            "--verify-only",
            "--offline-confirmed",
        ]
    )
    if (
        rebuilt.get("schema") != "postfiat-storage-migration-report-v1"
        or rebuilt.get("published") is not True
        or verified.get("schema") != "postfiat-storage-migration-report-v1"
        or verified.get("verify_only") is not True
        or verified.get("published") is not False
        or rebuilt.get("migration_packet_root")
        != verified.get("migration_packet_root")
    ):
        raise RuntimeError(f"{source_kind} transactional rebuild did not verify")
    canonical_export_path = Path(str(rebuilt.get("canonical_export_file", "")))
    canonical_export_receipt = rebuilt.get("canonical_export_receipt")
    if (
        canonical_export_path.resolve()
        != (rebuild / "canonical-history.jsonl").resolve()
        or not canonical_export_path.is_file()
        or not isinstance(canonical_export_receipt, dict)
        or canonical_export_receipt != verified.get("canonical_export_receipt")
        or canonical_export_receipt.get("schema")
        != "postfiat-transactional-canonical-export-receipt-v1"
        or canonical_export_receipt.get("finalized_height") != height
        or type(canonical_export_receipt.get("record_count")) is not int
        or canonical_export_receipt.get("record_count", 0) <= 0
        or len(str(canonical_export_receipt.get("records_sha3_384", ""))) != 96
        or any(
            character not in "0123456789abcdef"
            for character in str(canonical_export_receipt.get("records_sha3_384", ""))
        )
    ):
        raise RuntimeError(f"{source_kind} canonical JSONL export did not verify")

    manifest_path = rebuild / "storage-migration-manifest.json"
    checksum_path = rebuild / "storage-migration-manifest.sha3-384"
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "postfiat-storage-migration-manifest-v2"
        or manifest.get("chain_id") != CONTROLLED_CHAIN_ID
        or manifest.get("genesis_hash") != CONTROLLED_GENESIS_HASH
        or manifest.get("block_count") != height
        or manifest.get("source_tip", {}).get("height") != height
        or manifest.get("source_tip", {}).get("block_hash") != tip_hash
        or manifest.get("source_tip", {}).get("state_root") != state_root
    ):
        raise RuntimeError(f"{source_kind} migration manifest is not exact")
    packet_root = migration_packet_root(manifest)
    checksum = checksum_path.read_text(encoding="utf-8")
    manifest_file_sha3_384 = hashlib.sha3_384(manifest_path.read_bytes()).hexdigest()
    expected_checksum = (
        f"{manifest_file_sha3_384}  storage-migration-manifest.json\n"
    )
    if (
        packet_root != manifest.get("migration_packet_root")
        or packet_root != rebuilt.get("migration_packet_root")
        or packet_root != verified.get("migration_packet_root")
        or checksum != expected_checksum
    ):
        raise RuntimeError(f"{source_kind} migration manifest packet root failed")

    ordered_history = str(manifest.get("ordered_history_accumulator", ""))
    if len(ordered_history) != 96:
        raise RuntimeError(f"{source_kind} ordered-history accumulator is malformed")
    logical_report = manifest.get("logical_store_report")
    if not isinstance(logical_report, dict):
        raise RuntimeError(f"{source_kind} logical integrity report is missing")

    receipt: dict[str, Any] = {
        "schema": "postfiat-storage-replay-receipt-v1",
        "source_height": height,
        "source_kind": source_kind,
        "block_count": height,
        "commitment_mode": "legacy_below_storage_activation",
        "exact_replay": True,
        "full_replay_passed": True,
        "logical_rebuild_identical": True,
        "canonical_export_identical": True,
        "canonical_export_receipt": canonical_export_receipt,
        "canonical_export_sha256": sha256(canonical_export_path),
        "tip_hash": tip_hash,
        "state_root": state_root,
        "ordered_history_accumulator": ordered_history,
        "chain_id": status.get("chain_id"),
        "genesis_hash": status.get("genesis_hash"),
        "protocol_version": status.get("protocol_version"),
        "receipt_count": manifest.get("receipt_count"),
        "archive_count": manifest.get("archive_count"),
        "ordered_batch_count": manifest.get("ordered_batch_count"),
        "blocks_root": manifest.get("blocks_root"),
        "receipts_root": manifest.get("receipts_root"),
        "archive_root": manifest.get("archive_root"),
        "ordered_batches_root": manifest.get("ordered_batches_root"),
        "current_state_root": manifest.get("current_state_root"),
        "migration_packet_root": packet_root,
        "migration_manifest_sha256": sha256(manifest_path),
        "migration_manifest_sha3_384": hashlib.sha3_384(
            manifest_path.read_bytes()
        ).hexdigest(),
        "source_tree_sha256": source_tree_digest,
        "logical_store_report": logical_report,
        "source_revision": revision,
        "node_binary_sha256": sha256(node_bin),
        "node_binary_build": {
            "git_revision": status["build_git_revision"],
            "profile": status["build_profile"],
        },
        "offline": True,
        "network_contacted": False,
    }
    redactor.write(receipt_path, receipt)
    return {
        "path": receipt_path.relative_to(receipt_path.parent.parent).as_posix(),
        "sha256": sha256(receipt_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-bin", type=Path, required=True)
    parser.add_argument("--quarantine-dir", type=Path, required=True)
    parser.add_argument("--authenticated-history-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-source-revision", required=True)
    args = parser.parse_args()

    raw_node_bin = args.node_bin.expanduser()
    raw_output = args.output_dir.expanduser()
    raw_sources = {
        915: args.quarantine_dir.expanduser(),
        924: args.authenticated_history_dir.expanduser(),
    }
    if raw_node_bin.is_symlink() or raw_output.is_symlink():
        raise ValueError("binary and output paths must not be symlinks")
    for height, source in raw_sources.items():
        if source.is_symlink():
            raise ValueError(f"height-{height} source path must not be a symlink")

    node_bin = raw_node_bin.resolve()
    output = raw_output.resolve()
    sources = {height: path.resolve() for height, path in raw_sources.items()}
    if not node_bin.is_file() or node_bin.is_symlink() or node_bin.parent.name != "release":
        raise ValueError("--node-bin must identify a regular target/release binary")
    if output.exists():
        raise ValueError(f"refusing to overwrite output directory: {output}")
    revision = git_revision()
    if revision != args.expected_source_revision:
        raise ValueError("HEAD does not match --expected-source-revision")
    if not git_clean():
        raise ValueError("replay evidence requires a clean checkout")

    source_digests: dict[int, str] = {}
    for height, source in sources.items():
        validate_regular_tree(source, f"height-{height} source")
        if (
            output == source
            or output.is_relative_to(source)
            or source.is_relative_to(output)
        ):
            raise ValueError(
                f"height-{height} source and output directory must be disjoint"
            )
        source_digests[height] = tree_sha256(source)

    output.mkdir(parents=True)
    receipts_dir = output / "receipts"
    receipts_dir.mkdir()

    references: list[dict[str, str]] = []
    receipts: dict[int, dict[str, Any]] = {}
    redactor = PathRedactor().root("output", output).file("node-bin", node_bin)
    for height, source in sources.items():
        redactor.root(f"source-{height}", source)
    with tempfile.TemporaryDirectory(prefix="postfiat-storage-replay-") as temporary:
        scratch = Path(temporary)
        redactor.root("scratch", scratch)
        for height, source_kind in REQUIRED_SOURCES.items():
            receipt_path = receipts_dir / f"height-{height}.json"
            references.append(
                replay_source(
                    node_bin=node_bin,
                    source=sources[height],
                    height=height,
                    source_kind=source_kind,
                    scratch=scratch,
                    receipt_path=receipt_path,
                    revision=revision,
                    source_tree_digest=source_digests[height],
                    redactor=redactor,
                )
            )
            receipts[height] = read_json(receipt_path)
            if tree_sha256(sources[height]) != source_digests[height]:
                raise RuntimeError(
                    f"height-{height} immutable source changed during replay"
                )

    authenticated = receipts[924]
    report = {
        "schema": "postfiat-storage-scaling-replay-v1",
        "quarantine_archive_blocks": 915,
        "authenticated_history_height": 924,
        "exact_pre_activation_replay": True,
        "full_replay_passed": True,
        "logical_rebuild_identical": True,
        "canonical_export_identical": True,
        "tip_hash": authenticated["tip_hash"],
        "state_root": authenticated["state_root"],
        "ordered_history_accumulator": authenticated[
            "ordered_history_accumulator"
        ],
        "receipts": references,
        "source_revision": revision,
        "node_binary_sha256": sha256(node_bin),
        "node_binary_build": authenticated["node_binary_build"],
        "offline": True,
        "network_contacted": False,
    }
    report_path = output / "replay-report.json"
    redactor.write(report_path, report)
    redactor.write_local_paths(output)
    print(f"storage-scaling-replay=PASS")
    print(f"report={report_path}")
    return 0


SIGNED_MANIFEST_FILE = "snapshot.signed-manifest.json"
SIGNED_ARCHIVE_STEPS = (
    "snapshot-import-signed-finalized-checkpoint",
    "status",
    "verify-finalized-checkpoint",
    "verify-state",
)


def signed_archive_replay(
    *,
    node_bin: Path,
    archive: Path,
    trusted_publisher_file: Path,
    expected_height: int,
    expected_tip: str,
    expected_root: str,
    output: Path,
    revision: str,
    harness_revision: str = "",
) -> dict[str, str]:
    """Replay a signed post-activation export on a scratch copy.

    Signed import, finalized-checkpoint verification and the full verify-state
    replay run with ``node_bin``; the archive itself is only read and hashed.
    """
    validate_regular_tree(archive, "signed archive")
    manifest_path = archive / SIGNED_MANIFEST_FILE
    if not manifest_path.is_file():
        raise ValueError(f"source is not a signed archive: {SIGNED_MANIFEST_FILE} missing")
    signed = read_json(manifest_path)
    inner = signed.get("manifest")
    if (
        signed.get("schema") != "postfiat.signed_snapshot_manifest.v1"
        or not signed.get("signature_hex")
        or not isinstance(inner, dict)
    ):
        raise ValueError("source is not a signed archive: malformed signed manifest")
    if (
        inner.get("chain_id") != CONTROLLED_CHAIN_ID
        or inner.get("genesis_hash") != CONTROLLED_GENESIS_HASH
    ):
        raise ValueError("signed archive is not the controlled chain")
    for label, want, have in (
        ("height", expected_height, inner.get("block_height")),
        ("tip", expected_tip, inner.get("block_tip_hash")),
        ("root", expected_root, inner.get("state_root")),
    ):
        if want != have:
            raise ValueError(f"expected {label} does not match the signed manifest")
    trusted = read_json(trusted_publisher_file)
    if trusted.get("publisher") != signed.get("publisher"):
        raise ValueError("trusted publisher file does not name the manifest publisher")
    if output.exists():
        raise ValueError(f"refusing to overwrite output directory: {output}")
    if output.is_relative_to(archive) or archive.is_relative_to(output):
        raise ValueError("signed archive and output directory must be disjoint")

    source_tree_digest = tree_sha256(archive)
    output.mkdir(parents=True)
    steps_dir = output / "steps"
    steps: dict[str, dict[str, str]] = {}
    results: dict[str, dict[str, Any]] = {}
    redactor = (
        PathRedactor()
        .root("source", archive)
        .root("output", output)
        .file("node-bin", node_bin)
        .file("trusted-publisher-file", trusted_publisher_file)
    )

    def step(name: str, *arguments: str) -> dict[str, Any]:
        value = run_json([str(node_bin), name, *arguments])
        path = steps_dir / f"{name}.json"
        redactor.write(path, value)
        steps[name] = {"path": path.relative_to(output).as_posix(), "sha256": sha256(path)}
        results[name] = value
        return value

    with tempfile.TemporaryDirectory(prefix="postfiat-signed-archive-replay-") as temporary:
        scratch = Path(temporary)
        redactor.root("scratch", scratch)
        copy = scratch / "archive"
        data = scratch / "data"
        shutil.copytree(archive, copy, copy_function=shutil.copy2)
        step(
            SIGNED_ARCHIVE_STEPS[0],
            "--data-dir", str(data),
            "--snapshot-dir", str(copy),
            "--trusted-publisher-key-file", str(trusted_publisher_file),
            "--node-id", str(inner.get("node_id", "")),
        )
        status = step("status", "--data-dir", str(data), "--expect-height", str(expected_height))
        checkpoint = step("verify-finalized-checkpoint", "--data-dir", str(data))
        state = step("verify-state", "--data-dir", str(data))

    if status.get("build_git_revision") != revision[:8]:
        raise RuntimeError("replay binary is not built from the requested source")
    if status.get("build_profile") != "release":
        raise RuntimeError("replay binary is not a release build")
    block_log = state.get("block_log")
    if (
        checkpoint.get("verified") is not True
        or state.get("verified") is not True
        or not isinstance(block_log, dict)
        or block_log.get("verified") is not True
    ):
        raise RuntimeError("signed archive replay is not verified")
    observed = {
        "status": (
            status.get("block_height"),
            status.get("block_tip_hash"),
            status.get("state_root"),
        ),
        "verify-finalized-checkpoint": (
            checkpoint.get("checkpoint_height"),
            checkpoint.get("checkpoint_block_hash"),
            checkpoint.get("checkpoint_state_root"),
        ),
        "verify-state": (
            block_log.get("block_count"),
            block_log.get("tip_hash"),
            block_log.get("state_root"),
        ),
    }
    for name, (height, tip, root) in observed.items():
        if height != expected_height:
            raise RuntimeError(f"{name} height {height} differs from the expected height")
        if tip != expected_tip:
            raise RuntimeError(f"{name} tip hash differs from the expected tip")
        if root != expected_root:
            raise RuntimeError(f"{name} state root differs from the expected root")
    source_tree_after = tree_sha256(archive)
    if source_tree_after != source_tree_digest:
        raise RuntimeError("signed archive changed during replay")

    storage = status.get("storage") if isinstance(status.get("storage"), dict) else {}
    receipt: dict[str, Any] = {
        "schema": "postfiat-storage-signed-archive-replay-receipt-v1",
        "source_height": expected_height,
        "source_kind": "signed_archive",
        "block_count": expected_height,
        "commitment_version": storage.get("commitment_version"),
        "storage_activation_height": storage.get("scheduled_activation_height"),
        "exact_replay": True,
        "full_replay_passed": True,
        "tip_hash": expected_tip,
        "state_root": expected_root,
        "matched": {"height": True, "tip": True, "root": True},
        "verdict": "PASS",
        "chain_id": status.get("chain_id"),
        "genesis_hash": status.get("genesis_hash"),
        "protocol_version": status.get("protocol_version"),
        "node_id": inner.get("node_id"),
        "publisher": signed.get("publisher"),
        "signed_manifest_sha256": sha256(manifest_path),
        "trusted_publisher_file_sha256": sha256(trusted_publisher_file),
        "source_tree_sha256": source_tree_digest,
        "source_tree_sha256_after": source_tree_after,
        "steps": steps,
        "source_revision": revision,
        "harness_revision": harness_revision,
        "node_binary_sha256": sha256(node_bin),
        "node_binary_build": {
            "git_revision": status["build_git_revision"],
            "profile": status["build_profile"],
        },
        "offline": True,
        "network_contacted": False,
    }
    receipt_path = output / "receipts" / f"height-{expected_height}.json"
    redactor.write(receipt_path, receipt)
    redactor.write_local_paths(output)
    return {
        "path": receipt_path.relative_to(output).as_posix(),
        "sha256": sha256(receipt_path),
    }


def signed_archive_main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay one signed post-activation archive offline."
    )
    parser.add_argument("--node-bin", type=Path, required=True)
    parser.add_argument("--signed-archive-dir", type=Path, required=True)
    parser.add_argument("--trusted-publisher-file", type=Path, required=True)
    parser.add_argument("--expected-height", type=int, required=True)
    parser.add_argument("--expected-tip", required=True)
    parser.add_argument("--expected-root", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-source-revision", required=True)
    args = parser.parse_args()

    paths = (
        args.node_bin.expanduser(),
        args.signed_archive_dir.expanduser(),
        args.trusted_publisher_file.expanduser(),
        args.output_dir.expanduser(),
    )
    if any(path.is_symlink() for path in paths):
        raise ValueError("binary, archive, publisher and output paths must not be symlinks")
    node_bin, archive, trusted, output = (path.resolve() for path in paths)
    if not node_bin.is_file() or node_bin.parent.name != "release":
        raise ValueError("--node-bin must identify a regular target/release binary")
    # A frozen release binary predates this mode: --expected-source-revision
    # names the binary's source, which must be in this checkout's history.
    revision = args.expected_source_revision
    if len(revision) != 40 or subprocess.run(
        ["git", "merge-base", "--is-ancestor", revision, "HEAD"], cwd=REPO
    ).returncode != 0:
        raise ValueError("--expected-source-revision is not an ancestor of HEAD")
    if not git_clean():
        raise ValueError("replay evidence requires a clean checkout")
    reference = signed_archive_replay(
        node_bin=node_bin,
        archive=archive,
        trusted_publisher_file=trusted,
        expected_height=args.expected_height,
        expected_tip=args.expected_tip,
        expected_root=args.expected_root,
        output=output,
        revision=revision,
        harness_revision=git_revision(),
    )
    print("storage-signed-archive-replay=PASS")
    print(f"receipt={output / reference['path']}")
    print(f"receipt_sha256={reference['sha256']}")
    return 0


LEGACY_TIP_FILE = "chain_tip.json"
TRANSACTIONAL_MARKER = "transactional_generation.json"
RECORDED_MANIFEST_FIELDS = (
    "block_count",
    "receipt_count",
    "archive_count",
    "ordered_batch_count",
    "blocks_root",
    "receipts_root",
    "archive_root",
    "ordered_batches_root",
    "ordered_history_accumulator",
    "current_state_root",
)


def legacy_source_replay(
    *,
    node_bin: Path,
    source: Path,
    expected_height: int,
    expected_tip: str,
    expected_root: str,
    recorded_manifest: Path,
    output: Path,
    revision: str,
    harness_revision: str = "",
) -> dict[str, str]:
    """Replay one legacy pre-activation data directory with the pair-mode path.

    ``replay_source`` runs on a scratch copy; an independent ``--verify-only``
    then re-checks the rebuilt store while both scratch trees are hashed.
    """
    validate_regular_tree(source, "legacy source")
    if (source / TRANSACTIONAL_MARKER).exists():
        raise ValueError(f"legacy source is past storage activation: {TRANSACTIONAL_MARKER}")
    tip_path = source / LEGACY_TIP_FILE
    if not tip_path.is_file():
        raise ValueError(f"source is not a legacy data directory: {LEGACY_TIP_FILE} missing")
    # The node appends a MAC line after the JSON object; read the object only.
    tip, _ = json.JSONDecoder().raw_decode(tip_path.read_text(encoding="utf-8"))
    if not isinstance(tip, dict):
        raise ValueError(f"expected a JSON object: {LEGACY_TIP_FILE}")
    recorded = read_json(recorded_manifest)
    recorded_tip = recorded.get("source_tip") if isinstance(recorded.get("source_tip"), dict) else {}
    for record, label in ((tip, "source chain tip"), (recorded, "recorded manifest")):
        if (
            record.get("chain_id") != CONTROLLED_CHAIN_ID
            or record.get("genesis_hash") != CONTROLLED_GENESIS_HASH
        ):
            raise ValueError(f"{label} is not the controlled chain")
    for label, want, have, noted in (
        ("height", expected_height, tip.get("height"), recorded_tip.get("height")),
        ("tip", expected_tip, tip.get("block_hash"), recorded_tip.get("block_hash")),
        ("root", expected_root, tip.get("state_root"), recorded_tip.get("state_root")),
    ):
        if want != have:
            raise ValueError(f"expected {label} does not match the source chain tip")
        if want != noted:
            raise ValueError(f"expected {label} does not match the recorded manifest")
    if output.exists():
        raise ValueError(f"refusing to overwrite output directory: {output}")
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("legacy source and output directory must be disjoint")

    source_tree_digest = tree_sha256(source)
    output.mkdir(parents=True)
    receipt_path = output / "receipts" / f"height-{expected_height}.json"
    receipt_path.parent.mkdir()
    redactor = (
        PathRedactor()
        .root("source", source)
        .root("output", output)
        .file("node-bin", node_bin)
        .file("recorded-manifest", recorded_manifest)
    )
    with tempfile.TemporaryDirectory(prefix="postfiat-legacy-replay-") as temporary:
        scratch = Path(temporary)
        redactor.root("scratch", scratch)
        reference = replay_source(
            node_bin=node_bin,
            source=source,
            height=expected_height,
            source_kind=REQUIRED_SOURCES[924],
            scratch=scratch,
            receipt_path=receipt_path,
            revision=revision,
            source_tree_digest=source_tree_digest,
            redactor=redactor,
        )
        clone = scratch / f"source-{expected_height}"
        target = scratch / f"transactional-{expected_height}"
        before = (tree_sha256(clone), tree_sha256(target))
        verified = run_json(
            [
                str(node_bin),
                "storage-rebuild-transactional",
                "--data-dir", str(clone),
                "--output-dir", str(target),
                "--expected-tip", expected_tip,
                "--expected-state-root", expected_root,
                "--verify-only",
                "--offline-confirmed",
            ]
        )
        after = (tree_sha256(clone), tree_sha256(target))
    if before != after:
        raise RuntimeError("scratch trees changed during the independent --verify-only")
    receipt = read_json(receipt_path)
    if (
        verified.get("verify_only") is not True
        or verified.get("published") is not False
        or verified.get("migration_packet_root") != receipt["migration_packet_root"]
    ):
        raise RuntimeError("independent --verify-only did not verify the rebuilt store")
    if (receipt["source_height"], receipt["tip_hash"], receipt["state_root"]) != (
        expected_height,
        expected_tip,
        expected_root,
    ):
        raise RuntimeError("replay identity differs from the expected values")
    for field in RECORDED_MANIFEST_FIELDS:
        if receipt.get(field) != recorded.get(field):
            raise RuntimeError(f"replay {field} differs from the recorded manifest")
    source_tree_after = tree_sha256(source)
    if source_tree_after != source_tree_digest:
        raise RuntimeError("legacy source changed during replay")

    verify_path = output / "verify-only.json"
    redactor.write(verify_path, verified)
    report = {
        "schema": "postfiat-storage-legacy-replay-v1",
        "verdict": "PASS",
        "source_height": expected_height,
        "tip_hash": expected_tip,
        "state_root": expected_root,
        "chain_id": receipt["chain_id"],
        "genesis_hash": receipt["genesis_hash"],
        "commitment_mode": receipt["commitment_mode"],
        "ordered_history_accumulator": receipt["ordered_history_accumulator"],
        "matched": {
            "chain": True,
            "height": True,
            "tip": True,
            "root": True,
            **{field: True for field in RECORDED_MANIFEST_FIELDS},
        },
        "recorded_manifest_sha256": sha256(recorded_manifest),
        "independent_verify_only": {
            "output": {"path": "verify-only.json", "sha256": sha256(verify_path)},
            "clone_tree_sha256_before": before[0],
            "clone_tree_sha256_after": after[0],
            "target_tree_sha256_before": before[1],
            "target_tree_sha256_after": after[1],
        },
        "receipts": [reference],
        "source_tree_sha256": source_tree_digest,
        "source_tree_sha256_after": source_tree_after,
        "source_revision": revision,
        "harness_revision": harness_revision,
        "node_binary_sha256": receipt["node_binary_sha256"],
        "node_binary_build": receipt["node_binary_build"],
        "offline": True,
        "network_contacted": False,
    }
    report_path = output / "replay-report.json"
    redactor.write(report_path, report)
    redactor.write_local_paths(output)
    return {"path": "replay-report.json", "sha256": sha256(report_path)}


def legacy_source_main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay one legacy pre-activation data directory offline."
    )
    parser.add_argument("--node-bin", type=Path, required=True)
    parser.add_argument("--legacy-source-dir", type=Path, required=True)
    parser.add_argument("--recorded-manifest", type=Path, required=True)
    parser.add_argument("--expected-height", type=int, required=True)
    parser.add_argument("--expected-tip", required=True)
    parser.add_argument("--expected-root", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-source-revision", required=True)
    args = parser.parse_args()

    paths = (
        args.node_bin.expanduser(),
        args.legacy_source_dir.expanduser(),
        args.recorded_manifest.expanduser(),
        args.output_dir.expanduser(),
    )
    if any(path.is_symlink() for path in paths):
        raise ValueError("binary, source, manifest and output paths must not be symlinks")
    node_bin, source, recorded, output = (path.resolve() for path in paths)
    if not node_bin.is_file() or node_bin.parent.name != "release":
        raise ValueError("--node-bin must identify a regular target/release binary")
    revision = args.expected_source_revision
    if len(revision) != 40 or subprocess.run(
        ["git", "merge-base", "--is-ancestor", revision, "HEAD"], cwd=REPO
    ).returncode != 0:
        raise ValueError("--expected-source-revision is not an ancestor of HEAD")
    if not git_clean():
        raise ValueError("replay evidence requires a clean checkout")
    reference = legacy_source_replay(
        node_bin=node_bin,
        source=source,
        expected_height=args.expected_height,
        expected_tip=args.expected_tip,
        expected_root=args.expected_root,
        recorded_manifest=recorded,
        output=output,
        revision=revision,
        harness_revision=git_revision(),
    )
    print("storage-legacy-replay=PASS")
    print(f"report={output / reference['path']}")
    print(f"report_sha256={reference['sha256']}")
    return 0


if __name__ == "__main__":
    if "--signed-archive-dir" in sys.argv[1:]:
        raise SystemExit(signed_archive_main())
    if "--legacy-source-dir" in sys.argv[1:]:
        raise SystemExit(legacy_source_main())
    raise SystemExit(main())
