from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from postfiat_rpc.address import (
    ADDRESS_CHECKSUM_DOMAIN,
    AddressError,
    checksum_address,
    display_address,
    is_canonical_address,
    parse_address,
)

VECTORS = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "fixtures"
        / "addresses"
        / "pftl-address-vectors-v1.json"
    ).read_text(encoding="utf-8")
)


def test_vectors_declare_the_checksum_domain() -> None:
    assert VECTORS["schema"] == "postfiat.address_vectors.v1"
    assert VECTORS["checksum_domain"] == ADDRESS_CHECKSUM_DOMAIN


@pytest.mark.parametrize("vector", VECTORS["valid"], ids=lambda vector: vector["canonical"])
def test_valid_vectors_parse_and_checksum(vector: dict[str, str]) -> None:
    canonical = vector["canonical"]
    checksummed = vector["checksummed"]
    assert is_canonical_address(canonical)
    assert parse_address(canonical) == canonical
    assert parse_address(checksummed) == canonical
    assert checksum_address(canonical) == checksummed
    assert checksum_address(checksummed) == checksummed
    assert display_address(canonical) == checksummed
    assert checksummed.lower() == canonical


@pytest.mark.parametrize("vector", VECTORS["invalid_checksum"], ids=lambda vector: vector["input"])
def test_invalid_checksum_vectors_raise_a_checksum_error(vector: dict[str, str]) -> None:
    with pytest.raises(AddressError) as raised:
        parse_address(vector["input"])
    assert raised.value.reason == "bad_checksum"
    assert raised.value.malformed is False
    assert not is_canonical_address(vector["input"])


@pytest.mark.parametrize("vector", VECTORS["malformed"], ids=lambda vector: vector["description"])
def test_malformed_vectors_raise_their_reason(vector: dict[str, str]) -> None:
    with pytest.raises(AddressError) as raised:
        parse_address(vector["input"])
    assert raised.value.reason == vector["reason"]
    assert raised.value.malformed is True
    assert display_address(vector["input"]) == vector["input"]


def test_checksum_algorithm_matches_the_spec_formula() -> None:
    hex_part = "0123456789abcdef0123456789abcdef01234567"
    digest = hashlib.sha3_256(b"postfiat.address.checksum.v1\x00" + hex_part.encode()).digest()
    expected = "".join(
        character.upper()
        if character.isalpha() and (digest[index // 2] >> (4 * (1 - index % 2))) & 0xF >= 8
        else character
        for index, character in enumerate(hex_part)
    )
    assert checksum_address("pf" + hex_part) == "pf" + expected


def test_non_string_input_is_rejected() -> None:
    for value in [None, 42, b"pf" + b"0" * 40]:
        with pytest.raises(AddressError):
            parse_address(value)
