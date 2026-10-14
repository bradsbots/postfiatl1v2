"""Offline application-session regressions using the actual client and a wire adapter.

Only the optional websockets dependency's connect boundary is replaced. These
tests do not establish RFC6455 or live proxy interoperability.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest import mock


SOURCE = Path(os.environ.get("POSTFIAT_WS_SOURCE", Path(__file__).parents[1] / "postfiat_rpc/client.py"))
SPEC = importlib.util.spec_from_file_location("_websocket_session_client", SOURCE)
CLIENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CLIENT
SPEC.loader.exec_module(CLIENT)

ID_A = "independent-ws-A-101"
ID_B = "independent-ws-B-202"
ID_C = "independent-ws-C-404"
FOREIGN_ID = "independent-ws-foreign-303"
ENDPOINT = "ws://127.0.0.1:1/inert-test-adapter"
OBSERVATIONS = []


def reply(request_id, method, origin):
    return {
        "version": "postfiat-local-rpc-v1", "id": request_id, "ok": True,
        "result": {"method": method, "origin": origin, "request_id": request_id},
        "error": None, "events": [],
    }


FIRST = reply(ID_A, "status", "generation-1")
STALE = reply(ID_B, "server_info", "stale-generation-1")
CLEAN = reply(ID_B, "server_info", "clean-generation-2")
VALID_B = reply(ID_B, "server_info", "valid-generation-1")
VALID_C = reply(ID_C, "status", "valid-generation-1")
WRONG_ID = {**FIRST, "id": FOREIGN_ID}
WRONG_VERSION = {**FIRST, "version": "postfiat-local-rpc-v0"}
MISSING_RESULT = {key: value for key, value in FIRST.items() if key != "result"}
OVER_CAP = {**FIRST, "result": {"padding": "x" * 1000}}
BOUND_ERROR = {"code": "synthetic_rpc_error", "message": "inert bound refusal", "detail": {"source": "generation-1"}}
FAULTS = (
    ("wrong_response_id", WRONG_ID, "_call", "response id mismatch", None),
    ("wrong_response_version", WRONG_VERSION, "_call", "response version mismatch", None),
    ("malformed_json", "{", "_call", "response was not valid JSON:", None),
    ("array_envelope", "[]", "_call", "response envelope must be an object", None),
    ("null_envelope", "null", "_call", "response envelope must be an object", None),
    ("invalid_utf8", b"\xff", "_call", None, None),
    ("application_byte_cap", OVER_CAP, "_call", "response exceeded byte cap 1024", None),
    ("missing_success_result", MISSING_RESULT, "_call", "response missing result", None),
    ("receive_keyboard_interrupt", KeyboardInterrupt("inert interrupt A"), "_call", "inert interrupt A", None),
    ("call_response_wrong_id", WRONG_ID, "call_response", "response id mismatch", None),
    ("receive_timeout", TimeoutError("inert timeout A"), "_call", "WebSocket RPC timeout: status", None),
    ("send_os_error", None, "_call", "WebSocket RPC failed: inert send A", OSError("inert send A")),
    ("receive_os_error", OSError("inert recv A"), "_call", "WebSocket RPC failed: inert recv A", None),
)


def encoded(value):
    return json.dumps(value, separators=(",", ":")) if isinstance(value, dict) else value


def record(name, **values):
    observation = {"case": name, **values}
    OBSERVATIONS.append(observation)
    print("SESSION_OBSERVATION " + json.dumps(observation, sort_keys=True), flush=True)


class ScriptedSocket:
    def __init__(self, replies, *, send_error=None):
        self.replies = list(replies)
        self.send_error = send_error
        self.sent = []
        self.received = 0
        self.close_calls = 0
        self.detached_at_close = []
        self.client = None
        self.on_send = None
        self.close_error = None

    def send(self, wire):
        request = json.loads(wire)
        self.sent.append(request)
        if self.on_send:
            self.on_send(request)
        if self.send_error is not None:
            raise self.send_error

    def recv(self, *, timeout):
        self.received += 1
        value = self.replies.pop(0)
        if isinstance(value, BaseException):
            raise value
        return encoded(value)

    def close(self):
        self.close_calls += 1
        self.detached_at_close.append(self.client._websocket is None)
        if self.close_error is not None:
            raise self.close_error


class WebSocketSessionTests(unittest.TestCase):
    def connect_adapter(self, *sockets):
        client = CLIENT.PostFiatWebSocketRpcClient(ENDPOINT, response_byte_cap=1024)
        for socket in sockets:
            socket.client = client
        connections = []

        def connect(url, **kwargs):
            self.assertEqual(url, ENDPOINT)
            self.assertEqual(kwargs["max_size"], 1024)
            self.assertIsNone(kwargs["proxy"])
            socket = sockets[len(connections)]
            connections.append(socket)
            return socket

        modules = {name: types.ModuleType(name) for name in ("websockets", "websockets.sync", "websockets.sync.client")}
        modules["websockets.sync.client"].connect = connect
        dependency_patch = mock.patch.dict(sys.modules, modules)
        dependency_patch.start()
        self.addCleanup(dependency_patch.stop)
        self.addCleanup(client.close)
        return client, connections

    def run_fault(self, name, fault, entry, message, send_error):
        old = ScriptedSocket([fault, STALE] if send_error is None else [STALE], send_error=send_error)
        fresh = ScriptedSocket([CLEAN])
        client, connections = self.connect_adapter(old, fresh)
        error = None
        returned = None
        try:
            returned = getattr(client, entry)("status", {}, request_id=ID_A)
        except BaseException as caught:
            error = caught
        detached = client._websocket is None
        old_retained = client._websocket is old
        close_calls = old.close_calls
        next_result = client._call("server_info", {}, request_id=ID_B)
        generation = connections.index(client._websocket) + 1
        record(name, exception_class=type(error).__name__, exception_message=str(error),
               first_returned=returned, detached_at_error=detached, old_retained_at_error=old_retained,
               old_close_calls_at_error=close_calls, next_generation=generation, next_result=next_result,
               old_remaining_replies=len(old.replies), sent_ids=[[r["id"] for r in s.sent] for s in connections],
               detached_before_close=list(old.detached_at_close),
               original_interrupt_object=(error is fault) if isinstance(fault, KeyboardInterrupt) else None)
        self.assertIsNotNone(error)
        if name == "receive_keyboard_interrupt":
            self.assertIs(error, fault)
        elif name == "invalid_utf8":
            self.assertIsInstance(error, (UnicodeDecodeError, CLIENT.RpcProtocolError))
        else:
            self.assertIsInstance(error, CLIENT.RpcProtocolError)
        if message is not None:
            self.assertIn(message, str(error))
        self.assertIsNone(returned)
        self.assertTrue(detached)
        self.assertEqual(close_calls, 1)
        self.assertEqual(generation, 2)
        self.assertEqual(next_result, CLEAN["result"])
        self.assertEqual([r["id"] for r in old.sent], [ID_A])
        self.assertEqual([r["id"] for r in fresh.sent], [ID_B])
        self.assertEqual(old.replies, [STALE])

    def test_bound_rpc_error_reuse(self):
        refusal = {**FIRST, "ok": False, "result": None, "error": BOUND_ERROR}
        old = ScriptedSocket([refusal, VALID_B])
        client, connections = self.connect_adapter(old)
        with self.assertRaises(CLIENT.RpcError) as raised:
            client._call("status", {}, request_id=ID_A)
        retained = client._websocket is old
        close_calls = old.close_calls
        result = client._call("server_info", {}, request_id=ID_B)
        record("bound_rpc_error_reuse", exception_class=type(raised.exception).__name__,
               exception_method=raised.exception.method, exception_error=raised.exception.error,
               old_retained_at_error=retained, old_close_calls_at_error=close_calls,
               next_generation=len(connections), next_result=result)
        self.assertEqual(raised.exception.method, "status")
        self.assertEqual(raised.exception.error, BOUND_ERROR)
        self.assertTrue(retained)
        self.assertEqual(close_calls, 0)
        self.assertEqual(len(connections), 1)
        self.assertEqual(result, VALID_B["result"])

    def test_valid_sequential_reuse(self):
        old = ScriptedSocket([FIRST, VALID_B, VALID_C])
        client, connections = self.connect_adapter(old)
        values = [client._call("status", {}, request_id=ID_A),
                  client._call("server_info", {}, request_id=ID_B),
                  client.call_response("status", {}, request_id=ID_C)]
        record("valid_sequential_reuse", values=values, generations=[len(connections)] * 3,
               close_calls=old.close_calls, sent_ids=[r["id"] for r in old.sent],
               sent_methods=[r["method"] for r in old.sent])
        self.assertEqual(values, [FIRST["result"], VALID_B["result"], VALID_C])
        self.assertEqual(len(connections), 1)
        self.assertEqual(old.close_calls, 0)
        self.assertEqual([r["id"] for r in old.sent], [ID_A, ID_B, ID_C])
        self.assertEqual([r["method"] for r in old.sent], ["status", "server_info", "status"])

    def test_detach_before_close_failure(self):
        old = ScriptedSocket([FIRST])
        old.close_error = RuntimeError("inert close failure")
        client, _ = self.connect_adapter(old)
        client._call("status", {}, request_id=ID_A)
        client.close()
        record("detach_before_close_failure", detached=client._websocket is None,
               detached_before_close=list(old.detached_at_close), close_calls=old.close_calls)
        self.assertIsNone(client._websocket)
        self.assertEqual(old.detached_at_close, [True])

    def test_validation_serialization(self):
        old, fresh = ScriptedSocket([WRONG_ID, STALE]), ScriptedSocket([CLEAN])
        client, connections = self.connect_adapter(old, fresh)
        validation_entered, release_validation = threading.Event(), threading.Event()
        b_attempted, old_b_sent = threading.Event(), threading.Event()
        original_unwrap = client._unwrap_response
        original_send = client._send
        results, errors, error_detached = {}, {}, {}

        def gated_unwrap(method, request_id, response):
            if request_id == ID_A:
                validation_entered.set()
                if not release_validation.wait(3):
                    raise AssertionError("validator gate timed out")
            return original_unwrap(method, request_id, response)

        def observed_send(request):
            if request["id"] == ID_B:
                b_attempted.set()
            return original_send(request)

        old.on_send = lambda r: old_b_sent.set() if r["id"] == ID_B else None
        client._unwrap_response = gated_unwrap
        client._send = observed_send

        def run(label, method, request_id):
            try:
                results[label] = client._call(method, {}, request_id=request_id)
            except BaseException as error:
                errors[label] = error
                error_detached[label] = client._websocket is not old

        a = threading.Thread(target=run, args=("A", "status", ID_A), daemon=True)
        b = threading.Thread(target=run, args=("B", "server_info", ID_B), daemon=True)
        a.start()
        try:
            self.assertTrue(validation_entered.wait(3), "A did not reach actual validator")
            lock_held = client._send_lock.locked()
            b.start()
            self.assertTrue(b_attempted.wait(3), "B did not attempt actual sender")
            sent_before_release = old_b_sent.wait(0.25)
        finally:
            release_validation.set()
            a.join(3)
            if b.ident is not None:
                b.join(3)
        record("validation_serialization", validation_lock_held=lock_held,
               B_sent_on_old_before_A_release=sent_before_release,
               A_exception_class=type(errors.get("A")).__name__, A_old_session_detached_at_error=error_detached.get("A"),
               B_result=results.get("B"), B_exception_class=type(errors.get("B")).__name__,
               B_generation=connections.index(client._websocket) + 1 if client._websocket in connections else None,
               old_close_calls=old.close_calls, fresh_close_calls=fresh.close_calls,
               old_remaining_replies=len(old.replies), no_deadlock=not a.is_alive() and not b.is_alive())
        self.assertFalse(a.is_alive() or b.is_alive(), "bounded thread join failed")
        self.assertIsInstance(errors.get("A"), CLIENT.RpcProtocolError)
        self.assertNotIn("B", errors)
        self.assertTrue(lock_held)
        self.assertFalse(sent_before_release)
        self.assertTrue(error_detached["A"])
        self.assertEqual(results["B"], CLEAN["result"])
        self.assertIs(client._websocket, fresh)
        self.assertEqual(old.close_calls, 1)
        self.assertEqual(fresh.close_calls, 0)
        self.assertEqual(old.replies, [STALE])


def fault_test(case):
    def test(self):
        self.run_fault(*case)
    return test


for case in FAULTS:
    setattr(WebSocketSessionTests, "test_" + case[0], fault_test(case))


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    outcome = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(WebSocketSessionTests))
    report = {
        "mode": "stdlib unittest, inert scripted websockets.connect adapter; no sockets",
        "source": str(SOURCE.resolve()), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "python": sys.version, "cases": OBSERVATIONS, "tests_run": outcome.testsRun,
        "failures": len(outcome.failures), "errors": len(outcome.errors), "successful": outcome.wasSuccessful(),
    }
    if os.environ.get("POSTFIAT_WS_OBSERVATIONS"):
        Path(os.environ["POSTFIAT_WS_OBSERVATIONS"]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    sys.exit(0 if outcome.wasSuccessful() else 1)
