"""Single-object *_info reads are bound to the object id that was requested.

Each case runs the real ``_call`` -> ``_unwrap_response`` path with only
``_send`` replaced, so the binding check sees exactly what the node would send.
"""

from __future__ import annotations

import copy
from typing import Any, Callable
from unittest import mock

import pytest

from postfiat_rpc import PostFiatRpcClient, PostFiatWebSocketRpcClient, RpcProtocolError

# (method, id field, object field); ids are 96 lowercase hex characters
# (crates/types/src/core_chain.rs *_ID_HEX_LEN).
KINDS = [
    ("asset_info", "asset_id", "asset"),
    ("escrow_info", "escrow_id", "escrow"),
    ("nft_info", "nft_id", "nft"),
    ("offer_info", "offer_id", "offer"),
]
REQUESTED = "ab" * 48
OTHER = "cd" * 48

Shape = Callable[[str, str], dict[str, Any]]


def _found(id_field: str, object_field: str) -> dict[str, Any]:
    return {
        "schema": f"postfiat-{object_field}-info-v1",
        id_field: REQUESTED,
        "found": True,
        object_field: {id_field: REQUESTED, "owner": "pf-owner"},
    }


def _not_found(id_field: str, object_field: str) -> dict[str, Any]:
    return {
        "schema": f"postfiat-{object_field}-info-v1",
        id_field: REQUESTED,
        "found": False,
        object_field: None,
    }


def _with(base: Shape, mutate: Callable[[dict[str, Any], str, str], None]) -> Shape:
    def shape(id_field: str, object_field: str) -> dict[str, Any]:
        result = base(id_field, object_field)
        mutate(result, id_field, object_field)
        return result

    return shape


def _set(key: str, value: Any) -> Callable[[dict[str, Any], str, str], None]:
    def mutate(result: dict[str, Any], id_field: str, object_field: str) -> None:
        field = {"<id>": id_field, "<obj>": object_field}.get(key, key)
        result[field] = copy.deepcopy(value)

    return mutate


def _drop(key: str) -> Callable[[dict[str, Any], str, str], None]:
    def mutate(result: dict[str, Any], id_field: str, object_field: str) -> None:
        del result[{"<id>": id_field, "<obj>": object_field}.get(key, key)]

    return mutate


def _set_inner(value: Any, *, drop: bool = False) -> Callable[[dict[str, Any], str, str], None]:
    def mutate(result: dict[str, Any], id_field: str, object_field: str) -> None:
        if drop:
            del result[object_field][id_field]
        else:
            result[object_field][id_field] = value

    return mutate


def _extra(result: dict[str, Any], id_field: str, object_field: str) -> None:
    result["future_field"] = {"nested": [1, 2, 3]}
    if result[object_field] is not None:
        result[object_field]["future_inner_field"] = "x"


ACCEPT: dict[str, Shape] = {
    "found_matching_object": _found,
    "not_found_null_object": _not_found,
    "found_with_unknown_fields": _with(_found, _extra),
    "not_found_with_unknown_fields": _with(_not_found, _extra),
}

REFUSE: dict[str, tuple[Shape, str]] = {
    "echo_of_another_id": (_with(_found, _set("<id>", OTHER)), "<id> does not match"),
    "echo_of_another_id_not_found": (_with(_not_found, _set("<id>", OTHER)), "<id> does not match"),
    "echo_absent": (_with(_found, _drop("<id>")), "<id> does not match"),
    "echo_null": (_with(_found, _set("<id>", None)), "<id> does not match"),
    "echo_int": (_with(_found, _set("<id>", 1)), "<id> does not match"),
    "echo_list": (_with(_found, _set("<id>", [REQUESTED])), "<id> does not match"),
    "echo_uppercase": (_with(_found, _set("<id>", REQUESTED.upper())), "<id> does not match"),
    "echo_padded": (_with(_found, _set("<id>", REQUESTED + " ")), "<id> does not match"),
    "echo_prefix_only": (_with(_found, _set("<id>", REQUESTED[:-2])), "<id> does not match"),
    "inner_object_of_another_id": (_with(_found, _set_inner(OTHER)), "<obj>.<id> does not match"),
    "inner_id_absent": (_with(_found, _set_inner(None, drop=True)), "<obj>.<id> does not match"),
    "inner_id_null": (_with(_found, _set_inner(None)), "<obj>.<id> does not match"),
    "inner_id_int": (_with(_found, _set_inner(7)), "<obj>.<id> does not match"),
    "inner_id_uppercase": (_with(_found, _set_inner(REQUESTED.upper())), "<obj>.<id> does not match"),
    "found_false_with_object": (_with(_found, _set("found", False)), "<obj> must be null"),
    "found_false_with_empty_object": (
        _with(_not_found, _set("<obj>", {})),
        "<obj> must be null",
    ),
    "found_false_with_false_object": (
        _with(_not_found, _set("<obj>", False)),
        "<obj> must be null",
    ),
    "found_true_with_null_object": (_with(_found, _set("<obj>", None)), "<obj> must be an object"),
    "found_true_with_list_object": (_with(_found, _set("<obj>", [])), "<obj> must be an object"),
    "found_true_with_str_object": (_with(_found, _set("<obj>", "x")), "<obj> must be an object"),
    "found_absent": (_with(_found, _drop("found")), "found must be a boolean"),
    "found_null": (_with(_found, _set("found", None)), "found must be a boolean"),
    "found_str_yes": (_with(_found, _set("found", "yes")), "found must be a boolean"),
    "found_int_1": (_with(_found, _set("found", 1)), "found must be a boolean"),
    "found_int_0": (_with(_not_found, _set("found", 0)), "found must be a boolean"),
    "found_float": (_with(_found, _set("found", 1.0)), "found must be a boolean"),
    "object_key_absent_found_true": (_with(_found, _drop("<obj>")), "<obj> is missing"),
    "object_key_absent_found_false": (_with(_not_found, _drop("<obj>")), "<obj> is missing"),
    "result_list": (lambda _i, _o: [], "result must be an object"),
    "result_null": (lambda _i, _o: None, "result must be an object"),
}


def _run(client: PostFiatRpcClient, method: str, result: Any) -> tuple[Any, dict[str, Any]]:
    def respond(request: dict[str, Any]) -> dict[str, Any]:
        return {
            "version": "postfiat-local-rpc-v1",
            "id": request["id"],
            "ok": True,
            "result": result,
        }

    with mock.patch.object(client, "_send", side_effect=respond) as send:
        returned = getattr(client, method)(REQUESTED)
    return returned, send.call_args.args[0]


@pytest.mark.parametrize("label", list(ACCEPT))
@pytest.mark.parametrize("method,id_field,object_field", KINDS)
def test_info_read_accepts_a_result_bound_to_the_requested_id(
    method: str, id_field: str, object_field: str, label: str
) -> None:
    result = ACCEPT[label](id_field, object_field)
    returned, request = _run(PostFiatRpcClient("127.0.0.1:1234"), method, result)
    assert returned == result
    assert request["method"] == method
    assert request["params"] == {id_field: REQUESTED}


@pytest.mark.parametrize("label", list(REFUSE))
@pytest.mark.parametrize("method,id_field,object_field", KINDS)
def test_info_read_refuses_a_result_not_bound_to_the_requested_id(
    method: str, id_field: str, object_field: str, label: str
) -> None:
    shape, reason = REFUSE[label]
    reason = reason.replace("<obj>", object_field).replace("<id>", id_field)
    with pytest.raises(RpcProtocolError) as raised:
        _run(PostFiatRpcClient("127.0.0.1:1234"), method, shape(id_field, object_field))
    assert str(raised.value).startswith(f"{method} ")
    assert reason in str(raised.value)


@pytest.mark.parametrize("method,id_field,object_field", KINDS)
def test_websocket_client_inherits_the_binding(
    method: str, id_field: str, object_field: str
) -> None:
    client = PostFiatWebSocketRpcClient("ws://127.0.0.1:1234")
    result = _found(id_field, object_field)
    returned, _request = _run(client, method, result)
    assert returned == result
    foreign = _with(_found, _set_inner(OTHER))(id_field, object_field)
    with pytest.raises(RpcProtocolError, match=rf"^{method} {object_field}\.{id_field} does not match"):
        _run(client, method, foreign)
