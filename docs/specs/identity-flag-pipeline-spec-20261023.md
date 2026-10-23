# Identity flag pipeline: specification

Date: 23 October 2026. Status: **locked**. The Text Improvement Harness full gate
passed on 2026-10-23 with an average of 86.33/100 (GPT 85.40, Fable 85.60,
GLM 88.00; five runs per lane; run group `identity-flag-pipeline-spec-20261023`).
The scored content SHA-256 is
`6b68d8e7a63510525fd5a3504c7d798438491082d80f035a38021cb11547cc16`, the document
before this status line. The first gate scored 85.67. One improvement pass, a
direct OpenRouter call to `openai/gpt-5.6-sol-pro` with the harness critiques,
preceded the passing gate. This is step 2 of the
[Z2 advisory flag execution plan](../plans/active/z2-advisory-flag-execution-plan-20261022.md).

## 1. Outcome and scope

The [AI governance direction](../governance/ai-governance-direction-20260903.md),
confirmed on 2026-10-20 (row 1 of the
[pending operator decisions](../governance/pending-operator-decisions.md)), leaves the model one job.
It classifies whether an operator's frozen identity packet establishes a real
operator. That classification can do one thing only: send a candidate to the
strict entry profile. Everything model-derived stays `SHADOW_ONLY` until the
recorded promotion gates pass.

This specification fixes:

- the typed `identity_flag` and its two values;
- the rule that turns a model classification into a flag;
- the pinned execution profile and where each pin is recorded;
- the two-owner byte-convergent replay that makes a classification admissible;
- the data contract with the strict entry profile of step 3;
- the `SHADOW_ONLY` invariant of step 5;
- the shadow and binding failure policy, under which every failure yields no flag;
- the acceptance tests the implementation must have.

**Non-goals:**

- No flag model run and no GPU rental.
- No prompt text. Its bytes and hash are fixed in the package (step 2's second half).
- No code.
- No change to the score formula, the selector, the v3 sub-scorer (frozen, SHA-256
  `f71f29ddf00c3825447fc19034340d4ef714b9668345c51e6872586a844c5dc5`) or any
  fork artifact.
- No promotion of anything out of shadow.

## 2. Definitions

- **Round.** One fork scoring round, with its input freeze, frozen candidate
  set and round manifest.
- **Operator.** A validator in the round's frozen candidate set, identified by
  its master key.
- **Packet.** The frozen Markdown identity packet of an operator
  ([identity packets](../governance/validator-identity-packets.md)), identified by
  its SHA-256. A packet set is the frozen set of packets with its own SHA-256.
- **Packet coverage.** The identity-packet runbook builds a packet from public
  evidence for every candidate in the frozen candidate set. Operators do not
  submit packets. A candidate without a packet is a pipeline coverage gap. It
  is counted and reported for that round.
- **Model classification `M`.** The pinned flag model's typed answer for one
  operator: `clear` or `flag`. It exists only if it is admissible (§5).
- **Strict-profile result `D`.** Whether the operator does *not* yet meet the
  strict entry profile, computed by pinned integer code from the round's frozen
  evidence. Its identity input is the frozen v3 sub-scorer's identity sub-score:
  80 if and only if the domain is verified (`subscorer_v3.py`, `score_identity`).
  `D` never reads `M` or a flag.
- **Strict-profile rule.** The rule used to compute `D`, recorded as
  `interim_domain_only` or `entry_profile_v1`.
- **`identity_flag`.** The published per-operator bit (§3).
- **No flag.** `identity_flag = clear`, with the reason recorded in
  `admissibility`. A failure never produces `flag`.
- **Replay unreliable.** A round for which any scoring or padding slot diverges.
  It is recorded in `flags.json` and surfaced in the weekly record.

## 3. The typed `identity_flag`

There are exactly two values.

| Value | Meaning | Effect (`SHADOW_ONLY` until promotion) |
| --- | --- | --- |
| `flag` | The admissible model classification says the packet does not establish a real organization or person behind the claimed identity, or that the claimed institution and domain contradict the cited evidence. **And** `D` says the operator does not yet meet the strict entry profile. | For a non-incumbent, report that it would be held from a new seat in the fork, or from trust-view membership in l1v2, until the strict profile is met. A flagged incumbent is unaffected. |
| `clear` | Every other case: the model says `clear`, `D` says the strict profile is met, or the classification is missing, divergent or otherwise inadmissible. | The standard profile applies, as in the fork's configuration today. |

In binding mode after promotion, the same profile choice applies directly. A
flagged non-incumbent candidate is held from a new seat in the fork, or from
trust-view membership in l1v2, until the strict profile is met. A flagged
incumbent is unaffected.

**What a flag can never do.** It cannot lower a score, remove an incumbent,
change a threshold or block a round. Scores, thresholds and rounds never
change. An incumbent that is flagged keeps its seat. A flag is recomputed from
the round's packet every round.

## 4. The flag rule

```text
identity_flag(op) = flag   if M(op) is admissible and M(op) = flag
                              and D(op) = true (strict profile not met)
                    clear  otherwise
```

Absent evidence alone can never produce a flag. A flag always needs an
affirmative, admissible model classification of `flag`, as well as `D = true`.

**Where `D` comes from:**

- From step 3 on: `D(op) = not meets_strict_profile(op)`, as defined by the step-3
  module. The proposed defaults are a verified domain (v3 identity sub-score 80)
  **and** four consecutive clean rounds.
- Until step 3's module hash is pinned: `D(op) = (v3 identity sub-score != 80)`.
  This is the interim domain-only `D`.

The definition of `D` beyond the interim domain criterion, including the
definition of a clean round, belongs to step 3. This pipeline consumes that
definition only as a pure, hash-pinned function. The selected rule is recorded
in `strict_profile_rule`.

**Why both sides must agree:**

1. The model alone never produces an effect. Every flag needs a second judgment
   that any operator can recompute from frozen evidence with pinned integer code.
2. A flag only reaches operators that the strict profile would hold anyway.
   A model flag on an operator who already meets the strict profile changes
   nothing, so it is not published as a flag.
3. It avoids the failure the plan records. "Legitimacy score 0 = flag" would
   have flagged 33 of 55 validators on 2026-09-03, including all 20 PostFiat
   validators and 23 identities the packets call established or likely. A
   recognition prompt is not a fabrication test.

### 4.1 Worked example: the 2026-09-03 corpus

The [packet replay of 2026-09-03](../governance/identity-packet-replay-results-20260903.md)
covers 55 validators: 35 XRPL and 20 PostFiat. It used the institution-legitimacy
prompt, not a flag prompt. No `identity_flag` model output exists, so the model
side is shown with two stand-ins. The first is a legitimacy score of 0. The
second is the packet research's "not established" (no canonical entity). The
interim domain-only `D` is used, because clean rounds cannot be computed from
the corpus.

Frozen facts per validator (`validator-identity-packets-20260901/index.json`
and `identity-packet-replay-20260903/outputs/primary-run1.json`):

| Group | Validators | Packet identity | Legitimacy score | Domain verified (frozen evidence) |
| --- | ---: | --- | --- | --- |
| PostFiat | 10 | established or likely | 0 | yes |
| PostFiat | 10 | not established | 0 | yes |
| XRPL | 13 | established or likely | 0 | not recorded |
| XRPL | 22 | established or likely | 1–100 | not recorded (16 claim a domain, 6 none) |

What each rule would have produced:

| Rule | Flags | PostFiat | Established or likely |
| --- | ---: | ---: | ---: |
| Legitimacy score 0 = flag | 33 | 20 | 23 |
| Packet "not established" = flag | 10 | 10 | 0 |
| **This rule**, model side = score 0, interim `D` | 13 | 0 | 13 |
| **This rule**, model side = "not established", interim `D` | **0** | 0 | 0 |

How to read it:

- **PostFiat validators.** All 20 have verified domains, so `D` is false for every
  one of them, and this rule flags none of them under either stand-in.
- **The 13 XRPL validators.** They appear only because the corpus records no XRPL
  domain verification. That is an artifact of missing evidence. A real PostFiat
  candidate carries the fork's `domain_verified` value.
- **Clean rounds.** The full `D` of step 3 adds the clean-round criterion. A
  validator with fewer than four clean rounds would then have `D` true, so a model
  flag would reach it.
- **Limits.** These counts are descriptive. They are not a calibration of the
  future flag prompt.

The 2026-09-03 replay had identical bytes for 55/55 validator slots and 9/9
padding slots. This fact describes that replay only.

## 5. Two-owner byte-convergent replay

**Owners and runs:**

- Two GPU hosts rented from two distinct owners. The provider host IDs must
  differ, as on 2026-09-03.
- Two runs per host, so four runs in total.
- Independent organizations are a promotion gate (§8), not a step-2 requirement.

**What they replay:** the exact request bytes of the round (`requests.json`,
SHA-256 pinned), in the fixed batch schedule, with the fixed padding slots.

**Checks on each slot, before any comparison.** A slot that fails any check is
inadmissible.

- `finish_reason` is `stop`. A `length` finish is a truncation.
- The content parses as JSON and matches the response schema exactly. No
  additional properties are allowed.
- The response echoes the request's `validator_id` and `packet_sha256`.
- `classification` is `clear` or `flag`.
- `cited_fields` is non-empty, sorted, has no duplicates, and is a subset of the
  packet's closed field list.
- `reason_codes` is drawn from the closed list: empty for `clear`, at least one
  for `flag`.

**The byte-equality rule.** For every slot, two things must be identical across
all four runs: the request SHA-256, and the raw UTF-8 bytes of
`choices[0].message.content`. The comparator checks the first owner's first run
against the other three, as `compare_runs.py:40-69` does.

**Divergence: no flag.**

- If a slot's content differs in any run, or the slot is missing from any run,
  that operator's `M` is inadmissible.
- If a padding slot diverges, every operator in its batch is inadmissible. A
  padding divergence means the batch's numerics were not deterministic.
- If fewer than four runs complete (an outage), there are zero flags for the round.
- Any scoring or padding divergence sets `replay_unreliable` to `true`. The
  weekly record surfaces that status.

## 6. Pinned execution profile

Every pin below is recorded in the flag artifact and in the round manifest's
flag section. The section name is fixed in the 1b PR, beside `code.diversity_formula`.
The profile hash is the SHA-256 of the canonical JSON of the profile object.

| Pin | Value or source |
| --- | --- |
| Model identity | `Qwen/Qwen3.8-27B-FP8`, revision `017b9c7af6b5689d5dd426a76e0bc077eb5ca20a` (2026-09-03 profile, unchanged) |
| Runtime | `lmsysorg/sglang:nightly-dev-cu13-20260817-d91c3682@sha256:fa8774dd128600a09fd6d46670b06fb69a55dac8a3881e50ccf0916a45eb39af`, loopback-only endpoint |
| Decoding | temperature 0, top-p 1, thinking off, maximum 2,048 output tokens, seed 438916795, deterministic inference on |
| Runtime switches | radix cache, CUDA graphs and overlap scheduling off; Triton attention and linear-attention backends; chunked prefill 4096; context 32768 |
| Batching | fixed batch size 32, at most 32 running requests, fixed padding slots |
| Prompt | `postfiat.identity_flag.prompt.v1`, SHA-256 of the exact bytes (fixed in the package) |
| Response schema | `postfiat.identity_flag.model_response.v1`, SHA-256 of the canonical JSON |
| Inputs | packet-set SHA-256, each packet's SHA-256, the corpus-manifest SHA-256, the round's input-package hash, `requests.json` SHA-256 |
| Deterministic side | v3 sub-scorer SHA-256 `f71f29dd…c5dc5`; step-3 entry-profile module SHA-256 once pinned (until then `null`, with the interim `D`) |
| Replay | two distinct-owner hosts, two runs each |

## 7. Data contract with the strict entry profile (step 3)

The pipeline writes two canonical JSON artifacts per round: sorted keys, UTF-8,
operators sorted by `validator_id`.

`flags.json` (schema `postfiat.identity_flag.v1`):

```json
{
  "schema": "postfiat.identity_flag.v1",
  "shadow_only": true,
  "round": {"network": "testnet", "round_number": 0, "input_package_hash": "…"},
  "strict_profile_rule": "interim_domain_only",
  "replay_unreliable": false,
  "admissibility_summary": {
    "packet_coverage": {
      "candidates": "…",
      "with_packet": "…",
      "missing_packet": "…"
    },
    "counts_by_class": {
      "admissible": "…",
      "divergent": "…",
      "missing": "…",
      "truncated": "…",
      "invalid": "…",
      "wrong_echo": "…",
      "stale": "…",
      "outage": "…"
    }
  },
  "pins": {
    "profile_sha256": "…", "prompt_sha256": "…", "response_schema_sha256": "…",
    "packet_set_sha256": "…", "requests_sha256": "…",
    "subscorer_sha256": "f71f29dd…", "entry_profile_sha256": null
  },
  "operators": [
    {
      "validator_id": "…",
      "packet_sha256": "…",
      "identity_flag": "clear",
      "model_classification": "flag",
      "admissibility": "admissible",
      "strict_profile_unmet": false,
      "cited_fields": ["claimed_domain_and_official_urls", "public_identity"],
      "reason_codes": ["identity_not_established"]
    }
  ]
}
```

- `strict_profile_rule` is `interim_domain_only` or `entry_profile_v1`.
- `admissibility` takes one of these values: `admissible`, `divergent`,
  `missing`, `truncated`, `invalid`, `wrong_echo`, `stale`, `outage`.
- `model_classification` is `null` unless the classification is admissible.
- `admissibility_summary` gives counts for every admissibility class and packet
  coverage for the frozen candidate set.
- `replay_unreliable` is `true` when any scoring or padding slot diverges.
- The weekly record surfaces packet coverage, the admissibility summary and
  `replay_unreliable`.
- `admissibility.json` records each slot's four content SHA-256 values and
  whether they are byte-identical.

**What step 3 reads:** only `validator_id` and `identity_flag`, plus the artifact
hash. It checks the `pins` against the round manifest section first. A
mismatch, or a missing or unparsable artifact, means every operator is `clear`.
Step 3's flag input is `none`, `clear` or `flag`. `none` means the artifact is
missing, unparsable or rejected by the pin checks. `clear` is a valid
per-operator value from an accepted artifact. `none` and `clear` both select
the standard profile.

**No cycle.** `D` is step 3's `meets_strict_profile`, a pure function that takes
no flag input. The pipeline calls it to compute `identity_flag`. Step 3 then uses
`identity_flag` only to choose which profile applies.

## 8. `SHADOW_ONLY` invariant and promotion

The implementation must keep three things true:

1. **Every artifact is marked shadow.** Every flag artifact carries
   `"shadow_only": true`.
2. **Nothing binding reads a flag.** No fork selector, score formula, l1v2
   registry or trust view reads `identity_flag`.
3. **Binding mode needs a promotion record.** Binding mode is accepted only with
   a promotion record whose hash matches a recorded decision. Without one, the
   entry-profile module falls back to shadow and only reports.

**For every round:** final scores, the selected UNL and every l1v2 state are
byte-identical with and without `flags.json`.

**Promotion gates.** Promotion needs the gates the plan records: signed
reconstructable observations, three independent observers and replayers, an
open proposal lane, a pre-registered held-out evaluation with material lift and
no unsafe positive admission, hold or no-op on model deletion, a published
replay cost, and the drill set.

The model is never a liveness dependency. This specification selects the no-op
branch of “hold or no-op on model deletion.” Deleting the model behaves exactly
like running the fork without a flag pipeline: there is no flag, the standard
profile applies, and the failure is reported. A candidate that was flagged in
an earlier round is re-evaluated in every later round. If the current round has
no admissible model output, that candidate gets no flag. This rule is the same
in shadow and binding modes.

## 9. Failure policy

Every failure yields no flag for the stated scope. It selects the standard
profile and is reported. This policy is normative in both shadow and binding
modes.

| Case | Shadow mode | Binding mode |
| --- | --- | --- |
| Missing packet | No flag; standard profile; report a packet coverage gap for that candidate. | No flag; standard profile; report a packet coverage gap for that candidate. |
| Inadmissible response | No flag; standard profile; report its admissibility class for that candidate. | No flag; standard profile; report its admissibility class for that candidate. |
| Divergent scoring slot | No flag; standard profile; report divergence for that candidate and set `replay_unreliable`. | No flag; standard profile; report divergence for that candidate and set `replay_unreliable`. |
| Divergent padding slot | No flag; standard profile for its whole batch; report divergence and set `replay_unreliable`. | No flag; standard profile for its whole batch; report divergence and set `replay_unreliable`. |
| Outage | Zero flags; standard profile for the whole round; report the outage. | Zero flags; standard profile for the whole round; report the outage. |
| Stale pins | No flag; standard profile for the affected scope; report the stale pins. | No flag; standard profile for the affected scope; report the stale pins. |
| Model deletion | No flag; standard profile; report model deletion. | No flag; standard profile; report model deletion. This is the promotion gate's no-op branch. |

Detection and scope are fixed as follows.

| Failure | Detected by | Scope |
| --- | --- | --- |
| Missing output (slot absent in a run) | comparator | that operator |
| Run outage (fewer than four runs) | comparator | whole round |
| Divergent output | byte-equality rule | that operator; its whole batch if a padding slot diverges |
| Truncated, unparsable or schema-invalid response | slot checks | that operator |
| Wrong echo (`validator_id` or `packet_sha256`) | slot checks | that operator |
| Stale profile: an artifact pin differs from the round manifest section, or a packet is not in the frozen packet set | step-3 pin check | whole round (pins), or that operator (packet) |
| Operator without a packet | builder | that operator |
| Changed sub-scorer hash (not `f71f29dd…`, or not the hash the manifest pins) | pin check | whole round; any module change also restarts the plan's shadow count |
| Changed entry-profile hash | pin check | whole round |

An operator cannot choose to omit a packet. The identity-packet runbook builds
packets from public evidence for every candidate in the frozen candidate set.
A missing packet is therefore a pipeline coverage failure, not an
operator-controlled evasion path.

## 10. Acceptance tests

These cover the package under `benchmarks/ai-governance/identity-flag-<date>/`
and steps 3–5. The package tests are offline, using recorded fake responses;
there is no GPU run.

| Test | Proves |
| --- | --- |
| `test_builder_emits_identical_request_bytes_on_two_runs` | the request bytes are reproducible |
| `test_builder_covers_every_candidate_or_reports_packet_gap` | packets are runbook-built and missing packets are reported as coverage gaps |
| `test_flag_requires_model_flag_and_unmet_strict_profile` | the four-case truth table of §4 |
| `test_model_flag_alone_never_flags_an_operator_meeting_the_strict_profile` | the model alone has no effect |
| `test_absent_evidence_alone_never_produces_flag` | every flag needs an affirmative admissible model classification of `flag` |
| `test_divergent_slot_yields_no_flag_for_that_operator_only` | divergence is scoped to its operator |
| `test_padding_divergence_yields_no_flag_for_its_batch` | the batch rule |
| `test_missing_slot_yields_no_flag` | missing output |
| `test_run_outage_yields_zero_flags` | outage |
| `test_truncated_or_invalid_response_yields_no_flag` | the slot checks |
| `test_wrong_packet_echo_yields_no_flag` | the echo binding |
| `test_stale_profile_pin_yields_zero_flags` | the profile pins |
| `test_changed_subscorer_hash_yields_zero_flags` | the deterministic pin |
| `test_each_failure_changes_nothing_else` | no other operator's result moves |
| `test_flags_artifact_is_canonical_and_sorted` | byte-identical artifacts |
| `test_flags_artifact_records_strict_profile_rule` | the `D` variant is explicit |
| `test_admissibility_summary_reports_all_classes_and_packet_coverage` | per-round failures and coverage cannot be silent |
| `test_any_scoring_or_padding_divergence_marks_replay_unreliable` | divergent replay is surfaced |
| `test_worked_example_2026_09_03_counts` | §4.1's counts from the frozen corpus |
| `test_flags_never_change_scores_or_selected_unl` (step 4) | the invariant of §8 |
| `test_flagged_incumbent_keeps_its_seat` (step 4) | a flag never removes |
| `test_flag_only_withholds_a_new_seat` (step 4) | a flag never grants |
| `test_binding_mode_without_promotion_record_falls_back_to_shadow` (step 5) | the shadow guard |
| `test_shadow_and_binding_failures_yield_no_flag_and_standard_profile` (step 5) | the normative failure policy is the same in both modes |
| `test_model_deletion_is_no_op_without_flag_pipeline` (step 5) | deletion satisfies the no-op branch of the promotion gate |
| `test_previously_flagged_candidate_is_re_evaluated_each_round` (step 5) | no admissible current output means no current flag |

## 11. Open points, with leans

1. **Prompt text.** Lean: a new prompt v1 that asks the two questions of §3 (is
   the identity not established; do institution and domain contradict) and uses
   the packet research's "not established" criterion. Never reuse the
   legitimacy prompt. Bytes and hash are fixed in the package.
2. **`D` before step 3.** Lean: the interim domain-only `D`, recorded as
   `interim_domain_only` in the artifact. Switching to step 3's
   `meets_strict_profile` records `entry_profile_v1` and is a recorded rule
   change.
3. **Absent domain evidence (null).** Lean: count it as not verified. `D` then
   leans strict, but a flag still needs an affirmative admissible `M = flag`.
   Absent evidence alone never produces a flag.
4. **Reason codes.** Lean: two codes, `identity_not_established` and
   `institution_domain_contradiction`. `clear` carries none.
5. **Cited fields.** Lean: the closed list of the packet's fixed section names,
   as slugs: `validator_coordinates`, `claimed_domain_and_official_urls`,
   `public_identity`, `business_summary`, `public_x_handle`,
   `region_of_incorporation_and_operations`, `activities`,
   `estimated_public_profile_size`, `evidence` and `uncertainty_and_conflicts`.
6. **Padding divergence.** Lean: it invalidates its whole batch (§5).
7. **Owner.** Lean: a distinct provider host owner, as on 2026-09-03.
   Independent organizations stay a promotion gate.
8. **Cadence and cost.** Lean: every weekly round, about $5 per round
   (2026-09-03: $4.83). The inference-cost owner must be named in the decision
   sheet before the first GPU run.
9. **Packet freshness.** Lean: a packet is valid for a round only if its SHA-256
   is in a packet set frozen at or before the round's input freeze. The
   identity-packet runbook builds a packet from public evidence for every
   candidate. A candidate without a packet is a counted and reported pipeline
   coverage gap. It gets no flag and the standard profile, because the model
   may never block by being absent.
10. **Where the artifacts live.** Lean: an l1v2 shadow artifact under the
    package until 1b ships the manifest section. The fork publishes nothing about
    flags before then.

## Appendix A. Decisions of 2026-10-23

Added on 2026-10-23, after the lock. AGENTS.md does not allow a specification
that has passed the gate to be rewritten, so the decisions are recorded here
and the text above is unchanged. The bytes above this appendix are the locked
file of `6ba024e4` (SHA-256
`24102687f2df5a53e77c52d169e1cd10c06523354cee36e12b1f2e9a9b4662fc`). The scored
content hash in the status line does not cover this appendix.

The operator adopted all ten leans of §11 as decisions on 2026-10-23:

1. **Prompt.** A new prompt v1 asks the direction document's two questions.
   The legitimacy prompt is never reused. Pinned file:
   `benchmarks/ai-governance/identity-flag-20261023/prompt_v1.txt`, version
   `postfiat.identity_flag.prompt.v1`, SHA-256
   `e5a62a6db15443cea8dbb8b1c048309f10d4e7e87c4050b946cfb9941d443f19`.
2. **`D` before step 3.** The interim domain-only `D`, recorded as
   `interim_domain_only`. Switching to `entry_profile_v1` is a recorded rule change.
3. **Absent domain evidence.** It counts as not verified. A flag still needs an
   admissible model `flag`.
4. **Reason codes.** `identity_not_established` and
   `institution_domain_contradiction`.
5. **Cited fields.** The packet's ten fixed section names, as the slugs listed in §11.
6. **Padding divergence.** A divergent padding slot voids its batch.
7. **Owner.** A distinct provider host owner. Independent organizations stay a
   promotion gate.
8. **Cadence and cost.** Every weekly round. The inference-cost owner is named in
   the decision sheet before any GPU run.
9. **Packet freshness.** A packet counts for a round only if it is in the packet
   set frozen at or before the round's input freeze.
10. **Artifacts.** They live in this repository as shadow artifacts until 1b.

The model-deletion rule of §8 is confirmed as written: no flag, the standard
profile, and the failure reported.

The package also fixes two pins. The response schema
`postfiat.identity_flag.model_response.v1` has a canonical-JSON SHA-256 of
`2e383bc3057b1ce7f9a66f351286640470645893c57be8e2a8addc6825b8a609`. The step-3
entry-profile module is now pinned at SHA-256
`dd98970b92d284cace99efbc4992e1025600d04a74a045d45966576fed44c83f` (`1b317fc4`),
in place of the `null` of §6 and §7. The rule stays `interim_domain_only`.
