#!/usr/bin/env python3
"""Shadow evaluation of the deterministic sub-scorers against rounds 12-19.

For every fetched frozen testnet round this script:

1. computes deterministic sub-scores for every validator from the round's
   frozen inputs (``subscorer.py`` v1);
2. runs the fork's own ``compute_final_score`` and ``select_unl``
   (the pinned module files of the read-only ``dynamic-unl-scoring``
   clone, loaded directly so no third-party dependency is needed) over
   those sub-scores, using the round's frozen selector parameters and
   frozen previous UNL from its own manifest/inputs; and
3. compares against the round's published outputs: per-dimension mean/max
   absolute delta vs the model's sub-scores, final-score deltas, the number
   of validators crossing the score-40 cutoff in either direction (the
   headline number), UNL overlap and seats changed vs the published
   selection, and cutoff-boundary cases (final within 5 of 40 under either
   scorer) listed individually.

The per-era baseline is the round's published authoritative score: the
score formula over the model's sub-scores where the round's manifest pins
``code.score_formula`` (rounds 16+), the model's overall score before that
(rounds 12-15). As an internal control the baseline scores are also fed
through the selector to confirm the published UNL reproduces exactly under
the frozen parameters before the deterministic candidate is compared.

Writes ``results.json`` (machine-readable) and ``results-tables.md``
(per-round tables). No network, no model, no third-party dependencies:
the two fork modules whose logic runs (``score_formula``,
``unl_selector``) are loaded from their pinned files with local plain
data carriers standing in for the parser's ``ScoringResult`` and
``ValidatorScore`` (field-identical, no validation logic to replicate)
and a fail-loud stand-in for the fork settings, which the evaluation
must never read because every selector parameter comes from the round's
manifest. This keeps the evaluation and its guard tests runnable under
a bare interpreter.

Fail-loud guards (regression-tested in ``test_shadow_eval.py``): the
pinned fork module files must match the round's manifest content-hash
pins,
the round's pinned ``score_cutoff`` must equal the flip line, and the
frozen-entry and published-model validator sets must match exactly —
any mismatch raises instead of narrowing the comparison silently.

``--scorer-version 2`` evaluates ``subscorer_v2.py`` instead (era-aware
consensus: the round's frozen prompt version is passed to the scorer),
writes ``results-v2.json`` / ``results-tables-v2.md``, and embeds a
per-round v1-vs-v2 comparison read from the immutable ``results.json``.

``--scorer-version 3`` evaluates the frozen ``subscorer_v3.py`` (the four
model-owned dimensions) and takes diversity from the round itself: the
fork's pinned ``diversity_formula`` over ``inputs/diversity_inputs.json``
when the manifest carries ``code.diversity_formula`` (rounds from
2026-10-09), the published model value otherwise. It refuses a fork
clone that is not at its ``origin/main``, writes ``results-v3.json`` /
``results-tables-v3.md`` with a per-round v2-vs-v3 comparison and the
automated part of the Z2 step-6 acceptance check, and by default
evaluates rounds 12-19 plus every other fetched ``rounds/testnet-r*``.

In every version, a round that pins ``code.diversity_formula`` has its
baseline computed with the formula's diversity, and the result is
cross-checked against the published ``outputs/final_scores.json``.

Usage: ``python3 shadow_eval.py [--scorer-version {1,2,3}] [--rounds N ...]``
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import subprocess
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORK_ROOT = Path.home() / "repos" / "dynamic-unl-scoring"
FORK_SERVICES = FORK_ROOT / "scoring_service" / "services"
sys.path.insert(0, str(HERE))

import subscorer  # noqa: E402
import subscorer_v2  # noqa: E402
import subscorer_v3  # noqa: E402


@dataclass
class ValidatorScore:
    """Field-identical stand-in for the pinned parser's ``ValidatorScore``.

    The pinned class declares these fields with no validators or coercion,
    so a plain carrier is behaviorally identical for the values this
    evaluation constructs.
    """

    master_key: str
    score: int
    consensus: int
    reliability: int
    software: int
    diversity: int
    identity: int
    reasoning: str


@dataclass
class ScoringResult:
    """Field-identical stand-in for the pinned parser's ``ScoringResult``."""

    validator_scores: list[ValidatorScore]
    raw_response: str
    complete: bool
    errors: list[str] = field(default_factory=list)


class _UnusedForkSettings:
    """The fork settings must never be read by this evaluation.

    ``select_unl`` falls back to settings only for parameters not passed
    explicitly; the evaluation always passes the round's frozen manifest
    parameters, so any settings read is a bug and fails loudly.
    """

    def __getattr__(self, name: str):
        raise AttributeError(
            f"fork settings.{name} was read during the shadow evaluation; "
            "every selector parameter must come from the round's manifest"
        )


def _register_stub_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules[name] = module
    parent_name, _, child = name.rpartition(".")
    if parent_name:
        setattr(sys.modules[parent_name], child, module)
    return module


def _load_pinned_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    parent_name, _, child = name.rpartition(".")
    if parent_name:
        setattr(sys.modules[parent_name], child, module)
    spec.loader.exec_module(module)
    return module


# The real files behind every module name a round manifest may pin. Pin
# verification hashes these exact files; the loader below executes the
# score-formula and selector files directly, so the logic that runs is
# the pinned fork code without the fork package's optional dependencies.
_PINNED_MODULE_FILES = {
    "scoring_service.services.response_parser": FORK_SERVICES / "response_parser.py",
    "scoring_service.services.score_formula": FORK_SERVICES / "score_formula.py",
    "scoring_service.services.unl_selector": FORK_SERVICES / "unl_selector.py",
    "scoring_service.services.diversity_formula": FORK_SERVICES / "diversity_formula.py",
}

_register_stub_module("scoring_service")
_register_stub_module("scoring_service.services")
_register_stub_module("scoring_service.config").settings = _UnusedForkSettings()
_parser_stub = _register_stub_module("scoring_service.services.response_parser")
_parser_stub.ValidatorScore = ValidatorScore
_parser_stub.ScoringResult = ScoringResult

compute_final_score = _load_pinned_module(
    "scoring_service.services.score_formula",
    _PINNED_MODULE_FILES["scoring_service.services.score_formula"],
).compute_final_score
select_unl = _load_pinned_module(
    "scoring_service.services.unl_selector",
    _PINNED_MODULE_FILES["scoring_service.services.unl_selector"],
).select_unl
# Only the pure ``compute_diversity`` and the published constants run; the
# module's pydantic-based ``apply_diversity_formula`` is never called.
diversity_formula = _load_pinned_module(
    "scoring_service.services.diversity_formula",
    _PINNED_MODULE_FILES["scoring_service.services.diversity_formula"],
)

ROUNDS = tuple(range(12, 20))
CUTOFF_LINE = 40
BOUNDARY_MARGIN = 5
DIMENSIONS = subscorer.DIMENSIONS


def _load(round_dir: Path, rel_path: str) -> dict:
    return json.loads((round_dir / rel_path).read_text())


def _verify_code_pins(code: dict) -> None:
    """Fail loudly if a pinned fork module drifted from the round's pins.

    Every round's execution manifest content-hash-pins the parser, selector,
    and (formula-era) score-formula modules. The evaluation loads today's
    fork clone; if that clone has moved past the pinned content, the numbers
    it computes would no longer describe the frozen round.
    """
    for key in ("parser", "selector", "score_formula", "diversity_formula"):
        pin = code.get(key)
        if pin is None:
            continue
        module_file = _PINNED_MODULE_FILES.get(pin["module"])
        if module_file is None:
            raise ValueError(
                f"round pins unrecognized fork module {pin['module']!r}"
            )
        digest = hashlib.sha256(module_file.read_bytes()).hexdigest()
        if digest != pin["content_sha256"]:
            raise ValueError(
                f"fork module {pin['module']} (sha256 {digest}) does not match "
                f"the round's pinned {key} hash {pin['content_sha256']}; the "
                "fork clone has drifted from the frozen round"
            )


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def fork_checkout_state(root: Path = FORK_ROOT) -> dict:
    """The fork clone's HEAD against its last-fetched ``origin/main``."""
    commit = _git(root, "rev-parse", "HEAD")
    try:
        origin = _git(root, "rev-parse", "--verify", "refs/remotes/origin/main")
    except subprocess.CalledProcessError:
        origin = None
    behind = (
        int(_git(root, "rev-list", "--count", f"{commit}..{origin}")) if origin else None
    )
    return {"commit": commit, "origin_main": origin, "behind_origin_main": behind}


def require_current_fork(state: dict) -> None:
    """Refuse a fork clone that is not at its ``origin/main``."""
    if state["origin_main"] is None:
        raise ValueError("fork clone has no origin/main ref; fetch it first")
    if state["behind_origin_main"]:
        raise ValueError(
            f"fork clone {state['commit'][:7]} is {state['behind_origin_main']} "
            f"commits behind origin/main {state['origin_main'][:7]}; pull it "
            "(git pull --ff-only origin main) before evaluating"
        )
    if state["commit"] != state["origin_main"]:
        raise ValueError(
            f"fork clone {state['commit'][:7]} is not at origin/main "
            f"{state['origin_main'][:7]}"
        )


def _round_diversity(round_dir: Path, code: dict, master_keys) -> dict[str, int] | None:
    """Diversity from the round's pinned fork formula, or None before it."""
    pin = code.get("diversity_formula")
    if pin is None:
        return None
    module_params = diversity_formula.diversity_formula_parameters()
    if (
        pin.get("version") != diversity_formula.DIVERSITY_FORMULA_VERSION
        or pin.get("parameters") != module_params
    ):
        raise ValueError(
            f"{round_dir.name} pins diversity_formula version {pin.get('version')} "
            f"parameters {pin.get('parameters')}, but the loaded fork module has "
            f"diversity_formula parameters {module_params} at version "
            f"{diversity_formula.DIVERSITY_FORMULA_VERSION}"
        )
    inputs = _load(round_dir, pin["inputs"])
    by_key = {entry["master_key"]: entry for entry in inputs["validators"]}
    missing = sorted(set(master_keys) - set(by_key))
    if missing:
        raise ValueError(f"{round_dir.name}: diversity inputs carry no entry for {missing}")
    return {
        mk: diversity_formula.compute_diversity(
            by_key[mk]["country_validators"],
            by_key[mk]["provider_validators"],
            inputs["resolved_endpoints"],
        )
        for mk in master_keys
    }


def _check_published_final_scores(
    round_dir: Path, base_final: dict, computed_diversity: dict | None, model_scores: dict
) -> bool | None:
    """Cross-check the baseline against ``outputs/final_scores.json``.

    Required when the round pins the diversity formula; checked when
    present otherwise. Returns None when there is nothing to check.
    """
    path = round_dir / "outputs" / "final_scores.json"
    if computed_diversity is None and not path.exists():
        return None
    published = {e["master_key"]: e for e in _load(round_dir, "outputs/final_scores.json")["scores"]}
    if set(published) != set(base_final):
        raise ValueError(
            f"{round_dir.name}: outputs/final_scores.json validator set differs "
            "from the published model scores"
        )
    disagree = sorted(
        mk for mk, entry in published.items()
        if entry["final_score"] != base_final[mk]
        or (
            computed_diversity is not None
            and (
                entry.get("diversity") != computed_diversity[mk]
                or entry.get("model_diversity") != model_scores[mk]["diversity"]
            )
        )
    )
    if disagree:
        raise ValueError(
            f"{round_dir.name}: outputs/final_scores.json disagrees with the "
            f"pinned formula chain for {disagree}"
        )
    return True


def _model_scores(round_dir: Path) -> dict:
    return {
        v["master_key"]: v
        for v in _load(round_dir, "outputs/validator_scores.json")["validator_scores"]
    }


def candidate_subscores(round_dir: Path, scorer_version: int = 1) -> dict[str, dict[str, int]]:
    """The deterministic candidate's five sub-scores per master key.

    v3 scores four dimensions and takes diversity from the round: the
    pinned fork formula where the manifest carries it, the published model
    value (the one the round's selection used) before that.
    """
    code = _load(round_dir, "runtime/execution_manifest.json")["code"]
    validator_map = _load(round_dir, "inputs/validator_map.json")
    model_scores = _model_scores(round_dir)
    entries = subscorer.load_round_entries(round_dir)
    if scorer_version == 3:
        det_by_vid = subscorer_v3.score_round(entries, code["prompt"]["version"])
    elif scorer_version == 2:
        det_by_vid = subscorer_v2.score_round(entries, code["prompt"]["version"])
    else:
        det_by_vid = subscorer.score_round(entries)
    if len(det_by_vid) != len(entries):
        raise ValueError(
            f"{round_dir.name}: duplicate validator_id in the frozen entries "
            f"collapsed {len(entries)} entries to {len(det_by_vid)} scores"
        )
    det = {
        validator_map[vid]["master_key"]: dims for vid, dims in det_by_vid.items()
    }
    if len(det) != len(det_by_vid):
        raise ValueError(
            f"{round_dir.name}: duplicate master_key in validator_map "
            f"collapsed {len(det_by_vid)} scores to {len(det)}"
        )
    frozen_only = sorted(set(det) - set(model_scores))
    model_only = sorted(set(model_scores) - set(det))
    if frozen_only or model_only:
        raise ValueError(
            f"{round_dir.name}: validator sets differ between the frozen "
            f"entries and the published model scores (frozen-only "
            f"{frozen_only}, model-only {model_only})"
        )
    if scorer_version == 3:
        diversity = _round_diversity(round_dir, code, sorted(det)) or {
            mk: model_scores[mk]["diversity"] for mk in det
        }
        det = {mk: {**dims, "diversity": diversity[mk]} for mk, dims in det.items()}
    return det


def _select(finals: dict[str, int], previous_unl: list[str], params: dict) -> list[str]:
    result = ScoringResult(
        validator_scores=[
            ValidatorScore(
                master_key=mk, score=score, consensus=0, reliability=0,
                software=0, diversity=0, identity=0, reasoning="",
            )
            for mk, score in finals.items()
        ],
        raw_response="", complete=True, errors=[],
    )
    return select_unl(
        result,
        previous_unl=previous_unl,
        cutoff=params["score_cutoff"],
        max_size=params["max_size"],
        min_gap=params["min_score_gap"],
    ).unl


def evaluate_round(round_dir: Path, scorer_version: int = 1) -> dict:
    manifest = _load(round_dir, "runtime/execution_manifest.json")
    code = manifest["code"]
    _verify_code_pins(code)
    params = code["selector"]["parameters"]
    if params["score_cutoff"] != CUTOFF_LINE:
        raise ValueError(
            f"{round_dir.name} pins score_cutoff {params['score_cutoff']} but "
            f"this evaluation computes cutoff flips against {CUTOFF_LINE}"
        )
    formula_era = "score_formula" in code
    if "diversity_formula" in code and not formula_era:
        raise ValueError(
            f"{round_dir.name} pins diversity_formula without score_formula"
        )
    previous_unl = _load(round_dir, "inputs/previous_unl.json")["previous_unl"]
    published_unl = _load(round_dir, "outputs/selected_unl.json")["unl"]
    if len(published_unl) > params["max_size"]:
        raise ValueError(
            f"{round_dir.name}: published UNL has {len(published_unl)} seats but "
            f"the round pins max_size {params['max_size']}"
        )
    model_scores = _model_scores(round_dir)

    det = candidate_subscores(round_dir, scorer_version)

    common = sorted(set(det) & set(model_scores))
    computed_diversity = _round_diversity(round_dir, code, common)
    report: dict = {
        "round": round_dir.name,
        "prompt_version": code["prompt"]["version"],
        "selector_parameters": params,
        "baseline": "formula(model sub-scores)" if formula_era else "model overall score",
        "validators": len(det),
        "validators_compared": len(common),
    }
    if computed_diversity is not None:
        report["baseline"] = "formula(model sub-scores, formula diversity)"

    # Per-dimension deltas: deterministic vs model sub-scores.
    report["dimension_deltas"] = {
        dim: {
            "mean_abs": round(
                statistics.mean(
                    abs(det[mk][dim] - model_scores[mk][dim]) for mk in common
                ),
                2,
            ),
            "max_abs": max(abs(det[mk][dim] - model_scores[mk][dim]) for mk in common),
        }
        for dim in DIMENSIONS
    }

    # Final scores: deterministic candidate vs the round's published
    # authoritative baseline.
    det_final = {
        mk: compute_final_score(*(det[mk][dim] for dim in DIMENSIONS)) for mk in common
    }
    if formula_era:
        base_final = {
            mk: compute_final_score(
                *(
                    computed_diversity[mk]
                    if dim == "diversity" and computed_diversity is not None
                    else model_scores[mk][dim]
                    for dim in DIMENSIONS
                )
            )
            for mk in common
        }
    else:
        base_final = {mk: model_scores[mk]["score"] for mk in common}
    final_scores_checked = _check_published_final_scores(
        round_dir, base_final, computed_diversity, model_scores
    )

    final_deltas = sorted(abs(det_final[mk] - base_final[mk]) for mk in common)
    report["final_score_deltas"] = {
        "mean_abs": round(statistics.mean(final_deltas), 2),
        "max_abs": final_deltas[-1],
    }

    # Cutoff flips (the headline number).
    flips_out = sorted(
        mk for mk in common
        if base_final[mk] >= CUTOFF_LINE > det_final[mk]
    )
    flips_in = sorted(
        mk for mk in common
        if det_final[mk] >= CUTOFF_LINE > base_final[mk]
    )
    report["cutoff_flips"] = {
        "eligible_to_ineligible": len(flips_out),
        "ineligible_to_eligible": len(flips_in),
        "total": len(flips_out) + len(flips_in),
        "flipped_validators": [
            {
                "master_key": mk,
                "direction": direction,
                "baseline_final": base_final[mk],
                "deterministic_final": det_final[mk],
            }
            for direction, keys in (
                ("eligible->ineligible", flips_out),
                ("ineligible->eligible", flips_in),
            )
            for mk in keys
        ],
    }

    # Internal control: the baseline scores must reproduce the published UNL
    # under the round's own frozen parameters and previous UNL.
    control_unl = _select(base_final, previous_unl, params)
    report["baseline_reproduces_published_unl"] = set(control_unl) == set(published_unl)

    # Deterministic candidate selection vs the published UNL.
    det_unl = _select(det_final, previous_unl, params)
    report["published_unl_size"] = len(published_unl)
    report["deterministic_unl_size"] = len(det_unl)
    report["unl_overlap"] = len(set(det_unl) & set(published_unl))
    report["unl_seats_changed"] = len(set(det_unl) ^ set(published_unl)) // 2
    report["seats_gained"] = sorted(set(det_unl) - set(published_unl))
    report["seats_lost"] = sorted(set(published_unl) - set(det_unl))

    # Cutoff-boundary cases: final within BOUNDARY_MARGIN of the cutoff
    # under either scorer, listed individually.
    report["cutoff_boundary_cases"] = [
        {
            "master_key": mk,
            "baseline_final": base_final[mk],
            "deterministic_final": det_final[mk],
            "model_subscores": {dim: model_scores[mk][dim] for dim in DIMENSIONS},
            "deterministic_subscores": {dim: det[mk][dim] for dim in DIMENSIONS},
            "flipped": base_final[mk] >= CUTOFF_LINE > det_final[mk]
            or det_final[mk] >= CUTOFF_LINE > base_final[mk],
        }
        for mk in common
        if abs(base_final[mk] - CUTOFF_LINE) <= BOUNDARY_MARGIN
        or abs(det_final[mk] - CUTOFF_LINE) <= BOUNDARY_MARGIN
    ]

    if scorer_version == 3:
        # The automated part of the Z2 step-6 acceptance check; explaining
        # every eligible->ineligible flip and seat change stays a review.
        report["subscorer_v3_sha256"] = hashlib.sha256(
            Path(subscorer_v3.__file__).read_bytes()
        ).hexdigest()
        report["diversity_source"] = (
            "code.diversity_formula" if computed_diversity is not None else "model"
        )
        report["final_scores_match_published"] = final_scores_checked
        overlap_min = len(published_unl) - 1
        acceptance = {
            "internal_control": report["baseline_reproduces_published_unl"],
            "no_ineligible_to_eligible": not flips_in,
            "unl_overlap_min": overlap_min,
            "unl_overlap_ok": report["unl_overlap"] >= overlap_min,
        }
        acceptance["automated_pass"] = all(
            acceptance[k]
            for k in ("internal_control", "no_ineligible_to_eligible", "unl_overlap_ok")
        )
        report["acceptance"] = acceptance
    return report


def _round_table(report: dict) -> str:
    dims = report["dimension_deltas"]
    lines = [
        f"### {report['round']} (prompt {report['prompt_version']}, "
        f"baseline: {report['baseline']}, gap {report['selector_parameters']['min_score_gap']})",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Validators compared | {report['validators_compared']} |",
        *(
            f"| {dim} mean/max abs delta | {dims[dim]['mean_abs']} / {dims[dim]['max_abs']} |"
            for dim in DIMENSIONS
        ),
        f"| Final score mean/max abs delta | {report['final_score_deltas']['mean_abs']} "
        f"/ {report['final_score_deltas']['max_abs']} |",
        f"| Cutoff flips (out / in) | {report['cutoff_flips']['eligible_to_ineligible']} "
        f"/ {report['cutoff_flips']['ineligible_to_eligible']} |",
        f"| Baseline reproduces published UNL | {report['baseline_reproduces_published_unl']} |",
        f"| UNL overlap / seats changed | {report['unl_overlap']}"
        f"/{report['published_unl_size']} / {report['unl_seats_changed']} |",
    ]
    if "acceptance" in report:
        lines += [
            f"| Diversity source | {report['diversity_source']} |",
            f"| Automated acceptance (control, no in-flip, overlap >= "
            f"{report['acceptance']['unl_overlap_min']}) | "
            f"{'pass' if report['acceptance']['automated_pass'] else 'FAIL'} |",
        ]
    lines.append("")
    if report["cutoff_boundary_cases"]:
        lines += [
            "Cutoff-boundary cases (final within 5 of 40 under either scorer):",
            "",
            "| Validator | Baseline final | Deterministic final | Flipped |",
            "|---|---|---|---|",
            *(
                f"| `{c['master_key'][:12]}...` | {c['baseline_final']} "
                f"| {c['deterministic_final']} | {'YES' if c['flipped'] else 'no'} |"
                for c in report["cutoff_boundary_cases"]
            ),
            "",
        ]
    else:
        lines += ["No cutoff-boundary cases.", ""]
    return "\n".join(lines)


def _previous_comparison(reports: list[dict], version: int) -> dict | None:
    """Per-round comparison with the previous version's immutable results."""
    prev = version - 1
    prev_name = "results.json" if prev == 1 else f"results-v{prev}.json"
    prev_path = HERE / prev_name
    if not prev_path.exists():
        return None
    prev_rounds = {r["round"]: r for r in json.loads(prev_path.read_text())["rounds"]}
    a, b = f"v{prev}", f"v{version}"
    rounds = []
    for r in reports:
        old = prev_rounds.get(r["round"])
        if old is None:
            continue
        rounds.append({
            "round": r["round"],
            f"cutoff_flips_{a}": old["cutoff_flips"]["total"],
            f"cutoff_flips_{b}": r["cutoff_flips"]["total"],
            f"unl_overlap_{a}": old["unl_overlap"],
            f"unl_overlap_{b}": r["unl_overlap"],
            "published_unl_size": r["published_unl_size"],
            "dimension_mean_abs_delta": {
                dim: {
                    a: old["dimension_deltas"][dim]["mean_abs"],
                    b: r["dimension_deltas"][dim]["mean_abs"],
                }
                for dim in DIMENSIONS
            },
        })
    return {
        "baseline_results": f"{prev_name} (sub-scorers {a}, immutable)",
        "rounds": rounds,
        f"total_cutoff_flips_{a}": sum(r[f"cutoff_flips_{a}"] for r in rounds),
        f"total_cutoff_flips_{b}": sum(r[f"cutoff_flips_{b}"] for r in rounds),
    }


def _fetched_rounds() -> list[int]:
    rounds_dir = HERE / "rounds"
    if not rounds_dir.exists():
        return []
    return [
        int(path.name.removeprefix("testnet-r"))
        for path in rounds_dir.glob("testnet-r*")
        if path.name.removeprefix("testnet-r").isdigit()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorer-version", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--rounds", type=int, nargs="+", default=None)
    args = parser.parse_args()
    scorer_version = args.scorer_version
    suffix = "" if scorer_version == 1 else f"-v{scorer_version}"
    if args.rounds is not None:
        round_numbers = sorted(set(args.rounds))
    elif scorer_version == 3:
        round_numbers = sorted(set(ROUNDS) | set(_fetched_rounds()))
    else:
        round_numbers = list(ROUNDS)
    fork_state = None
    if scorer_version == 3:
        fork_state = fork_checkout_state(FORK_ROOT)
        require_current_fork(fork_state)

    rounds_dir = HERE / "rounds"
    reports, failures = [], []
    for round_number in round_numbers:
        round_dir = rounds_dir / f"testnet-r{round_number}"
        if not round_dir.exists():
            failures.append(f"testnet-r{round_number}: not fetched")
            continue
        try:
            reports.append(evaluate_round(round_dir, scorer_version))
        except FileNotFoundError as exc:
            failures.append(f"testnet-r{round_number}: missing artifact {exc.filename}")

    results = {
        "evaluation": (
            f"deterministic sub-scorers v{scorer_version} shadow evaluation"
        ),
        "cutoff_line": CUTOFF_LINE,
        "boundary_margin": BOUNDARY_MARGIN,
        "rounds": reports,
        "failures": failures,
        "headline": {
            "total_cutoff_flips": sum(r["cutoff_flips"]["total"] for r in reports),
            "rounds_evaluated": len(reports),
        },
    }
    if fork_state is not None:
        results["fork"] = {"repository": "postfiatorg/dynamic-unl-scoring", **fork_state}
        results["subscorer_v3_sha256"] = hashlib.sha256(
            Path(subscorer_v3.__file__).read_bytes()
        ).hexdigest()
        results["headline"]["rounds_passing_automated_acceptance"] = sum(
            r["acceptance"]["automated_pass"] for r in reports
        )
    if scorer_version != 1:
        comparison = _previous_comparison(reports, scorer_version)
        if comparison is not None:
            results[f"v{scorer_version - 1}_comparison"] = comparison
    (HERE / f"results{suffix}.json").write_text(json.dumps(results, indent=1) + "\n")

    tables = [
        f"# Deterministic sub-scorer v{scorer_version} shadow evaluation "
        "— per-round tables"
        if scorer_version != 1
        else "# Deterministic sub-scorer shadow evaluation — per-round tables",
        "",
        f"Rounds evaluated: {len(reports)}; fetch/evaluation failures: "
        f"{failures if failures else 'none'}.",
        "",
        *(_round_table(r) for r in reports),
    ]
    (HERE / f"results-tables{suffix}.md").write_text("\n".join(tables))

    for r in reports:
        print(
            f"{r['round']}: flips {r['cutoff_flips']['total']} "
            f"(out {r['cutoff_flips']['eligible_to_ineligible']}, "
            f"in {r['cutoff_flips']['ineligible_to_eligible']}), "
            f"UNL overlap {r['unl_overlap']}/{r['published_unl_size']}, "
            f"control {'OK' if r['baseline_reproduces_published_unl'] else 'MISMATCH'}"
        )
    if failures:
        print("failures:", failures)
    print(f"total cutoff flips: {results['headline']['total_cutoff_flips']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
