"""Inert actual-client regression for the two account collection read bindings.

The literal vectors were frozen independently before the correction or outputs.
Codex assisted this regression; no wallet, service or real transport is invoked.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys


ORACLE_SHA256 = "d2dc53e0d08924fbade01ba5faa8ebb8451ee757cb0a036c2d1185ee584c5919"
FIXTURE_SHA256 = "3bce1ddfa84b3d2d4b1d487ed3b76cee863e9b66af7538d8f6b7a3760bbcef92"


def _same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            _same(actual[key], value) for key, value in expected.items()
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            _same(a, e) for a, e in zip(actual, expected)
        )
    return actual == expected


def _expected(case, stage):
    response = case["adapter"].get("response")
    return {
        "id": case["id"], "method": case["method"],
        "arguments_before": case["arguments"], "arguments_after": case["arguments"],
        "response_before": response, "response_after": response,
        "send_calls": case["expected_send_calls"], "socket_attempts": 0,
        "observed": case["expected_" + stage],
    }


def run_probe(source=None, fixture_path=None, *, emit=False):
    source = Path(source or Path(__file__).parents[1] / "postfiat_rpc" / "client.py")
    fixture_path = Path(fixture_path or Path(__file__).parent / "fixtures" / "account_collection_binding_vectors.json")
    fixture_bytes = fixture_path.read_bytes()
    assert hashlib.sha256(fixture_bytes).hexdigest() == FIXTURE_SHA256
    fixture = json.loads(fixture_bytes)
    assert fixture["oracle_sha256"] == ORACLE_SHA256
    cases = fixture["cases"]
    assert len(cases) == 114 and len({case["id"] for case in cases}) == 114
    assert all(case["method"] in {"account_offers", "account_escrows"} for case in cases)
    assert all(case["adapter"]["kind"] in {"return", "raise"} for case in cases)
    assert all(case["adapter"].get("error_class", "OSError") == "OSError" for case in cases)

    attempts = [0]
    original_connection, original_socket = socket.create_connection, socket.socket

    def forbidden_socket(*args, **kwargs):
        attempts[0] += 1
        raise AssertionError("real socket transport is forbidden in collection regression")

    socket.create_connection = socket.socket = forbidden_socket
    module_name = "_postfiat_account_collection_binding_client"
    old_module = sys.modules.get(module_name)
    observations = []
    try:
        spec = importlib.util.spec_from_file_location(module_name, source)
        assert spec is not None and spec.loader is not None
        sdk = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = sdk
        spec.loader.exec_module(sdk)
        for case in cases:
            attempts_before = attempts[0]
            arguments = copy.deepcopy(case["arguments"])
            arguments_before = copy.deepcopy(arguments)
            response = copy.deepcopy(case["adapter"].get("response"))
            response_before = copy.deepcopy(response)
            response_result = response.get("result") if isinstance(response, dict) else None
            response_error = response.get("error") if isinstance(response, dict) else None
            collection_key = "offers" if case["method"] == "account_offers" else "escrows"
            collection = response_result.get(collection_key) if isinstance(response_result, dict) else None
            original_rows = list(collection) if isinstance(collection, list) else None
            send_calls = []
            client = sdk.PostFiatRpcClient(sdk.Endpoint("collection.invalid", 1))

            def inert_send(request):
                send_calls.append(copy.deepcopy(request))
                if case["adapter"]["kind"] == "raise":
                    raise OSError(case["adapter"]["message"])
                return response

            client._send = inert_send
            try:
                result = getattr(client, case["method"])(*arguments["args"], **arguments["kwargs"])
                result_collection = result.get(collection_key) if isinstance(result, dict) else None
                observed = {
                    "kind": "return", "value": copy.deepcopy(result), "value_type": type(result).__name__,
                    "same_response_result_object": result is response_result,
                    "same_collection_object": result_collection is collection if isinstance(collection, list) else None,
                    "same_row_objects": [i < len(original_rows) and row is original_rows[i] for i, row in enumerate(result_collection)]
                    if isinstance(result_collection, list) and original_rows is not None else None,
                }
            except Exception as error:
                rpc_error = isinstance(error, sdk.RpcError)
                observed = {
                    "kind": "error", "error_class": type(error).__name__, "message": str(error),
                    "rpc_method": error.method if rpc_error else None,
                    "rpc_error": copy.deepcopy(error.error) if rpc_error else None,
                    "same_rpc_error_object": error.error is response_error if rpc_error else None,
                }
            observation = {
                "id": case["id"], "method": case["method"],
                "arguments_before": arguments_before, "arguments_after": copy.deepcopy(arguments),
                "response_before": response_before, "response_after": copy.deepcopy(response),
                "send_calls": send_calls, "socket_attempts": attempts[0] - attempts_before,
                "observed": observed,
            }
            observations.append(observation)
            if emit:
                print(json.dumps({"observation": observation}, separators=(",", ":")), flush=True)
    finally:
        socket.create_connection, socket.socket = original_connection, original_socket
        if old_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = old_module

    summary = {
        "runtime": sys.version.split()[0], "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(), "oracle_sha256": ORACLE_SHA256,
        "observations": len(observations), "constructors": len(cases),
        "returns": sum(row["observed"]["kind"] == "return" for row in observations),
        "errors": sum(row["observed"]["kind"] == "error" for row in observations),
        "socket_attempts": attempts[0],
        "original_mismatches": [case["id"] for case, row in zip(cases, observations) if not _same(row, _expected(case, "original"))],
        "corrected_mismatches": [case["id"] for case, row in zip(cases, observations) if not _same(row, _expected(case, "corrected"))],
    }
    if emit:
        print(json.dumps({"summary": summary}, separators=(",", ":")), flush=True)
    return observations, summary


def test_account_collection_binding():
    _, summary = run_probe()
    assert summary["corrected_mismatches"] == []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source")
    parser.add_argument("--fixture")
    options = parser.parse_args()
    _, actual_summary = run_probe(options.source, options.fixture, emit=True)
    assert actual_summary["corrected_mismatches"] == [], actual_summary["corrected_mismatches"]
