"""Deterministic sub-scorers v3 for the Dynamic UNL shadow evaluation.

Versioned FORMULA-style: ``SUBSCORER_VERSION = 3``. This is the module
frozen for the Z2 shadow window
(``docs/plans/active/z2-advisory-flag-execution-plan-20261022.md`` step 1a):
its SHA-256 over these exact bytes is the recorded content hash, and any
byte change restarts the counted rounds. v1 (``subscorer.py``) and v2
(``subscorer_v2.py``) stay unchanged and reproducible. Like v2 it is
self-contained, so the hash covers every rule it applies; frozen-input
extraction stays in ``subscorer.py`` and is not a scoring rule.

v3 is v2 reconciled to the ``dynamic-unl-scoring`` fork's current rules
(fork ``main`` ``e70515d``, prompt v12). Nothing else changes:

1. **Minimum safe version** (fork ``d85a3e9``, 2026-09-21, prompt v11+):
   a validator whose frozen entry carries ``fails_minimum_safe_version:
   true`` scores software 0. The verdict is the collector's
   (``collector.py`` ``check_minimum_safe_version``) and is taken as given;
   it touches no other dimension, and a false or absent value has no
   effect, exactly as prompt v12 states.
2. **Diversity formula v1** (fork ``ffe7582``, 2026-10-09): the fork owns
   diversity in code (``diversity_formula.py``, pinned in every round
   manifest as ``code.diversity_formula``). v3 therefore scores only the
   four dimensions the model still supplies; the v2 band matrix is
   retired. The shadow comparison takes diversity unchanged from the
   round's pinned formula (or, for rounds that predate it, from the
   published model value that the round's selection used).
3. **25 testnet seats** (fork ``5f65bdf``, 2026-09-24): no sub-score rule
   reads the seat count (prompt v12 uses it only for the network report),
   so no v3 rule changes. The seat count enters the comparison only
   through each round's pinned ``code.selector.parameters.max_size``.

CONSENSUS (era-aware, unchanged from v2):
    era >= 8 (prompt v8+): floor(100 * min(1h, 24h, 30d)).
    era < 8 (prompt v5/v6): 10 if 1h < 0.5, else floor(100 * 30d).
    A null/missing window counts as 0.0. Exact decimal floor via Fraction.

RELIABILITY (unchanged from v2; null window -> 0.0):
    c1 < 0.5                          -> 10
    else if c1 < 0.999 or c24 < 0.999 -> m = min(c1, c24):
        m >= 0.99 -> 65;  m >= 0.95 -> 55;  m >= 0.9 -> 50;  else -> 40
    else -> c30 >= 0.9995 -> 100;  >= 0.999 -> 95;  >= 0.995 -> 90;
            >= 0.99 -> 85;  >= 0.95 -> 80;  else -> 75

SOFTWARE:
    fails_minimum_safe_version true -> 0 (new in v3);
    otherwise v2's ordering against the round's own set: latest -> 100;
    same major.minor -> 80; same major -> 60; older major -> 40;
    missing/unparsable -> 50.

IDENTITY (unchanged from v2):
    domain_verified -> 80; domain unverified -> 55; no domain -> 45.

Read but neutral, as in v2: ``incomplete`` window flags (scored at face
value, which prompt v12 also requires), fee votes, and the formal
``identity`` field.

Integer 0-100 outputs, deterministic, no network, no model.
"""

from __future__ import annotations

import re
from fractions import Fraction

SUBSCORER_VERSION = 3

# The four dimensions the model still supplies under prompt v12; the
# fork's diversity formula owns the fifth.
DIMENSIONS = ("consensus", "reliability", "software", "identity")

WORST_WINDOW_ERA_FIRST_PROMPT = 8

MINIMUM_SAFE_VERSION_FAILURE_SOFTWARE = 0

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_PROMPT_VERSION_RE = re.compile(r"^v(\d+)$")

_CLEAN = 0.999


def prompt_era(prompt_version: str) -> int:
    """Parse a round's prompt version (``"v5"`` .. ``"v12"``) to its era."""
    match = _PROMPT_VERSION_RE.match(prompt_version.strip())
    if match is None:
        raise ValueError(f"unrecognized prompt version {prompt_version!r}")
    return int(match.group(1))


def _window_score(entry: dict, window: str) -> float:
    data = entry.get(f"agreement_{window}")
    if not data or data.get("score") is None:
        return 0.0
    return float(data["score"])


def _floor_100(score: float) -> int:
    return int(Fraction(str(score)) * 100)


def score_consensus(entry: dict, era: int) -> int:
    if era >= WORST_WINDOW_ERA_FIRST_PROMPT:
        return _floor_100(min(_window_score(entry, w) for w in ("1h", "24h", "30d")))
    if _window_score(entry, "1h") < 0.5:
        return 10
    return _floor_100(_window_score(entry, "30d"))


def score_reliability(entry: dict) -> int:
    c1 = _window_score(entry, "1h")
    c24 = _window_score(entry, "24h")
    c30 = _window_score(entry, "30d")
    if c1 < 0.5:
        return 10
    if c1 < _CLEAN or c24 < _CLEAN:
        m = min(c1, c24)
        for threshold, score in ((0.99, 65), (0.95, 55), (0.9, 50)):
            if m >= threshold:
                return score
        return 40
    for threshold, score in (
        (0.9995, 100), (0.999, 95), (0.995, 90), (0.99, 85), (0.95, 80),
    ):
        if c30 >= threshold:
            return score
    return 75


def _parse_version(version: object) -> tuple[int, int, int] | None:
    if not isinstance(version, str):
        return None
    match = _VERSION_RE.match(version.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def score_software(entry: dict, newest: tuple[int, int, int] | None) -> int:
    if entry.get("fails_minimum_safe_version") is True:
        return MINIMUM_SAFE_VERSION_FAILURE_SOFTWARE
    version = _parse_version(entry.get("server_version"))
    if version is None or newest is None:
        return 50
    if version >= newest:
        return 100
    if version[:2] == newest[:2]:
        return 80
    if version[0] == newest[0]:
        return 60
    return 40


def score_identity(entry: dict) -> int:
    if entry.get("domain_verified"):
        return 80
    if entry.get("domain"):
        return 55
    return 45


def score_round(entries: list[dict], prompt_version: str) -> dict[str, dict[str, int]]:
    """Score every validator of a round under the round's own prompt era.

    Returns ``{validator_id: {dimension: int}}`` over ``DIMENSIONS``.
    ``prompt_version`` is the round's frozen ``code.prompt.version``; it
    selects the consensus era and nothing else.
    """
    era = prompt_era(prompt_version)
    newest = max(
        (v for v in (_parse_version(e.get("server_version")) for e in entries) if v),
        default=None,
    )
    return {
        entry["validator_id"]: {
            "consensus": score_consensus(entry, era),
            "reliability": score_reliability(entry),
            "software": score_software(entry, newest),
            "identity": score_identity(entry),
        }
        for entry in entries
    }
