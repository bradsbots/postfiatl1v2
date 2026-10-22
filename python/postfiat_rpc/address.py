"""PFTL account address parsing and checksummed display.

The canonical address is ``pf`` + 40 lowercase hex characters; it is the only
form used on chain and in signed transactions.

The optional checksum (spec: ``docs/wallets/address-format.md``)::

    h = SHA3-256("postfiat.address.checksum.v1" || 0x00 || lowercase 40-hex)
    hex character i is uppercased when it is a letter a-f and nibble i of h
    (high nibble of h[i // 2] for even i, low nibble for odd i) is >= 8

:func:`parse_address` accepts the all-lowercase form and the exact checksummed
form and returns the canonical form. This mirrors
``crates/crypto_provider/src/address.rs`` and the published vectors in
``docs/fixtures/addresses/pftl-address-vectors-v1.json``.
"""

from __future__ import annotations

import hashlib
import string

ADDRESS_PREFIX = "pf"
ADDRESS_HEX_LEN = 40
ADDRESS_LEN = 42
ADDRESS_CHECKSUM_DOMAIN = "postfiat.address.checksum.v1"

_MESSAGES = {
    "missing_prefix": "address must start with `pf`",
    "uppercase_prefix": "address prefix must be lowercase `pf`",
    "wrong_length": "address must be `pf` followed by exactly 40 hex characters",
    "non_hex": "address must be `pf` followed by 40 hex characters (0-9, a-f)",
    "bad_checksum": (
        "address checksum does not match; use the all-lowercase form or the exact "
        "checksummed form"
    ),
}
_HEX_DIGITS = frozenset(string.hexdigits)


class AddressError(ValueError):
    """Raised for an address that is malformed or has a wrong checksum."""

    def __init__(self, reason: str) -> None:
        super().__init__(_MESSAGES.get(reason, reason))
        self.reason = reason
        self.malformed = reason != "bad_checksum"


def _checksum_hex(lowercase_hex: str) -> str:
    digest = hashlib.sha3_256(
        ADDRESS_CHECKSUM_DOMAIN.encode("ascii") + b"\x00" + lowercase_hex.encode("ascii")
    ).digest()
    out = []
    for index, character in enumerate(lowercase_hex):
        byte = digest[index // 2]
        nibble = byte >> 4 if index % 2 == 0 else byte & 0x0F
        out.append(character.upper() if character in "abcdef" and nibble >= 8 else character)
    return "".join(out)


def _hex_part(value: object) -> str:
    if not isinstance(value, str) or len(value) < 2:
        raise AddressError("missing_prefix")
    prefix = value[:2]
    if prefix != ADDRESS_PREFIX:
        raise AddressError("uppercase_prefix" if prefix.lower() == ADDRESS_PREFIX else "missing_prefix")
    # Non-ASCII input is rejected before the length check so the reason does
    # not depend on how an implementation counts string length.
    if not value.isascii():
        raise AddressError("non_hex")
    if len(value) != ADDRESS_LEN:
        raise AddressError("wrong_length")
    hex_part = value[2:]
    if not all(character in _HEX_DIGITS for character in hex_part):
        raise AddressError("non_hex")
    return hex_part


def parse_address(value: object) -> str:
    """Return the canonical lowercase address for lowercase or checksummed input.

    Does not trim whitespace; trim pasted text first.
    """

    hex_part = _hex_part(value)
    lowercase = hex_part.lower()
    if hex_part != lowercase and _checksum_hex(lowercase) != hex_part:
        raise AddressError("bad_checksum")
    return ADDRESS_PREFIX + lowercase


def is_canonical_address(value: object) -> bool:
    """True only for ``pf`` + 40 lowercase hex characters."""

    try:
        return parse_address(value) == value
    except AddressError:
        return False


def checksum_address(value: object) -> str:
    """Return the checksummed display form of an accepted address."""

    canonical = parse_address(value)
    return ADDRESS_PREFIX + _checksum_hex(canonical[2:])


def display_address(value: object) -> object:
    """Checksummed form when ``value`` is an accepted address, else unchanged."""

    try:
        return checksum_address(value)
    except AddressError:
        return value
