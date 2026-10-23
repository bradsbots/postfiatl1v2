#!/usr/bin/env python3
"""Build the shared strict-entry-profile fixtures (Z2 step 3).

Writes ``fixtures/cases.json``: every case has its inputs, the expected output
and the SHA-256 of that output's canonical JSON. The Rust module
(``crates/consensus_cobalt/src/validator_entry_profile.rs``) and the Python
mirror (``python/postfiat_rpc/validator_entry_profile.py``) must both produce
exactly those bytes.

Case groups:

- ``direction``: the direction's five cases plus boundaries. Their expected
  outputs are written here by hand, and the build refuses to write if the
  mirror disagrees with any of them.
- ``worked_example_20260903``: the spec's section 4.1, from the committed
  2026-09-03 corpus and replay outputs.
- ``round_28``: the fork's testnet round 28, from the fetched round files
  (gitignored, SHA-256-pinned in the sub-scorer's ``rounds-manifest.json``).

No network. Run from the repository root: ``python3 benchmarks/ai-governance/validator-entry-profile-20261023/build_fixtures.py``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "python"))

from postfiat_rpc import validator_entry_profile as vep  # noqa: E402

SUBSCORER = ROOT / "benchmarks/ai-governance/dunl-subscorer-shadow-20260901"
CORPUS = ROOT / "benchmarks/ai-governance/validator-identity-packets-20260901/index.json"
REPLAY = ROOT / "benchmarks/ai-governance/identity-packet-replay-20260903/outputs/primary-run1.json"
H = "ab" * 32


def params(rule: str = "entry_profile_v1", **overrides) -> dict:
    value = {
        "schema": "postfiat.validator_entry_profile.parameters.v1",
        "required_clean_rounds": 4,
        "require_verified_domain": True,
        "strict_profile_rule": rule,
    }
    value.update(overrides)
    return value


def rnd(number: int, *, present=True, domain=True, score=90, cutoff=40) -> dict:
    return {"round_number": number, "final_scores_sha256": H, "present": present,
            "domain_verified": domain, "final_score": score, "score_cutoff": cutoff}


def op(vid: str, *, flag="flag", incumbent=False, domain=True, current=29, history=()) -> dict:
    return {"validator_id": vid, "current_round": current, "incumbent": incumbent,
            "domain_verified": domain, "flag": flag, "history": list(history)}


def decision(vid, *, profile, seat, met, clean, reasons, rule="entry_profile_v1", current=29) -> dict:
    return {"clean_rounds": clean, "current_round": current, "meets_strict_profile": met,
            "profile": profile, "reasons": sorted(reasons), "schema": vep.DECISION_SCHEMA,
            "seat": seat, "shadow_only": True, "strict_profile_rule": rule, "validator_id": vid}


PINS = {"profile_sha256": "11" * 32, "subscorer_sha256": "f71f29ddf00c3825447fc19034340d4ef714b9668345c51e6872586a844c5dc5",
        "entry_profile_sha256": None}


def flags_artifact(rows, **overrides) -> dict:
    value = {"schema": "postfiat.identity_flag.v1", "shadow_only": True, "pins": dict(PINS),
             "operators": [{"validator_id": vid, "identity_flag": flag} for vid, flag in rows]}
    value.update(overrides)
    return value


def direction_cases() -> list[dict]:
    four = [rnd(25), rnd(26), rnd(27), rnd(28)]
    cases = [
        ("flagged_real_operator_eligible_after_four_clean_rounds",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-real", history=four)},
         decision("op-real", profile="strict", seat="may_take_new_seat", met=True, clean=4,
                  reasons=["flag_selects_strict_profile", "strict_profile_met"])),
        ("flagged_entrant_withheld_before_the_strict_profile",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-new", history=[rnd(27), rnd(28)])},
         decision("op-new", profile="strict", seat="new_seat_withheld", met=False, clean=2,
                  reasons=["flag_selects_strict_profile", "strict_clean_rounds_below_required"])),
        ("flagged_incumbent_keeps_its_seat",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-inc", incumbent=True, domain=False)},
         decision("op-inc", profile="strict", seat="keeps_seat", met=False, clean=0,
                  reasons=["flag_selects_strict_profile", "incumbent_keeps_seat",
                           "strict_clean_rounds_below_required", "strict_domain_not_verified"])),
        ("model_outage_no_artifact_resolves_to_no_flag",
         {"kind": "resolve_flag_input", "artifact": None, "expected_pins": PINS, "validator_id": "op-x"},
         {"flag": "none"}),
        ("no_flag_input_selects_the_standard_profile",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-x", flag="none", domain=False)},
         decision("op-x", profile="standard", seat="may_take_new_seat", met=False, clean=0,
                  reasons=["no_flag_input_standard_profile"])),
        ("divergent_replay_inadmissible_model_gives_clear",
         {"kind": "identity_flag", "parameters": params(), "model_classification": "none",
          "operator": op("op-div", history=[])},
         {"identity_flag": "clear", "meets_strict_profile": False, "validator_id": "op-div"}),
        ("boundary_three_clean_rounds_is_not_enough",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-3", history=[rnd(26), rnd(27), rnd(28)])},
         decision("op-3", profile="strict", seat="new_seat_withheld", met=False, clean=3,
                  reasons=["flag_selects_strict_profile", "strict_clean_rounds_below_required"])),
        ("boundary_a_gap_breaks_the_run",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-gap", history=[rnd(24), rnd(25), rnd(27), rnd(28)])},
         decision("op-gap", profile="strict", seat="new_seat_withheld", met=False, clean=2,
                  reasons=["flag_selects_strict_profile", "strict_clean_rounds_below_required"])),
        ("boundary_domain_lost_in_round_four",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-lost", history=[rnd(25), rnd(26), rnd(27), rnd(28, domain=False)])},
         decision("op-lost", profile="strict", seat="new_seat_withheld", met=False, clean=0,
                  reasons=["flag_selects_strict_profile", "strict_clean_rounds_below_required"])),
        ("boundary_score_below_cutoff_is_not_clean",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-low", history=[rnd(25), rnd(26, score=39), rnd(27), rnd(28)])},
         decision("op-low", profile="strict", seat="new_seat_withheld", met=False, clean=2,
                  reasons=["flag_selects_strict_profile", "strict_clean_rounds_below_required"])),
        ("boundary_absent_from_a_round_is_not_clean",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-abs", history=[rnd(25), rnd(26), rnd(27, present=False, score=0), rnd(28)])},
         decision("op-abs", profile="strict", seat="new_seat_withheld", met=False, clean=1,
                  reasons=["flag_selects_strict_profile", "strict_clean_rounds_below_required"])),
        ("boundary_a_flag_that_clears_selects_the_standard_profile",
         {"kind": "evaluate", "parameters": params(), "operator": op("op-clr", flag="clear", history=[rnd(28)])},
         decision("op-clr", profile="standard", seat="may_take_new_seat", met=False, clean=1,
                  reasons=["flag_clear_standard_profile"])),
        ("boundary_model_flag_on_an_operator_meeting_the_strict_profile_gives_clear",
         {"kind": "identity_flag", "parameters": params(), "model_classification": "flag", "operator": op("op-met", history=four)},
         {"identity_flag": "clear", "meets_strict_profile": True, "validator_id": "op-met"}),
        ("boundary_model_flag_and_unmet_strict_profile_gives_flag",
         {"kind": "identity_flag", "parameters": params(), "model_classification": "flag", "operator": op("op-unmet", history=[rnd(28)])},
         {"identity_flag": "flag", "meets_strict_profile": False, "validator_id": "op-unmet"}),
        ("interim_rule_verified_domain_meets_without_history",
         {"kind": "evaluate", "parameters": params("interim_domain_only"), "operator": op("op-int")},
         decision("op-int", profile="strict", seat="may_take_new_seat", met=True, clean=0,
                  reasons=["flag_selects_strict_profile", "strict_profile_met"], rule="interim_domain_only")),
        ("interim_rule_unverified_domain_is_withheld",
         {"kind": "evaluate", "parameters": params("interim_domain_only"), "operator": op("op-int-x", domain=False)},
         decision("op-int-x", profile="strict", seat="new_seat_withheld", met=False, clean=0,
                  reasons=["flag_selects_strict_profile", "strict_domain_not_verified"], rule="interim_domain_only")),
        ("resolve_valid_flag", {"kind": "resolve_flag_input", "artifact": flags_artifact([("op-a", "flag"), ("op-b", "clear")]),
                                "expected_pins": PINS, "validator_id": "op-a"}, {"flag": "flag"}),
        ("resolve_valid_clear", {"kind": "resolve_flag_input", "artifact": flags_artifact([("op-a", "flag"), ("op-b", "clear")]),
                                 "expected_pins": PINS, "validator_id": "op-b"}, {"flag": "clear"}),
        ("resolve_pin_mismatch_gives_none", {"kind": "resolve_flag_input",
                                             "artifact": flags_artifact([("op-a", "flag")], pins={**PINS, "subscorer_sha256": "00" * 32}),
                                             "expected_pins": PINS, "validator_id": "op-a"}, {"flag": "none"}),
        ("resolve_wrong_schema_gives_none", {"kind": "resolve_flag_input",
                                             "artifact": flags_artifact([("op-a", "flag")], schema="postfiat.identity_flag.v0"),
                                             "expected_pins": PINS, "validator_id": "op-a"}, {"flag": "none"}),
        ("resolve_non_shadow_artifact_gives_none", {"kind": "resolve_flag_input",
                                                    "artifact": flags_artifact([("op-a", "flag")], shadow_only=False),
                                                    "expected_pins": PINS, "validator_id": "op-a"}, {"flag": "none"}),
        ("resolve_absent_operator_gives_none", {"kind": "resolve_flag_input", "artifact": flags_artifact([("op-a", "flag")]),
                                                "expected_pins": PINS, "validator_id": "op-z"}, {"flag": "none"}),
        ("resolve_duplicate_operator_gives_none", {"kind": "resolve_flag_input",
                                                   "artifact": flags_artifact([("op-a", "flag"), ("op-a", "clear")]),
                                                   "expected_pins": PINS, "validator_id": "op-a"}, {"flag": "none"}),
        ("resolve_unknown_flag_value_gives_none", {"kind": "resolve_flag_input", "artifact": flags_artifact([("op-a", "maybe")]),
                                                   "expected_pins": PINS, "validator_id": "op-a"}, {"flag": "none"}),
        ("refuse_duplicate_history_round", {"kind": "evaluate", "parameters": params(),
                                            "operator": op("op-e", history=[rnd(28), rnd(28)])}, {"error": "history_round_duplicated"}),
        ("refuse_history_round_not_before_current", {"kind": "evaluate", "parameters": params(),
                                                     "operator": op("op-e", history=[rnd(29)])}, {"error": "history_round_not_before_current"}),
        ("refuse_bad_final_scores_hash", {"kind": "evaluate", "parameters": params(),
                                          "operator": op("op-e", history=[{**rnd(28), "final_scores_sha256": "AB" * 32}])},
         {"error": "history_final_scores_sha256_invalid"}),
        ("refuse_unknown_flag_input", {"kind": "evaluate", "parameters": params(), "operator": op("op-e", flag="maybe")},
         {"error": "operator_flag_unsupported"}),
        ("refuse_optional_domain_requirement", {"kind": "evaluate", "parameters": params(require_verified_domain=False),
                                                "operator": op("op-e")}, {"error": "parameters_require_verified_domain_must_be_true"}),
        ("refuse_unknown_strict_profile_rule", {"kind": "evaluate", "parameters": params("model_only"), "operator": op("op-e")},
         {"error": "parameters_strict_profile_rule_unsupported"}),
        ("refuse_boolean_as_round_number", {"kind": "evaluate", "parameters": params(),
                                            "operator": op("op-e", history=[{**rnd(28), "round_number": True}])},
         {"error": "history_round_number_invalid"}),
    ]
    out = []
    for name, case, expected in cases:
        actual = vep.run_case(case)
        if actual != expected:
            raise SystemExit(f"mirror disagrees with the hand-written expectation for {name}: {actual} != {expected}")
        out.append({"group": "direction", "name": name, **case})
    return out


def worked_example_cases() -> list[dict]:
    index = {row["validator_id"]: row for row in json.loads(CORPUS.read_text())}
    results = [r for r in json.loads(REPLAY.read_text())["results"] if not r["padding"]]
    cases = []
    for stand_in in ("legitimacy_score_zero", "packet_not_established"):
        for result in sorted(results, key=lambda r: r["validator_id"]):
            row = index[result["validator_id"]]
            model_flag = (result["parsed"]["score"] == 0) if stand_in == "legitimacy_score_zero" else (row["canonical_entity"] is None)
            cases.append({
                "group": "worked_example_20260903", "name": f"{stand_in}:{row['network']}:{row['validator_id']}",
                "kind": "identity_flag", "parameters": params("interim_domain_only"),
                "model_classification": "flag" if model_flag else "clear",
                "operator": op(row["validator_id"], flag="none", domain=row["domain_verification_status"] is True, current=21),
            })
    return cases


def round_28_cases() -> list[dict]:
    rd = SUBSCORER / "rounds" / "testnet-r28"
    pins = json.loads((SUBSCORER / "rounds-manifest.json").read_text())["rounds"]["28"]
    for rel, meta in pins.items():
        if hashlib.sha256((rd / rel).read_bytes()).hexdigest() != meta["sha256"]:
            raise SystemExit(f"round 28 file {rel} does not match its pin")
    sys.path.insert(0, str(SUBSCORER))
    import subscorer  # noqa: E402

    vmap = json.loads((rd / "inputs/validator_map.json").read_text())
    entries = {vmap[e["validator_id"]]["master_key"]: e for e in subscorer.load_round_entries(rd)}
    finals = {e["master_key"]: e["final_score"] for e in json.loads((rd / "outputs/final_scores.json").read_text())["scores"]}
    previous = set(json.loads((rd / "inputs/previous_unl.json").read_text())["previous_unl"])
    cutoff = json.loads((rd / "runtime/execution_manifest.json").read_text())["code"]["selector"]["parameters"]["score_cutoff"]
    final_sha = pins["outputs/final_scores.json"]["sha256"]
    cases = []
    for rule in ("entry_profile_v1", "interim_domain_only"):
        for mk in sorted(entries):
            verified = entries[mk].get("domain_verified") is True
            history = [{"round_number": 28, "final_scores_sha256": final_sha, "present": True,
                        "domain_verified": verified, "final_score": finals[mk], "score_cutoff": cutoff}]
            cases.append({"group": "round_28", "name": f"{rule}:{mk}", "kind": "evaluate", "parameters": params(rule),
                          "operator": op(mk, incumbent=mk in previous, domain=verified, history=history)})
    return cases


def main() -> int:
    cases = direction_cases() + worked_example_cases() + round_28_cases()
    for case in cases:
        case["expected"] = vep.run_case(case)
        case["expected_sha256"] = hashlib.sha256(vep.canonical_bytes(case["expected"])).hexdigest()
    flags = {}
    for case in cases:
        if case["group"] == "worked_example_20260903":
            stand_in = case["name"].split(":")[0]
            flags[stand_in] = flags.get(stand_in, 0) + (case["expected"]["identity_flag"] == "flag")
    if flags != {"legitimacy_score_zero": 13, "packet_not_established": 0}:
        raise SystemExit(f"worked example counts differ from the spec: {flags}")
    document = {
        "schema": "postfiat.validator_entry_profile.fixtures.v1",
        "module_schema": vep.SCHEMA,
        "module_version": vep.VERSION,
        "counts": {group: sum(c["group"] == group for c in cases) for group in ("direction", "worked_example_20260903", "round_28")},
        "worked_example_flags": flags,
        "cases": cases,
    }
    out = HERE / "fixtures" / "cases.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
    print(f"wrote {out.relative_to(ROOT)}: {len(cases)} cases {document['counts']} flags {flags}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
