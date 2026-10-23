"""Python mirror of the strict entry profile rule module (Z2 step 3).

Independent implementation of ``crates/consensus_cobalt/src/validator_entry_profile.rs``.
It shares no code with the Rust module and must produce byte-identical
canonical JSON on every shared fixture in
``benchmarks/ai-governance/validator-entry-profile-20261023/fixtures/``.

The rules follow the locked
``docs/specs/identity-flag-pipeline-spec-20261023.md`` (sections 3, 4 and 7):

- ``meets_strict_profile`` is a pure function that never reads a flag.
  Under ``entry_profile_v1`` it needs a verified domain and at least
  ``required_clean_rounds`` consecutive clean rounds ending at the round before
  the current one. Under ``interim_domain_only`` it needs a verified domain.
- A round is clean for an operator when it is present in that round's frozen
  final scores, its domain was verified, and its final score is at or above the
  round's cutoff. This is the proposed default, pending its decision line.
- ``identity_flag`` is ``flag`` only when an admissible model classification is
  ``flag`` and the strict profile is not met; otherwise ``clear``.
- ``resolve_flag_input`` returns ``none`` for a missing artifact, a wrong schema,
  a non-shadow artifact, a pin mismatch, an absent or duplicated operator, or an
  unknown flag value.
- A flag input of ``none`` or ``clear`` selects the standard profile, and ``flag``
  selects the strict one. A flag never removes an incumbent and only withholds a
  new seat.

Everything here is ``SHADOW_ONLY``: no consensus path calls it.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "postfiat.validator_entry_profile.v1"
DECISION_SCHEMA = "postfiat.validator_entry_profile.decision.v1"
FLAGS_SCHEMA = "postfiat.identity_flag.v1"
VERSION = 1
RULES = ("entry_profile_v1", "interim_domain_only")
FLAG_INPUTS = ("none", "clear", "flag")
MODEL_CLASSIFICATIONS = ("none", "clear", "flag")

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FLAG_REASONS = {
    "none": "no_flag_input_standard_profile",
    "clear": "flag_clear_standard_profile",
    "flag": "flag_selects_strict_profile",
}


class EntryProfileError(ValueError):
    """An input the module refuses; the message is a stable error code."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _uint(value: Any, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 2**64 - 1:
        raise EntryProfileError(code)
    return value


def _bool(value: Any, code: str) -> bool:
    if not isinstance(value, bool):
        raise EntryProfileError(code)
    return value


def validate_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    if parameters.get("schema") != "postfiat.validator_entry_profile.parameters.v1":
        raise EntryProfileError("parameters_schema_unsupported")
    required = _uint(parameters.get("required_clean_rounds"), "parameters_required_clean_rounds_invalid")
    if required < 1:
        raise EntryProfileError("parameters_required_clean_rounds_invalid")
    if parameters.get("require_verified_domain") is not True:
        raise EntryProfileError("parameters_require_verified_domain_must_be_true")
    rule = parameters.get("strict_profile_rule")
    if rule not in RULES:
        raise EntryProfileError("parameters_strict_profile_rule_unsupported")
    return {
        "required_clean_rounds": required,
        "require_verified_domain": True,
        "strict_profile_rule": rule,
    }


def _history(history: Any, current_round: int) -> list[dict[str, Any]]:
    if not isinstance(history, list):
        raise EntryProfileError("history_invalid")
    rows = []
    seen: set[int] = set()
    for row in history:
        if not isinstance(row, Mapping):
            raise EntryProfileError("history_round_invalid")
        number = _uint(row.get("round_number"), "history_round_number_invalid")
        if number >= current_round:
            raise EntryProfileError("history_round_not_before_current")
        if number in seen:
            raise EntryProfileError("history_round_duplicated")
        seen.add(number)
        digest = row.get("final_scores_sha256")
        if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
            raise EntryProfileError("history_final_scores_sha256_invalid")
        rows.append({
            "round_number": number,
            "present": _bool(row.get("present"), "history_present_invalid"),
            "domain_verified": _bool(row.get("domain_verified"), "history_domain_verified_invalid"),
            "final_score": _uint(row.get("final_score"), "history_final_score_invalid"),
            "score_cutoff": _uint(row.get("score_cutoff"), "history_score_cutoff_invalid"),
        })
    return rows


def _is_clean(row: Mapping[str, Any]) -> bool:
    return bool(row["present"] and row["domain_verified"] and row["final_score"] >= row["score_cutoff"])


def consecutive_clean_rounds(history: Sequence[Mapping[str, Any]], current_round: int) -> int:
    """Clean rounds in an unbroken run ending at ``current_round - 1``."""
    by_round = {row["round_number"]: row for row in _history(history, current_round)}
    count = 0
    expected = current_round - 1
    while expected >= 0 and expected in by_round and _is_clean(by_round[expected]):
        count += 1
        expected -= 1
    return count


def meets_strict_profile(parameters: Mapping[str, Any], operator: Mapping[str, Any]) -> bool:
    params = validate_parameters(parameters)
    current_round = _uint(operator.get("current_round"), "operator_current_round_invalid")
    domain_verified = _bool(operator.get("domain_verified"), "operator_domain_verified_invalid")
    clean = consecutive_clean_rounds(operator.get("history", []), current_round)
    if params["strict_profile_rule"] == "interim_domain_only":
        return domain_verified
    return domain_verified and clean >= params["required_clean_rounds"]


def identity_flag(model_classification: str, strict_profile_met: bool) -> str:
    """The spec's flag rule: an admissible model ``flag`` and an unmet strict profile."""
    if model_classification not in MODEL_CLASSIFICATIONS:
        raise EntryProfileError("model_classification_unsupported")
    _bool(strict_profile_met, "strict_profile_met_invalid")
    return "flag" if model_classification == "flag" and not strict_profile_met else "clear"


def resolve_flag_input(
    artifact: Mapping[str, Any] | None,
    expected_pins: Mapping[str, Any],
    validator_id: str,
) -> str:
    """Step 3's flag input from a flags artifact; any defect gives ``none``."""
    if not isinstance(artifact, Mapping):
        return "none"
    if artifact.get("schema") != FLAGS_SCHEMA or artifact.get("shadow_only") is not True:
        return "none"
    if artifact.get("pins") != dict(expected_pins):
        return "none"
    operators = artifact.get("operators")
    if not isinstance(operators, list):
        return "none"
    matches = [row for row in operators if isinstance(row, Mapping) and row.get("validator_id") == validator_id]
    if len(matches) != 1:
        return "none"
    value = matches[0].get("identity_flag")
    return value if value in ("clear", "flag") else "none"


def evaluate(parameters: Mapping[str, Any], operator: Mapping[str, Any]) -> dict[str, Any]:
    """The entry-profile decision for one operator in one round."""
    params = validate_parameters(parameters)
    validator_id = operator.get("validator_id")
    if not isinstance(validator_id, str) or not validator_id:
        raise EntryProfileError("operator_validator_id_invalid")
    current_round = _uint(operator.get("current_round"), "operator_current_round_invalid")
    incumbent = _bool(operator.get("incumbent"), "operator_incumbent_invalid")
    domain_verified = _bool(operator.get("domain_verified"), "operator_domain_verified_invalid")
    flag = operator.get("flag")
    if flag not in FLAG_INPUTS:
        raise EntryProfileError("operator_flag_unsupported")
    clean = consecutive_clean_rounds(operator.get("history", []), current_round)
    met = meets_strict_profile(parameters, operator)

    reasons = [_FLAG_REASONS[flag]]
    profile = "strict" if flag == "flag" else "standard"
    if incumbent:
        seat = "keeps_seat"
        reasons.append("incumbent_keeps_seat")
    elif profile == "standard" or met:
        seat = "may_take_new_seat"
    else:
        seat = "new_seat_withheld"
    if profile == "strict":
        if met:
            reasons.append("strict_profile_met")
        else:
            if not domain_verified:
                reasons.append("strict_domain_not_verified")
            if params["strict_profile_rule"] == "entry_profile_v1" and clean < params["required_clean_rounds"]:
                reasons.append("strict_clean_rounds_below_required")
    return {
        "clean_rounds": clean,
        "current_round": current_round,
        "meets_strict_profile": met,
        "profile": profile,
        "reasons": sorted(reasons),
        "schema": DECISION_SCHEMA,
        "seat": seat,
        "shadow_only": True,
        "strict_profile_rule": params["strict_profile_rule"],
        "validator_id": validator_id,
    }


def run_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Run one shared fixture case; refusals become ``{"error": code}``."""
    kind = case["kind"]
    try:
        if kind == "evaluate":
            output: Any = evaluate(case["parameters"], case["operator"])
        elif kind == "identity_flag":
            met = meets_strict_profile(case["parameters"], case["operator"])
            output = {
                "identity_flag": identity_flag(case["model_classification"], met),
                "meets_strict_profile": met,
                "validator_id": case["operator"]["validator_id"],
            }
        elif kind == "resolve_flag_input":
            output = {"flag": resolve_flag_input(case.get("artifact"), case["expected_pins"], case["validator_id"])}
        else:
            raise EntryProfileError("case_kind_unsupported")
    except EntryProfileError as error:
        output = {"error": str(error)}
    return output
