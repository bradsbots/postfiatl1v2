"""Identity flag pipeline skeleton (Z2 step 2), ``SHADOW_ONLY``.

Implements the locked ``docs/specs/identity-flag-pipeline-spec-20261023.md``:

- the typed ``identity_flag`` with exactly two values, ``clear`` and ``flag`` (§3);
- the flag rule: an admissible model ``flag`` **and** an unmet strict profile
  (§4). The strict check and the rule come from the strict entry profile
  mirror (``python/postfiat_rpc/validator_entry_profile.py``), under the decided
  ``interim_domain_only`` rule;
- the pinned execution-profile record and the round-manifest section (§6);
- the request builder, which reuses the 2026-09-03 replay layout: exact packet
  bytes between markers, fixed batches of 32 and fixed padding slots;
- the two-owner byte-convergent replay check and the per-slot checks (§5);
- the failure table (§9), in which every failure gives no flag;
- the ``SHADOW_ONLY`` guard (§8). Any binding use raises ``ShadowOnlyViolation``.

No model is called here. The GPU host runner is the 2026-09-03 package's
``run_host.py``. Its outputs are the run files this module compares.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "python"))

from postfiat_rpc import validator_entry_profile as vep  # noqa: E402

FLAGS_SCHEMA = "postfiat.identity_flag.v1"
RESPONSE_SCHEMA_NAME = "postfiat.identity_flag.model_response.v1"
PROFILE_SCHEMA = "postfiat.identity_flag.profile.v1"
ADMISSIBILITY_SCHEMA = "postfiat.identity_flag.admissibility.v1"
PROMPT_VERSION = "postfiat.identity_flag.prompt.v1"
PROMPT_PATH = HERE / "prompt_v1.txt"
SCHEMA_PATH = HERE / "response_schema_v1.json"
SUBSCORER_PATH = REPO / "benchmarks/ai-governance/dunl-subscorer-shadow-20260901/subscorer_v3.py"
ENTRY_PROFILE_RUST_PATH = REPO / "crates/consensus_cobalt/src/validator_entry_profile.rs"
ENTRY_PROFILE_PYTHON_PATH = REPO / "python/postfiat_rpc/validator_entry_profile.py"

# Pinned values (spec §6; decisions of 2026-10-23 in the spec's appendix).
SUBSCORER_V3_SHA256 = "f71f29ddf00c3825447fc19034340d4ef714b9668345c51e6872586a844c5dc5"
ENTRY_PROFILE_RUST_SHA256 = "dd98970b92d284cace99efbc4992e1025600d04a74a045d45966576fed44c83f"
ENTRY_PROFILE_PYTHON_SHA256 = "18191847385dc2f52b9479e9a6e822b43e4866b6570704e8239b47f594bcff00"
STRICT_PROFILE_RULE = "interim_domain_only"
STRICT_PARAMETERS = {
    "schema": "postfiat.validator_entry_profile.parameters.v1",
    "required_clean_rounds": 4,
    "require_verified_domain": True,
    "strict_profile_rule": STRICT_PROFILE_RULE,
}
MODEL = "Qwen/Qwen3.8-27B-FP8"
MODEL_REVISION = "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"
RUNTIME_IMAGE = (
    "lmsysorg/sglang:nightly-dev-cu13-20260817-d91c3682"
    "@sha256:fa8774dd128600a09fd6d46670b06fb69a55dac8a3881e50ccf0916a45eb39af"
)
SEED = 438916795
BATCH_SIZE = 32
MAX_TOKENS = 2048
OWNERS_REQUIRED = 2
RUNS_PER_OWNER = 2
BEGIN_MARK = "----- BEGIN FROZEN IDENTITY PACKET (exact bytes) -----\n"
END_MARK = "\n----- END FROZEN IDENTITY PACKET -----\n"

IDENTITY_FLAG_VALUES = ("clear", "flag")
CLASSIFICATIONS = ("clear", "flag")
REASON_CODES = ("identity_not_established", "institution_domain_contradiction")
CITED_FIELDS = (
    "activities",
    "business_summary",
    "claimed_domain_and_official_urls",
    "estimated_public_profile_size",
    "evidence",
    "public_identity",
    "public_x_handle",
    "region_of_incorporation_and_operations",
    "uncertainty_and_conflicts",
    "validator_coordinates",
)
ADMISSIBILITY_CLASSES = (
    "admissible", "divergent", "missing", "truncated", "invalid", "wrong_echo", "stale", "outage",
)
PAD_CONTENT = '{"pad":true}'
PAD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"pad": {"type": "boolean"}},
    "required": ["pad"],
}


class ShadowOnlyViolation(RuntimeError):
    """A binding use of a model-derived output before the promotion gates pass."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def response_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def response_schema_sha256() -> str:
    """Spec §6: the SHA-256 of the schema's canonical JSON."""
    return sha256(canonical(response_schema()))


# --- SHADOW_ONLY guard (spec §8) -------------------------------------------

def require_shadow(mode: str) -> None:
    if mode != "shadow":
        raise ShadowOnlyViolation(
            f"identity flags are SHADOW_ONLY until the promotion gates pass; mode {mode!r} refused"
        )


def binding_flag_input(*_args: Any, **_kwargs: Any) -> str:
    """The binding path. No promotion record exists, so every call raises."""
    raise ShadowOnlyViolation(
        "no promotion record: identity flags may not feed a selector, score, registry or trust view"
    )


def assert_shadow_artifact(artifact: Mapping[str, Any]) -> None:
    if artifact.get("shadow_only") is not True:
        raise ShadowOnlyViolation("a flags artifact must carry shadow_only: true")


# --- Pinned execution profile and round-manifest section (spec §6) ---------

def execution_profile() -> dict[str, Any]:
    return {
        "schema": PROFILE_SCHEMA,
        "model": {"repo_id": MODEL, "revision": MODEL_REVISION},
        "runtime": {
            "image": RUNTIME_IMAGE,
            "loopback_only": True,
            "radix_cache": False,
            "cuda_graphs": False,
            "overlap_schedule": False,
            "attention_backend": "triton",
            "linear_attn_backend": "triton",
            "chunked_prefill_size": 4096,
            "context_length": 32768,
        },
        "decoding": {
            "temperature": 0,
            "top_p": 1,
            "thinking": False,
            "max_tokens": MAX_TOKENS,
            "seed": SEED,
            "deterministic_inference": True,
        },
        "batching": {"batch_size": BATCH_SIZE, "max_running_requests": BATCH_SIZE},
        "prompt": {"version": PROMPT_VERSION, "sha256": file_sha256(PROMPT_PATH)},
        "response_schema": {"name": RESPONSE_SCHEMA_NAME, "sha256": response_schema_sha256()},
        "replay": {"distinct_owner_hosts": OWNERS_REQUIRED, "runs_per_host": RUNS_PER_OWNER},
        "deterministic_side": {
            "subscorer_sha256": SUBSCORER_V3_SHA256,
            "entry_profile_sha256": ENTRY_PROFILE_RUST_SHA256,
            "entry_profile_mirror_sha256": ENTRY_PROFILE_PYTHON_SHA256,
            "strict_profile_rule": STRICT_PROFILE_RULE,
        },
    }


def profile_sha256(profile: Mapping[str, Any] | None = None) -> str:
    return sha256(canonical(profile if profile is not None else execution_profile()))


def manifest_section() -> dict[str, Any]:
    """The round-manifest flag section the 1b PR adds beside ``code.diversity_formula``."""
    return {
        "module": "benchmarks/ai-governance/identity-flag-20261023/identity_flag_pipeline.py",
        "module_sha256": file_sha256(Path(__file__)),
        "version": 1,
        "schema": FLAGS_SCHEMA,
        "profile_sha256": profile_sha256(),
        "prompt_sha256": file_sha256(PROMPT_PATH),
        "response_schema_sha256": response_schema_sha256(),
        "subscorer_sha256": SUBSCORER_V3_SHA256,
        "entry_profile_sha256": ENTRY_PROFILE_RUST_SHA256,
        "strict_profile_rule": STRICT_PROFILE_RULE,
        "shadow_only": True,
    }


def deterministic_side_matches() -> bool:
    """The files behind the deterministic pins still have the pinned bytes."""
    return (
        file_sha256(SUBSCORER_PATH) == SUBSCORER_V3_SHA256
        and file_sha256(ENTRY_PROFILE_RUST_PATH) == ENTRY_PROFILE_RUST_SHA256
        and file_sha256(ENTRY_PROFILE_PYTHON_PATH) == ENTRY_PROFILE_PYTHON_SHA256
    )


# --- Request builder (reuses the 2026-09-03 layout) ------------------------

def packet_set_sha256(packets: Sequence[Mapping[str, Any]]) -> str:
    rows = sorted(packets, key=lambda p: p["validator_id"])
    lines = "".join(f"{p['network']}|{p['validator_id']}|{p['packet_sha256']}\n" for p in rows)
    return sha256(lines)


def _user_message(packet: Mapping[str, Any], packet_set: str) -> str:
    return (
        f"network: {packet['network']}\n"
        f"validator_id: {packet['validator_id']}\n"
        f"packet_sha256: {packet['packet_sha256']}\n"
        f"packet_set_sha256: {packet_set}\n\n"
        + BEGIN_MARK + packet["packet_text"] + END_MARK
    )


def build_requests(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Request rows in a fixed order (by validator id), padded to whole batches."""
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    schema = response_schema()
    packet_set = packet_set_sha256(packets)
    rows: list[dict[str, Any]] = []
    for packet in sorted(packets, key=lambda p: p["validator_id"]):
        if sha256(packet["packet_text"].encode("utf-8")) != packet["packet_sha256"]:
            raise ValueError(f"packet bytes do not match packet_sha256 for {packet['validator_id']}")
        body = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": _user_message(packet, packet_set)},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": MAX_TOKENS,
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": RESPONSE_SCHEMA_NAME, "strict": True, "schema": schema}},
        }
        rows.append({"slot": len(rows), "validator_id": packet["validator_id"], "network": packet["network"],
                     "packet_sha256": packet["packet_sha256"], "padding": False,
                     "request_sha256": sha256(canonical(body)), "body": body})
    for index in range((-len(rows)) % BATCH_SIZE):
        body = {"model": MODEL, "messages": [
            {"role": "system", "content": "Output exactly " + PAD_CONTENT + " and nothing else."},
            {"role": "user", "content": f"pad {index}"}],
            "temperature": 0, "top_p": 1, "max_tokens": 64,
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "pad", "strict": True, "schema": PAD_SCHEMA}}}
        rows.append({"slot": len(rows), "validator_id": f"PAD-{index}", "network": "pad",
                     "packet_sha256": None, "padding": True,
                     "request_sha256": sha256(canonical(body)), "body": body})
    return rows


def requests_sha256(requests: Sequence[Mapping[str, Any]]) -> str:
    return sha256(canonical(list(requests)))


# --- Per-slot checks and the replay comparison (spec §5) -------------------

def check_response(request: Mapping[str, Any], content: str, finish_reason: str) -> tuple[str, dict | None]:
    """Admissibility class of one slot's content, plus the parsed response if admissible."""
    if finish_reason != "stop":
        return "truncated", None
    if not isinstance(content, str):
        return "invalid", None
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, RecursionError):
        return "invalid", None
    if request["padding"]:
        return ("admissible", parsed) if content == PAD_CONTENT else ("invalid", None)
    keys = {"validator_id", "packet_sha256", "classification", "cited_fields", "reason_codes"}
    if not isinstance(parsed, dict) or set(parsed) != keys:
        return "invalid", None
    if parsed["validator_id"] != request["validator_id"] or parsed["packet_sha256"] != request["packet_sha256"]:
        return "wrong_echo", None
    classification, cited, reasons = parsed["classification"], parsed["cited_fields"], parsed["reason_codes"]
    if (not isinstance(cited, list) or not isinstance(reasons, list)
            or not all(isinstance(v, str) for v in cited + reasons)):
        return "invalid", None
    if classification not in CLASSIFICATIONS:
        return "invalid", None
    if (not isinstance(cited, list) or not cited or cited != sorted(set(cited))
            or any(field not in CITED_FIELDS for field in cited)):
        return "invalid", None
    if not isinstance(reasons, list) or reasons != sorted(set(reasons)) or any(r not in REASON_CODES for r in reasons):
        return "invalid", None
    if (classification == "clear") != (reasons == []):
        return "invalid", None
    return "admissible", parsed


def compare_runs(requests: Sequence[Mapping[str, Any]], runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Per-slot admissibility across the four runs (spec §5).

    A run is ``{"owner": str, "results": [{"slot", "request_sha256", "content",
    "finish_reason"}]}``, the shape of the 2026-09-03 ``run_host.py`` output plus
    the owner label. Fewer than two owners with two runs each is an outage.
    """
    owners: dict[str, int] = {}
    for run in runs:
        owners[str(run.get("owner"))] = owners.get(str(run.get("owner")), 0) + 1
    outage = (len(runs) != OWNERS_REQUIRED * RUNS_PER_OWNER
              or sorted(owners.values()) != [RUNS_PER_OWNER] * OWNERS_REQUIRED)
    slots: dict[int, dict[str, Any]] = {}
    for request in requests:
        contents: list[tuple[Any, Any] | None] = []
        status = None
        for run in runs:
            row = next((r for r in run.get("results", []) if r.get("slot") == request["slot"]), None)
            if row is None:
                status = status or "missing"
                contents.append(None)
                continue
            if row.get("request_sha256") != request["request_sha256"]:
                status = status or "stale"
            contents.append((row.get("content"), row.get("finish_reason")))
        if outage:
            status = "outage"
        identical = bool(contents) and None not in contents and len(set(contents)) == 1
        if status is None and not identical:
            status = "divergent"
        parsed = None
        if status is None:
            content, finish_reason = contents[0]  # type: ignore[misc]
            status, parsed = check_response(request, content, finish_reason)
        slots[request["slot"]] = {
            "slot": request["slot"],
            "batch": request["slot"] // BATCH_SIZE,
            "validator_id": request["validator_id"],
            "packet_sha256": request["packet_sha256"],
            "padding": request["padding"],
            "request_sha256": request["request_sha256"],
            "content_sha256": [None if c is None or not isinstance(c[0], str) else sha256(c[0]) for c in contents],
            "byte_identical": identical,
            "status": status,
            "voided_by_padding_slot": None,
            "parsed": parsed,
        }
    # Spec §5 and decision 6: a padding slot that is not admissible voids its batch.
    replay_unreliable = any(s["status"] == "divergent" for s in slots.values())
    for pad in sorted((s for s in slots.values() if s["padding"] and s["status"] != "admissible"),
                      key=lambda s: s["slot"]):
        for other in slots.values():
            if other["batch"] == pad["batch"] and not other["padding"] and other["status"] == "admissible":
                other["status"] = pad["status"]
                other["voided_by_padding_slot"] = pad["slot"]
                other["parsed"] = None
    return {"outage": outage, "replay_unreliable": replay_unreliable, "slots": slots}


# --- Flags artifact (spec §7) ----------------------------------------------

def strict_profile_met(round_info: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    """``not D``: the step-3 module under the decided ``interim_domain_only`` rule.

    Decision 3 of 2026-10-23: absent domain evidence (``None``) counts as not verified.
    """
    return vep.meets_strict_profile(STRICT_PARAMETERS, {
        "current_round": round_info["round_number"],
        "domain_verified": candidate.get("domain_verified") is True,
        "history": [],
    })


def build_flags(
    *,
    round_info: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    packets: Sequence[Mapping[str, Any]],
    runs: Sequence[Mapping[str, Any]],
    expected_section: Mapping[str, Any],
    frozen_packet_set: Iterable[str] | None = None,
    mode: str = "shadow",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(flags.json, admissibility.json)`` for one round. Every failure gives no flag.

    ``candidates`` are ``{"validator_id", "domain_verified"}`` rows (the frozen
    candidate set); ``packets`` are ``{"validator_id", "network", "packet_sha256",
    "packet_text"}``; ``expected_section`` is the round manifest's flag section;
    ``frozen_packet_set`` (optional) is the packet SHA-256 set frozen at the
    round's input freeze (decision 9).
    """
    require_shadow(mode)
    requests = build_requests(packets)
    comparison = compare_runs(requests, runs)
    by_validator = {s["validator_id"]: s for s in comparison["slots"].values() if not s["padding"]}
    pins_stale = dict(expected_section) != manifest_section() or not deterministic_side_matches()
    frozen = None if frozen_packet_set is None else set(frozen_packet_set)
    pins = {
        "profile_sha256": profile_sha256(),
        "prompt_sha256": file_sha256(PROMPT_PATH),
        "response_schema_sha256": response_schema_sha256(),
        "packet_set_sha256": packet_set_sha256(packets),
        "requests_sha256": requests_sha256(requests),
        "subscorer_sha256": SUBSCORER_V3_SHA256,
        "entry_profile_sha256": ENTRY_PROFILE_RUST_SHA256,
    }
    operators = []
    counts = {name: 0 for name in ADMISSIBILITY_CLASSES}
    candidate_rows = sorted(candidates, key=lambda c: c["validator_id"])
    for candidate in candidate_rows:
        slot = by_validator.get(candidate["validator_id"])
        status = "missing" if slot is None else slot["status"]
        if pins_stale or (slot is not None and frozen is not None and slot["packet_sha256"] not in frozen):
            status = "stale"
        parsed = slot["parsed"] if slot is not None and status == "admissible" else None
        met = strict_profile_met(round_info, candidate)
        flag = vep.identity_flag(parsed["classification"] if parsed else "none", met)
        counts[status] += 1
        operators.append({
            "validator_id": candidate["validator_id"],
            "packet_sha256": slot["packet_sha256"] if slot else None,
            "identity_flag": flag,
            "model_classification": parsed["classification"] if parsed else None,
            "admissibility": status,
            "strict_profile_unmet": not met,
            "cited_fields": parsed["cited_fields"] if parsed else [],
            "reason_codes": parsed["reason_codes"] if parsed else [],
        })
    with_packet = sum(1 for c in candidate_rows if c["validator_id"] in by_validator)
    flags = {
        "schema": FLAGS_SCHEMA,
        "shadow_only": True,
        "round": dict(round_info),
        "pins": pins,
        "strict_profile_rule": STRICT_PROFILE_RULE,
        "replay_unreliable": comparison["replay_unreliable"],
        "admissibility_summary": {
            "packet_coverage": {"candidates": len(candidate_rows), "with_packet": with_packet,
                                "missing_packet": len(candidate_rows) - with_packet},
            "counts_by_class": counts,
        },
        "operators": operators,
    }
    admissibility = {
        "schema": ADMISSIBILITY_SCHEMA,
        "shadow_only": True,
        "round": dict(round_info),
        "outage": comparison["outage"],
        "pins_stale": pins_stale,
        "replay_unreliable": comparison["replay_unreliable"],
        "slots": [{k: v for k, v in s.items() if k != "parsed"}
                  for s in sorted(comparison["slots"].values(), key=lambda s: s["slot"])],
    }
    assert_shadow_artifact(flags)
    assert_shadow_artifact(admissibility)
    return flags, admissibility


def artifact_bytes(artifact: Mapping[str, Any]) -> bytes:
    """Canonical JSON: sorted keys, UTF-8, one trailing newline (spec §7)."""
    assert_shadow_artifact(artifact)
    return (canonical(artifact) + "\n").encode("utf-8")


def write_artifacts(directory: Path, flags: Mapping[str, Any], admissibility: Mapping[str, Any]) -> None:
    flags_bytes, admissibility_bytes = artifact_bytes(flags), artifact_bytes(admissibility)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "flags.json").write_bytes(flags_bytes)
    (directory / "admissibility.json").write_bytes(admissibility_bytes)
