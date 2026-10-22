#!/usr/bin/env python3
"""Fail-closed controls for the retired-module build recovery; no network."""
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path

script = Path(__file__).with_name("pfusdc-tier4-prover-build")
loader = importlib.machinery.SourceFileLoader("public_build", str(script))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class RecoveryTests(unittest.TestCase):
    def test_corrupt_download_never_promoted(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                module.prepare_proxy(cache, lambda _: b"corrupt")
            self.assertEqual(list(cache.rglob("*.info")), [])

    def test_corrupt_existing_cache_is_not_trusted_or_silently_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            target = cache / module.MODULE / "@v" / f"{module.VERSION}.info"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                module.prepare_proxy(cache, lambda _: self.fail("unexpected network"))
            self.assertEqual(target.read_bytes(), b"corrupt")

    def test_build_retains_default_features_and_locked_resolution(self):
        root = script.parent.parent
        command = module.build_command(root, False)
        self.assertEqual(command[:2], ["cargo", "build"])
        self.assertEqual(command[-1], "--locked")
        self.assertNotIn("--no-default-features", command)
        self.assertEqual(module.build_command(root, True)[1], "test")

    def test_changed_sdk_stops_before_recovery_or_cargo(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "tools/pfusdc-tier4-prover/Cargo.toml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('[features]\ndefault=["sp1-native-gnark"]\n'
                                '[dependencies.sp1-sdk]\nversion="=6.8.1"\n')
            with self.assertRaisesRegex(ValueError, "SP1 version changed"):
                module.build_command(root, False)

    def test_changed_default_contract_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "tools/pfusdc-tier4-prover/Cargo.toml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('[features]\ndefault=[]\n')
            with self.assertRaisesRegex(ValueError, "feature contract changed"):
                module.build_command(root, False)


if __name__ == "__main__":
    unittest.main()
