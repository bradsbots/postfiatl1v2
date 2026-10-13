"""Unit tests for the Python-coverage detector of scripts/testnet-rpc-method-inventory.

The freshness test checks the committed artifacts against the generator; this
file checks the generator's own extractor against known wrapper shapes, so a
wrapper style the detector does not recognise fails here instead of silently
reporting python_client=false in the launch-surface map (or, worse, a literal
that is not a method name becoming a phantom inventory row).
"""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "scripts" / "testnet-rpc-method-inventory"
REAL_CLIENT = REPO / "python" / "postfiat_rpc" / "client.py"


def _load_generator():
    loader = importlib.machinery.SourceFileLoader("testnet_rpc_method_inventory_gen", str(GENERATOR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# Declared in the reverse of their forwarding order so that proving
# `_verification_report` requires `_object_read` to have been proven first.
HELPERS = '''
    def _verification_report(self, method: str) -> dict[str, Any]:
        return self._object_read(method, {})

    def _object_read(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        result = self._call(method, params)
        return result

    def _emit(self, event: str) -> None:
        pass
'''


def _module(body: str) -> str:
    """Wrap method bodies (indented as in client.py) into a parseable module."""
    return "from typing import Any\n\n\nclass Client:\n" + body + "\n"


class PythonClientDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = _load_generator()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _detect(self, body: str) -> set[str]:
        """Run the detector against `body` as the methods of a client.py class."""
        fake_client = Path(self._tmp.name) / "client.py"
        fake_client.write_text(_module(body), encoding="utf-8")
        self.generator.PY_CLIENT = fake_client
        return self.generator.extract_python_client_methods()

    def _helpers(self, body: str) -> set[str]:
        return self.generator.python_client_forwarding_helpers(ast.parse(_module(body)))

    def test_detects_single_line_transport_calls(self) -> None:
        body = '''
    def status(self) -> dict[str, Any]:
        return self._call("status")

    def blocks(self, limit: int) -> list[dict[str, Any]]:
        return self._call("blocks", self._limit_params(limit))
'''
        self.assertEqual(self._detect(body), {"status", "blocks"})

    def test_detects_transport_calls_with_the_literal_on_the_next_line(self) -> None:
        # black wraps the longer calls like this; client.py on main has 15 such
        # sites (mempool_submit_*, owned_sign*, navcoin_bridge_packet, ...).
        body = '''
    def submit_signed_transfer(self, signed_transfer_json: str) -> dict[str, Any]:
        result = self._call(
            "mempool_submit_signed_transfer",
            {"signed_transfer_json": signed_transfer_json},
        )
        return result
'''
        self.assertEqual(self._detect(body), {"mempool_submit_signed_transfer"})

    def test_detects_calls_routed_through_forwarding_helpers(self) -> None:
        body = HELPERS + '''
    def vault_bridge_status(self, asset_id: str) -> dict[str, Any]:
        return self._object_read(
            "vault_bridge_status", {"asset_id": self._required_text(asset_id, "asset_id")}
        )

    def nav_reserve_proof_status(self, asset_id: str) -> dict[str, Any]:
        return self._object_read("nav_reserve_proof_status", {"asset_id": asset_id})

    def verify_blocks(self) -> dict[str, Any]:
        return self._verification_report("verify_blocks")
'''
        self.assertEqual(self._helpers(body), {"_call", "_object_read", "_verification_report"})
        self.assertEqual(
            self._detect(body),
            {"vault_bridge_status", "nav_reserve_proof_status", "verify_blocks"},
        )

    def test_ignores_literals_handed_to_non_forwarding_helpers(self) -> None:
        # `_required_text` takes the value first, `_emit` takes an event name:
        # neither forwards a method, so "owner" and "started" must not appear.
        body = HELPERS + '''
    def shield_scan(self, owner: str) -> list[dict[str, Any]]:
        self._emit("started")
        return self._call("shield_scan", {"owner": self._required_text(owner, "owner")})

    def helper(self, value: str) -> str:
        return self._required_text(value, "value")
'''
        self.assertEqual(self._detect(body), {"shield_scan"})

    def test_ignores_literals_handed_to_a_typed_helper_that_does_not_forward(self) -> None:
        # A `method: str` parameter alone does not make a transport helper: this
        # one formats the name and never reaches `_call`, so "phantom_method"
        # must not become an inventory row.
        body = '''
    def _audit_label(self, method: str) -> str:
        return f"audit:{method}"

    def status(self) -> dict[str, Any]:
        self._audit_label("phantom_method")
        return self._call("status")
'''
        self.assertEqual(self._helpers(body), {"_call"})
        self.assertEqual(self._detect(body), {"status"})

    def test_ignores_a_typed_helper_that_calls_the_transport_with_its_own_literal(self) -> None:
        # The helper reaches `_call`, but with a fixed name rather than its
        # `method` parameter, so its callers' literals are not method names.
        body = '''
    def _probe(self, method: str) -> bool:
        return self._call("status").get(method) is not None

    def has_metrics(self) -> bool:
        return self._probe("phantom_method")
'''
        self.assertEqual(self._helpers(body), {"_call"})
        self.assertEqual(self._detect(body), {"status"})

    def test_exception_constructor_taking_a_method_is_not_a_helper(self) -> None:
        # client.py's RpcError.__init__(self, method: str, error) stores the
        # name; it is not a transport helper and must not be proven as one.
        body = '''
    def __init__(self, method: str, error: dict[str, Any]) -> None:
        self.method = method
        self.error = error

    def status(self) -> dict[str, Any]:
        return self._call("status")
'''
        self.assertEqual(self._helpers(body), {"_call"})
        self.assertEqual(self._detect(body), {"status"})

    def test_source_parameter_overrides_the_client_file(self) -> None:
        self.generator.PY_CLIENT = Path(self._tmp.name) / "does-not-exist.py"
        self.assertEqual(self.generator.extract_python_client_methods(), set())
        self.assertEqual(
            self.generator.extract_python_client_methods(_module('''
    def status(self) -> dict[str, Any]:
        return self._call("status")
''')),
            {"status"},
        )

    def test_real_client_detection_is_a_superset_of_the_single_line_form(self) -> None:
        source = REAL_CLIENT.read_text(encoding="utf-8")
        single_line = set(re.findall(r'self\._call\("([^"]+)"', source))
        self.generator.PY_CLIENT = REAL_CLIENT
        detected = self.generator.extract_python_client_methods()
        self.assertTrue(single_line, "expected single-line self._call(...) wrappers in client.py")
        self.assertEqual(single_line - detected, set())
        # The multi-line sites are the ones the single-line form misses.
        self.assertIn("mempool_submit_signed_transfer", detected)
        # Every proven helper in the real client forwards to the transport;
        # RpcError.__init__ takes a `method` and is not one of them.
        proven = self.generator.python_client_forwarding_helpers(ast.parse(source))
        self.assertIn("_call", proven)
        self.assertNotIn("__init__", proven)


if __name__ == "__main__":
    unittest.main()
