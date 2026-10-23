# Identity flag pipeline: package skeleton (Z2 step 2)

`SHADOW_ONLY`. This package implements the locked
[identity flag pipeline specification](../../../docs/specs/identity-flag-pipeline-spec-20261023.md),
with the decisions of its Appendix A (2026-10-23). It is step 2 of the
[Z2 plan](../../../docs/plans/active/z2-advisory-flag-execution-plan-20261022.md).
It calls no model. No GPU run has used it yet.

| File | What it is |
| --- | --- |
| `prompt_v1.txt` | Prompt `postfiat.identity_flag.prompt.v1`: the direction document's two questions and the typed output. SHA-256 `e5a62a6db15443cea8dbb8b1c048309f10d4e7e87c4050b946cfb9941d443f19` |
| `response_schema_v1.json` | `postfiat.identity_flag.model_response.v1`: five required fields, no others. Canonical-JSON SHA-256 `2e383bc3057b1ce7f9a66f351286640470645893c57be8e2a8addc6825b8a609` |
| `identity_flag_pipeline.py` | The typed flag, the execution profile and manifest section, the request builder, the slot checks, the four-run comparison, the failure table, `flags.json` and `admissibility.json`, and the `SHADOW_ONLY` guard |
| `admissibility.py` | CLI. It writes a round's request rows for the host runner, or the round's `flags.json` and `admissibility.json` from four run files |
| `build_fixtures.py` | Rebuilds `fixtures/` from committed data (`--check` reports drift) |
| `fixtures/worked_example_20260903.json` | The spec's §4.1 corpus: 55 validators with their legitimacy score, "not established" and domain-verified facts |
| `fixtures/round_28_candidates.json` | Testnet round 28's 61 candidates: incumbent, `domain_verified`, and the 2026-09-01 packet where one exists (20) |
| `test_identity_flag_pipeline.py` | Offline tests with stubbed model outputs |

## Rules as implemented

- **Flag.** `identity_flag` is `flag` only when the model's classification is
  admissible and says `flag`, **and** the strict profile is not met. The strict
  check is `meets_strict_profile` of the step-3 mirror
  (`python/postfiat_rpc/validator_entry_profile.py`) under `interim_domain_only`.
  Absent domain evidence counts as not verified.
- **Admissible.** The slot must be byte-identical across four runs: two owners,
  two runs each. It must have finished with `stop`. It must match the schema
  exactly and echo the request's `validator_id` and `packet_sha256`.
  `cited_fields` must be sorted and non-empty. `reason_codes` must be empty for
  `clear` and non-empty for `flag`.
- **Failures give no flag.** These cases cover that operator only: a missing
  packet, a missing slot, a divergent slot, a truncated or invalid response, a
  wrong echo, a run that replayed other request bytes, and a packet outside the
  frozen packet set. These cases give zero flags for the round: an outage (not
  exactly two owners × two runs), a manifest section that differs from the
  package's, and a changed sub-scorer or entry-profile file.
- **Padding slots.** The spec requires that a divergent padding slot voids its
  batch. The skeleton applies the same rule to a padding slot that is
  inadmissible for any reason. A voided operator takes the padding slot's class,
  and `voided_by_padding_slot` records which slot voided it.
- **Guard.** `build_flags(mode != "shadow")` and `binding_flag_input()` raise
  `ShadowOnlyViolation`. So does writing any artifact without
  `"shadow_only": true`.

## Pins

| Pin | SHA-256 |
| --- | --- |
| Execution profile (canonical JSON of `execution_profile()`) | `2b16e2472fea4e3cefad3484cb9791ad5558785eb912e6ed48843e5aed774b56` |
| v3 sub-scorer `dunl-subscorer-shadow-20260901/subscorer_v3.py` | `f71f29ddf00c3825447fc19034340d4ef714b9668345c51e6872586a844c5dc5` |
| Entry profile `crates/consensus_cobalt/src/validator_entry_profile.rs` | `dd98970b92d284cace99efbc4992e1025600d04a74a045d45966576fed44c83f` |
| Entry profile mirror `python/postfiat_rpc/validator_entry_profile.py` | `18191847385dc2f52b9479e9a6e822b43e4866b6570704e8239b47f594bcff00` |

`manifest_section()` is the round-manifest flag section that 1b will publish.
It adds the SHA-256 of `identity_flag_pipeline.py` itself, so any edit to the
module makes earlier pins stale.

## Run

```bash
python3 -m pytest benchmarks/ai-governance/identity-flag-20261023 -q
python3 benchmarks/ai-governance/identity-flag-20261023/build_fixtures.py --check
```

## Results on the fixtures (stubbed model outputs)

- **2026-09-03 corpus.** With the score-0 stand-in, the rule gives 13 flags,
  all XRPL. With the "not established" stand-in, it gives 0. "Legitimacy 0"
  alone would give 33.
- **Round 28.** There are 61 candidates. 20 have a packet and 41 do not, and
  those 41 are reported as coverage gaps. All 20 with a packet have verified
  domains, so a model that flags everyone still gives 0 flags. The 12 candidates
  without a verified domain are all among the 41 without a packet.

## Before the first GPU run

- **Host runner.** The 2026-09-03 `run_host.py` checks its own legitimacy prompt
  and response schema, so the flag requests need a variant of it. Its output
  shape (`slot`, `request_sha256`, `content`, `finish_reason`) is what
  `admissibility.py --run` reads.
- **Packets.** A packet set is needed that covers the round's candidates and is
  frozen by the input freeze.
- **Cost owner.** The inference-cost owner must be named in the decision sheet.
