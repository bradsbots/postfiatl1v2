from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from postfiat_rpc import wallet as wallet_module

REPO_ROOT = Path(__file__).resolve().parents[2]


def _package_binaries(crate_dir: str) -> set[str]:
    """Binary targets cargo sees in one workspace crate: src/main.rs + src/bin/*.rs + [[bin]]."""
    crate = REPO_ROOT / "crates" / crate_dir
    manifest = tomllib.loads((crate / "Cargo.toml").read_text(encoding="utf-8"))
    names = {entry["name"] for entry in manifest.get("bin", [])}
    if (crate / "src" / "main.rs").exists():
        names.add(manifest["package"]["name"])
    names.update(path.stem for path in (crate / "src" / "bin").glob("*.rs"))
    return names


class WalletCargoFallbackTests(unittest.TestCase):
    """Without <repo>/target/debug binaries the wallet falls back to `cargo run`.

    Both packages have more than one binary target, so the fallback must name
    the binary or cargo refuses with "could not determine which binary to run".
    """

    def test_fallbacks_name_the_binary_cargo_must_run(self) -> None:
        with tempfile.TemporaryDirectory() as empty_root:
            with mock.patch.object(wallet_module, "REPO_ROOT", Path(empty_root)):
                node = wallet_module._node_bin()
                sdk = wallet_module._sdk_bin()
        self.assertEqual(
            node, ["cargo", "run", "-p", "postfiat-node", "--bin", "postfiat-node", "--"]
        )
        self.assertEqual(
            sdk, ["cargo", "run", "-p", "postfiat-rpc-sdk", "--bin", "postfiat-rpc-sdk", "--"]
        )

    def test_both_packages_have_several_binaries(self) -> None:
        node_bins = _package_binaries("node")
        sdk_bins = _package_binaries("rpc_sdk")
        self.assertIn("postfiat-node", node_bins)
        self.assertIn("postfiat-rpc-sdk", sdk_bins)
        self.assertGreater(len(node_bins), 1)
        self.assertGreater(len(sdk_bins), 1)

    def test_built_binary_is_still_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            debug = Path(root) / "target" / "debug"
            debug.mkdir(parents=True)
            (debug / "postfiat-node").write_text("", encoding="utf-8")
            (debug / "postfiat-rpc-sdk").write_text("", encoding="utf-8")
            with mock.patch.object(wallet_module, "REPO_ROOT", Path(root)):
                self.assertEqual(wallet_module._node_bin(), [str(debug / "postfiat-node")])
                self.assertEqual(wallet_module._sdk_bin(), [str(debug / "postfiat-rpc-sdk")])


if __name__ == "__main__":
    unittest.main()
