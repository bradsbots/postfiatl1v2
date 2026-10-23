"""Offline tests of the identity flag skeleton (spec §10 package tests, plus pins and guard).

Model outputs are stubbed from frozen facts; no model is called.
Run: ``python3 -m pytest benchmarks/ai-governance/identity-flag-20261023 -q``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import admissibility  # noqa: E402
import build_fixtures  # noqa: E402
import identity_flag_pipeline as pl  # noqa: E402
from postfiat_rpc import validator_entry_profile as vep  # noqa: E402

PROMPT_V1_SHA256 = "e5a62a6db15443cea8dbb8b1c048309f10d4e7e87c4050b946cfb9941d443f19"
LOCKED_SPEC_SHA256 = "24102687f2df5a53e77c52d169e1cd10c06523354cee36e12b1f2e9a9b4662fc"  # 6ba024e4
CORPUS = HERE.parent / "validator-identity-packets-20260901"
SPEC = pl.REPO / "docs/specs/identity-flag-pipeline-spec-20261023.md"
PLAN = pl.REPO / "docs/plans/active/z2-advisory-flag-execution-plan-20261022.md"
WORKED_ROUND = {"network": "corpus-20260901", "round_number": 0, "input_package_hash": "0" * 64}


# --- fixtures and stubbed runs ---------------------------------------------

def _load(name: str) -> dict:
    return json.loads((HERE / "fixtures" / name).read_text())


def _packet(row: dict) -> dict:
    return {
        "validator_id": row["validator_id"],
        "network": row["network"],
        "packet_sha256": row["packet_sha256"],
        "packet_text": (CORPUS / row["packet_path"]).read_text(encoding="utf-8"),
    }


@pytest.fixture(scope="module")
def worked():
    data = _load("worked_example_20260903.json")
    rows = data["validators"]
    candidates = [{"validator_id": r["validator_id"], "domain_verified": r["domain_verified"]} for r in rows]
    return data, rows, candidates, [_packet(r) for r in rows]


@pytest.fixture(scope="module")
def round28():
    data = _load("round_28_candidates.json")
    candidates = [{"validator_id": c["validator_id"], "domain_verified": c["domain_verified"]}
                  for c in data["candidates"]]
    packets = [_packet(c) for c in data["candidates"] if c["packet_path"]]
    return data, candidates, packets


def response(request: dict, classification: str) -> str:
    return json.dumps({
        "validator_id": request["validator_id"],
        "packet_sha256": request["packet_sha256"],
        "classification": classification,
        "cited_fields": ["public_identity", "uncertainty_and_conflicts"],
        "reason_codes": ["identity_not_established"] if classification == "flag" else [],
    }, sort_keys=True)


def make_runs(requests: list, decide) -> list:
    """Four byte-identical runs, two per owner; ``decide(validator_id) -> clear|flag``."""
    results = []
    for req in requests:
        content = pl.PAD_CONTENT if req["padding"] else response(req, decide(req["validator_id"]))
        results.append({"slot": req["slot"], "request_sha256": req["request_sha256"],
                        "content": content, "finish_reason": "stop"})
    return [{"owner": owner, "results": copy.deepcopy(results)} for owner in ("A", "A", "B", "B")]


def run_flags(candidates, packets, runs, *, section=None, round_info=WORKED_ROUND, **kwargs):
    return pl.build_flags(round_info=round_info, candidates=candidates, packets=packets, runs=runs,
                          expected_section=section if section is not None else pl.manifest_section(), **kwargs)


def flagged(flags: dict) -> set:
    return {op["validator_id"] for op in flags["operators"] if op["identity_flag"] == "flag"}


def by_id(flags: dict) -> dict:
    return {op["validator_id"]: op for op in flags["operators"]}


def slot_of(requests: list, validator_id: str) -> int:
    return next(r["slot"] for r in requests if r["validator_id"] == validator_id)


def all_flag(_vid: str) -> str:
    return "flag"


@pytest.fixture(scope="module")
def base(worked):
    """The model says flag for every operator: the flag then reaches exactly the D-true ones."""
    _, rows, candidates, packets = worked
    requests = pl.build_requests(packets)
    runs = make_runs(requests, all_flag)
    flags, adm = run_flags(candidates, packets, runs)
    return requests, runs, flags, adm


def xrpl_ids(worked) -> list:
    return [r["validator_id"] for r in worked[1] if r["network"] == "xrpl"]


# --- prompt, schema and pins ------------------------------------------------

def test_prompt_v1_hash_is_pinned_in_package_spec_and_plan():
    digest = hashlib.sha256(pl.PROMPT_PATH.read_bytes()).hexdigest()
    assert digest == PROMPT_V1_SHA256
    assert pl.manifest_section()["prompt_sha256"] == digest
    assert pl.execution_profile()["prompt"] == {"version": "postfiat.identity_flag.prompt.v1", "sha256": digest}
    assert digest in SPEC.read_text() and digest in PLAN.read_text()


def test_locked_spec_text_is_unchanged_above_the_decisions_appendix():
    raw = SPEC.read_bytes()
    locked = raw[: raw.index(b"\n## Appendix A. Decisions of 2026-10-23")]
    assert hashlib.sha256(locked).hexdigest() == LOCKED_SPEC_SHA256


def test_prompt_asks_the_two_questions_and_never_the_legitimacy_prompt():
    text = pl.PROMPT_PATH.read_text(encoding="utf-8")
    assert "Question 1: Does the packet fail to establish a real organization or person" in text
    assert "Question 2: Do the claimed institution and the claimed domain contradict" in text
    for word in ("legitima", "score", "band", "prestige", "reputation"):
        assert word not in text.lower()
    for value in pl.CITED_FIELDS + pl.REASON_CODES:
        assert f'"{value}"' in text


def test_response_schema_is_the_spec_schema():
    schema = pl.response_schema()
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["validator_id", "packet_sha256", "classification", "cited_fields", "reason_codes"]
    props = schema["properties"]
    assert set(props) == set(schema["required"])
    assert tuple(props["classification"]["enum"]) == pl.CLASSIFICATIONS == pl.IDENTITY_FLAG_VALUES == ("clear", "flag")
    assert tuple(props["cited_fields"]["items"]["enum"]) == pl.CITED_FIELDS
    assert props["cited_fields"]["minItems"] == 1 and props["cited_fields"]["uniqueItems"] is True
    assert tuple(props["reason_codes"]["items"]["enum"]) == pl.REASON_CODES
    assert pl.response_schema_sha256() == hashlib.sha256(pl.canonical(schema).encode()).hexdigest()


def test_execution_profile_pins_model_prompt_and_deterministic_side():
    profile = pl.execution_profile()
    assert profile["model"] == {"repo_id": "Qwen/Qwen3.8-27B-FP8",
                                "revision": "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"}
    assert profile["decoding"]["seed"] == 438916795 and profile["decoding"]["temperature"] == 0
    assert profile["replay"] == {"distinct_owner_hosts": 2, "runs_per_host": 2}
    side = profile["deterministic_side"]
    assert side["subscorer_sha256"] == "f71f29ddf00c3825447fc19034340d4ef714b9668345c51e6872586a844c5dc5"
    assert side["entry_profile_sha256"] == "dd98970b92d284cace99efbc4992e1025600d04a74a045d45966576fed44c83f"
    assert side["strict_profile_rule"] == "interim_domain_only"
    assert pl.deterministic_side_matches()
    section = pl.manifest_section()
    assert section["profile_sha256"] == pl.profile_sha256() and section["shadow_only"] is True
    assert section["module_sha256"] == hashlib.sha256(Path(pl.__file__).read_bytes()).hexdigest()


def test_fixtures_rebuild_from_committed_data():
    for name, text in build_fixtures.build().items():
        assert (HERE / "fixtures" / name).read_text() == text


# --- SHADOW_ONLY guard (spec §8) ---------------------------------------------

def test_shadow_only_guard_refuses_every_binding_use(worked, base, tmp_path):
    _, _, candidates, packets = worked
    _, runs, flags, adm = base
    for mode in ("binding", "promoted", "", None):
        with pytest.raises(pl.ShadowOnlyViolation):
            run_flags(candidates, packets, runs, mode=mode)
    with pytest.raises(pl.ShadowOnlyViolation):
        pl.binding_flag_input(flags, "any-validator")
    assert flags["shadow_only"] is True and adm["shadow_only"] is True
    tampered = dict(flags, shadow_only=False)
    with pytest.raises(pl.ShadowOnlyViolation):
        pl.artifact_bytes(tampered)
    with pytest.raises(pl.ShadowOnlyViolation):
        pl.write_artifacts(tmp_path / "out", tampered, adm)
    assert not (tmp_path / "out").exists()
    # Step 3's resolver refuses a non-shadow artifact as well.
    assert vep.resolve_flag_input(tampered, flags["pins"], flags["operators"][0]["validator_id"]) == "none"


# --- §10 package tests -------------------------------------------------------

def test_builder_emits_identical_request_bytes_on_two_runs(worked):
    packets = worked[3]
    first = pl.build_requests(packets)
    shuffled = list(packets)
    random.Random(7).shuffle(shuffled)
    second = pl.build_requests(shuffled)
    assert pl.canonical(first).encode() == pl.canonical(second).encode()
    assert pl.requests_sha256(first) == pl.requests_sha256(second)
    assert len(first) == 64 and sum(r["padding"] for r in first) == 9
    for row in first:
        assert row["request_sha256"] == hashlib.sha256(pl.canonical(row["body"]).encode()).hexdigest()
        if not row["padding"]:
            user = row["body"]["messages"][1]["content"]
            packet = next(p for p in packets if p["validator_id"] == row["validator_id"])
            assert pl.BEGIN_MARK + packet["packet_text"] + pl.END_MARK in user
            assert row["body"]["messages"][0]["content"] == pl.PROMPT_PATH.read_text(encoding="utf-8")
    bad = dict(packets[0], packet_text=packets[0]["packet_text"] + " ")
    with pytest.raises(ValueError):
        pl.build_requests([bad])


def test_builder_covers_every_candidate_or_reports_packet_gap(round28):
    data, candidates, packets = round28
    requests = pl.build_requests(packets)
    flags, _ = run_flags(candidates, packets, make_runs(requests, all_flag), round_info=data["round"])
    assert [op["validator_id"] for op in flags["operators"]] == sorted(c["validator_id"] for c in candidates)
    assert flags["admissibility_summary"]["packet_coverage"] == {"candidates": 61, "with_packet": 20,
                                                                 "missing_packet": 41}
    gaps = [op for op in flags["operators"] if op["packet_sha256"] is None]
    assert len(gaps) == 41
    assert all(op["admissibility"] == "missing" and op["identity_flag"] == "clear" for op in gaps)
    # All 20 packeted round-28 candidates have verified domains, so the interim D is false for each.
    assert flagged(flags) == set()
    unmet = [op for op in flags["operators"] if op["strict_profile_unmet"]]
    assert len(unmet) == 12 and all(op["packet_sha256"] is None for op in unmet)


def test_flag_requires_model_flag_and_unmet_strict_profile(worked):
    for model in ("none", "clear", "flag"):
        for met in (True, False):
            assert vep.identity_flag(model, met) == ("flag" if model == "flag" and not met else "clear")
    _, rows, candidates, packets = worked
    xrpl = [r["validator_id"] for r in rows if r["network"] == "xrpl"][:2]
    pf = [r["validator_id"] for r in rows if r["network"] == "postfiat"][:2]
    model = {xrpl[0]: "flag", xrpl[1]: "clear", pf[0]: "flag", pf[1]: "clear"}
    requests = pl.build_requests(packets)
    flags, _ = run_flags(candidates, packets, make_runs(requests, lambda v: model.get(v, "clear")))
    assert flagged(flags) == {xrpl[0]}
    ops = by_id(flags)
    assert ops[xrpl[0]]["strict_profile_unmet"] and not ops[pf[0]]["strict_profile_unmet"]
    assert ops[pf[0]]["model_classification"] == "flag" and ops[pf[0]]["identity_flag"] == "clear"


def test_model_flag_alone_never_flags_an_operator_meeting_the_strict_profile(worked, base):
    flags = base[2]
    met = {op["validator_id"] for op in flags["operators"] if not op["strict_profile_unmet"]}
    assert len(met) == 20 and not (flagged(flags) & met)
    assert all(by_id(flags)[v]["model_classification"] == "flag" for v in met)
    assert flagged(flags) == set(xrpl_ids(worked))


def test_absent_evidence_alone_never_produces_flag(worked):
    _, rows, candidates, packets = worked
    requests = pl.build_requests(packets)
    flags, _ = run_flags(candidates, packets, make_runs(requests, lambda _v: "clear"))
    unmet = [op for op in flags["operators"] if op["strict_profile_unmet"]]
    assert len(unmet) == 35 and flagged(flags) == set()
    # No packets and no model output at all: still no flag.
    flags, _ = run_flags(candidates, [], [])
    assert flagged(flags) == set()


def _mutate(runs: list, slot: int, run_index: int = 3, **changes) -> list:
    runs = copy.deepcopy(runs)
    row = next(r for r in runs[run_index]["results"] if r["slot"] == slot)
    row.update(changes)
    return runs


def _drop(runs: list, slot: int, run_index: int = 3) -> list:
    runs = copy.deepcopy(runs)
    runs[run_index]["results"] = [r for r in runs[run_index]["results"] if r["slot"] != slot]
    return runs


def test_divergent_slot_yields_no_flag_for_that_operator_only(worked, base):
    requests, runs, flags, _ = base
    _, _, candidates, packets = worked
    target = xrpl_ids(worked)[0]
    content = next(r for r in runs[0]["results"] if r["slot"] == slot_of(requests, target))["content"]
    mutated = _mutate(runs, slot_of(requests, target), content=content.replace("public_identity", "evidence"))
    new, adm = run_flags(candidates, packets, mutated)
    assert by_id(new)[target]["admissibility"] == "divergent" and by_id(new)[target]["identity_flag"] == "clear"
    assert flagged(new) == flagged(flags) - {target}
    slot = next(s for s in adm["slots"] if s["validator_id"] == target)
    assert slot["byte_identical"] is False and len(set(slot["content_sha256"])) == 2


def test_padding_divergence_yields_no_flag_for_its_batch(worked, base):
    requests, runs, flags, _ = base
    _, _, candidates, packets = worked
    pad = next(r for r in requests if r["padding"])
    new, adm = run_flags(candidates, packets, _mutate(runs, pad["slot"], content='{"pad":false}'))
    batch = {r["validator_id"] for r in requests if not r["padding"] and r["slot"] // 32 == pad["slot"] // 32}
    assert len(batch) == 23
    assert flagged(new) == flagged(flags) - batch
    for vid in batch:
        assert by_id(new)[vid]["admissibility"] == "divergent" and by_id(new)[vid]["identity_flag"] == "clear"
    voided = [s for s in adm["slots"] if s["voided_by_padding_slot"] == pad["slot"]]
    assert {s["validator_id"] for s in voided} == batch
    other = {r["validator_id"] for r in requests if r["slot"] < 32}
    assert all(by_id(new)[v] == by_id(flags)[v] for v in other)


def test_missing_slot_yields_no_flag(worked, base):
    requests, runs, flags, _ = base
    _, _, candidates, packets = worked
    target = xrpl_ids(worked)[1]
    new, _ = run_flags(candidates, packets, _drop(runs, slot_of(requests, target)))
    assert by_id(new)[target]["admissibility"] == "missing"
    assert flagged(new) == flagged(flags) - {target}


def test_run_outage_yields_zero_flags(worked, base):
    _, runs, _, _ = base
    _, _, candidates, packets = worked
    for broken in (runs[:3], runs[:2], [], runs + runs[:1],
                   [dict(r, owner="A") for r in runs], [dict(r, owner=o) for r, o in zip(runs, "AAAB")]):
        new, adm = run_flags(candidates, packets, broken)
        assert flagged(new) == set() and adm["outage"] is True
        assert new["admissibility_summary"]["counts_by_class"]["outage"] == 55
    # Model deletion is the outage case with no runs at all: the no-op branch.
    new, _ = run_flags(candidates, packets, [])
    assert all(op["identity_flag"] == "clear" and op["model_classification"] is None for op in new["operators"])


def _response_variants(request: dict) -> list:
    good = json.loads(response(request, "flag"))
    variants = [
        ("truncated", None, "length"),
        ("invalid", '{"validator_id": ', "stop"),
        ("invalid", "[]", "stop"),
        ("invalid", json.dumps(dict(good, extra=1), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, classification="maybe"), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, cited_fields=[]), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, cited_fields=["public_identity", "evidence"]), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, cited_fields=["evidence", "evidence"]), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, cited_fields=["website"]), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, reason_codes=[]), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, reason_codes=["fabricated"]), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, classification="clear"), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, cited_fields=[["evidence"]]), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, reason_codes="identity_not_established"), sort_keys=True), "stop"),
        ("invalid", json.dumps(dict(good, classification=["flag"]), sort_keys=True), "stop"),
    ]
    return variants


def _replace_everywhere(runs: list, slot: int, content, finish_reason) -> list:
    runs = copy.deepcopy(runs)
    for run in runs:
        for row in run["results"]:
            if row["slot"] == slot:
                row["content"] = content if content is not None else row["content"]
                row["finish_reason"] = finish_reason
    return runs


def test_truncated_or_invalid_response_yields_no_flag(worked, base):
    requests, runs, flags, _ = base
    _, _, candidates, packets = worked
    target = xrpl_ids(worked)[2]
    slot = slot_of(requests, target)
    request = requests[slot]
    for expected, content, finish in _response_variants(request):
        new, _ = run_flags(candidates, packets, _replace_everywhere(runs, slot, content, finish))
        assert by_id(new)[target]["admissibility"] == expected, content
        assert flagged(new) == flagged(flags) - {target}
    assert pl.check_response(request, None, "stop") == ("invalid", None)


def test_wrong_packet_echo_yields_no_flag(worked, base):
    requests, runs, flags, _ = base
    _, _, candidates, packets = worked
    target = xrpl_ids(worked)[3]
    slot = slot_of(requests, target)
    good = json.loads(response(requests[slot], "flag"))
    for wrong in (dict(good, validator_id=xrpl_ids(worked)[4]), dict(good, packet_sha256="f" * 64)):
        new, _ = run_flags(candidates, packets,
                           _replace_everywhere(runs, slot, json.dumps(wrong, sort_keys=True), "stop"))
        assert by_id(new)[target]["admissibility"] == "wrong_echo"
        assert flagged(new) == flagged(flags) - {target}


def test_stale_profile_pin_yields_zero_flags(worked, base):
    requests, runs, flags, _ = base
    _, _, candidates, packets = worked
    for key in ("profile_sha256", "prompt_sha256", "response_schema_sha256", "module_sha256",
                "entry_profile_sha256", "strict_profile_rule"):
        section = dict(pl.manifest_section(), **{key: "changed"})
        new, adm = run_flags(candidates, packets, runs, section=section)
        assert flagged(new) == set() and adm["pins_stale"] is True
        assert new["admissibility_summary"]["counts_by_class"]["stale"] == 55
    new, _ = run_flags(candidates, packets, runs, section={})
    assert flagged(new) == set()
    # A packet outside the frozen packet set is stale for that operator only.
    target = xrpl_ids(worked)[5]
    frozen = {p["packet_sha256"] for p in packets if p["validator_id"] != target}
    new, _ = run_flags(candidates, packets, runs, frozen_packet_set=frozen)
    assert by_id(new)[target]["admissibility"] == "stale"
    assert flagged(new) == flagged(flags) - {target}
    # A run that replayed other request bytes is stale for that slot.
    new, _ = run_flags(candidates, packets, _mutate(runs, slot_of(requests, target), request_sha256="0" * 64))
    assert by_id(new)[target]["admissibility"] == "stale"
    assert flagged(new) == flagged(flags) - {target}


def test_changed_subscorer_hash_yields_zero_flags(worked, base, tmp_path, monkeypatch):
    _, runs, flags, _ = base
    _, _, candidates, packets = worked
    assert len(flagged(flags)) == 35
    section = dict(pl.manifest_section(), subscorer_sha256="0" * 64)
    new, _ = run_flags(candidates, packets, runs, section=section)
    assert flagged(new) == set()
    changed = tmp_path / "subscorer_v3.py"
    changed.write_bytes(pl.SUBSCORER_PATH.read_bytes() + b"\n# changed\n")
    monkeypatch.setattr(pl, "SUBSCORER_PATH", changed)
    assert pl.deterministic_side_matches() is False
    new, adm = run_flags(candidates, packets, runs)
    assert flagged(new) == set() and adm["pins_stale"] is True


def test_each_failure_changes_nothing_else(worked, base):
    requests, runs, flags, _ = base
    _, _, candidates, packets = worked
    target = xrpl_ids(worked)[6]
    slot = slot_of(requests, target)
    good = json.loads(response(requests[slot], "flag"))
    failures = {
        "divergent": _mutate(runs, slot, content="{}"),
        "missing": _drop(runs, slot),
        "truncated": _replace_everywhere(runs, slot, None, "length"),
        "invalid": _replace_everywhere(runs, slot, "not json", "stop"),
        "wrong_echo": _replace_everywhere(runs, slot, json.dumps(dict(good, packet_sha256="e" * 64)), "stop"),
        "stale": _mutate(runs, slot, request_sha256="1" * 64),
    }
    before = by_id(flags)
    for status, mutated in failures.items():
        new, _ = run_flags(candidates, packets, mutated)
        after = by_id(new)
        assert after[target]["admissibility"] == status and after[target]["identity_flag"] == "clear"
        for vid, row in before.items():
            if vid != target:
                assert after[vid] == row, (status, vid)
        assert new["pins"] == flags["pins"]


def test_flags_artifact_is_canonical_and_sorted(worked, base, tmp_path):
    _, runs, flags, adm = base
    _, _, candidates, packets = worked
    again, again_adm = run_flags(list(reversed(candidates)), list(reversed(packets)), list(reversed(runs)))
    assert pl.artifact_bytes(flags) == pl.artifact_bytes(again)
    assert pl.artifact_bytes(adm) == pl.artifact_bytes(again_adm)
    ids = [op["validator_id"] for op in flags["operators"]]
    assert ids == sorted(ids)
    raw = pl.artifact_bytes(flags)
    assert raw == (json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":")) + "\n").encode()
    pl.write_artifacts(tmp_path, flags, adm)
    assert (tmp_path / "flags.json").read_bytes() == raw
    assert (tmp_path / "admissibility.json").read_bytes() == pl.artifact_bytes(adm)


def test_flags_artifact_records_strict_profile_rule(base):
    flags = base[2]
    assert flags["schema"] == "postfiat.identity_flag.v1"
    assert flags["strict_profile_rule"] == "interim_domain_only"
    assert flags["pins"]["subscorer_sha256"] == pl.SUBSCORER_V3_SHA256
    assert flags["pins"]["entry_profile_sha256"] == pl.ENTRY_PROFILE_RUST_SHA256
    assert flags["pins"]["prompt_sha256"] == PROMPT_V1_SHA256
    # Step 3 reads the artifact through its resolver: the pins accepted, a flag per operator.
    vid = sorted(flagged(flags))[0]
    assert vep.resolve_flag_input(flags, flags["pins"], vid) == "flag"
    assert vep.resolve_flag_input(flags, dict(flags["pins"], prompt_sha256="0" * 64), vid) == "none"


def test_admissibility_summary_reports_all_classes_and_packet_coverage(worked, base):
    flags = base[2]
    summary = flags["admissibility_summary"]
    assert tuple(summary["counts_by_class"]) == pl.ADMISSIBILITY_CLASSES
    assert sum(summary["counts_by_class"].values()) == summary["packet_coverage"]["candidates"] == 55
    assert summary["packet_coverage"] == {"candidates": 55, "with_packet": 55, "missing_packet": 0}
    _, _, candidates, packets = worked
    new, _ = run_flags(candidates, packets[:50], make_runs(pl.build_requests(packets[:50]), all_flag))
    assert new["admissibility_summary"]["packet_coverage"] == {"candidates": 55, "with_packet": 50,
                                                               "missing_packet": 5}
    assert new["admissibility_summary"]["counts_by_class"]["missing"] == 5


def test_any_scoring_or_padding_divergence_marks_replay_unreliable(worked, base):
    requests, runs, flags, adm = base
    _, _, candidates, packets = worked
    assert flags["replay_unreliable"] is False and adm["replay_unreliable"] is False
    scoring = slot_of(requests, xrpl_ids(worked)[0])
    pad = next(r["slot"] for r in requests if r["padding"])
    for slot in (scoring, pad):
        new, new_adm = run_flags(candidates, packets, _mutate(runs, slot, content='{"x":1}'))
        assert new["replay_unreliable"] is True and new_adm["replay_unreliable"] is True
    # Identical but inadmissible content is not a divergence.
    new, _ = run_flags(candidates, packets, _replace_everywhere(runs, scoring, "not json", "stop"))
    assert new["replay_unreliable"] is False


def test_worked_example_2026_09_03_counts(worked):
    data, rows, candidates, packets = worked
    requests = pl.build_requests(packets)
    score_zero = {r["validator_id"] for r in rows if r["legitimacy_score"] == 0}
    not_established = {r["validator_id"] for r in rows if r["not_established"]}
    assert len(score_zero) == 33 and len(not_established) == 10
    first, _ = run_flags(candidates, packets, make_runs(requests, lambda v: "flag" if v in score_zero else "clear"))
    second, _ = run_flags(candidates, packets,
                          make_runs(requests, lambda v: "flag" if v in not_established else "clear"))
    networks = {r["validator_id"]: r["network"] for r in rows}
    assert len(flagged(first)) == 13 and {networks[v] for v in flagged(first)} == {"xrpl"}
    assert len(flagged(second)) == 0
    assert data["expected_flags"] == {"legitimacy_score_zero": 13, "packet_not_established": 0}
    cases = json.loads((HERE.parent / "validator-entry-profile-20261023/fixtures/cases.json").read_text())
    assert cases["worked_example_flags"] == data["expected_flags"]


# --- CLI ----------------------------------------------------------------------

def test_admissibility_cli_writes_both_artifacts(round28, tmp_path, capsys):
    data, candidates, packets = round28
    requests_path = tmp_path / "requests.json"
    round_path = HERE / "fixtures/round_28_candidates.json"
    assert admissibility.main(["--round", str(round_path), "--requests-out", str(requests_path)]) == 0
    requests = json.loads(requests_path.read_text())
    assert pl.requests_sha256(requests) == pl.requests_sha256(pl.build_requests(packets))
    args = ["--round", str(round_path), "--out", str(tmp_path / "out")]
    section = tmp_path / "section.json"
    section.write_text(json.dumps(pl.manifest_section()))
    args += ["--section", str(section)]
    for index, run in enumerate(make_runs(requests, all_flag)):
        path = tmp_path / f"run{index}.json"
        path.write_text(json.dumps({"results": run["results"]}))
        args += ["--run", f"{run['owner']}={path}"]
    capsys.readouterr()
    assert admissibility.main(args) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["flags"] == 0 and printed["packet_coverage"]["missing_packet"] == 41
    flags = json.loads((tmp_path / "out/flags.json").read_text())
    assert flags["shadow_only"] is True and len(flags["operators"]) == 61
    assert (tmp_path / "out/admissibility.json").exists()
