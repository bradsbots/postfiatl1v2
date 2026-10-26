# Identity flag pipeline: package skeleton (Z2 step 2)

`SHADOW_ONLY`. This package implements the locked
[identity flag pipeline specification](../../../docs/specs/identity-flag-pipeline-spec-20261023.md),
with the decisions of its Appendix A (2026-10-23). It is step 2 of the
[Z2 plan](../../../docs/plans/active/z2-advisory-flag-execution-plan-20261022.md).
Only `run_host.py` calls a model, on a GPU host. No GPU run has used it yet.

| File | What it is |
| --- | --- |
| `prompt_v1.txt` | Prompt `postfiat.identity_flag.prompt.v1`: the direction document's two questions and the typed output. SHA-256 `e5a62a6db15443cea8dbb8b1c048309f10d4e7e87c4050b946cfb9941d443f19` |
| `response_schema_v1.json` | `postfiat.identity_flag.model_response.v1`: five required fields, no others. Canonical-JSON SHA-256 `2e383bc3057b1ce7f9a66f351286640470645893c57be8e2a8addc6825b8a609` |
| `identity_flag_pipeline.py` | The typed flag, the execution profile and manifest section, the request builder, the slot checks, the four-run comparison, the failure table, `flags.json` and `admissibility.json`, and the `SHADOW_ONLY` guard |
| `admissibility.py` | CLI. It writes a round's request rows for the host runner, or the round's `flags.json` and `admissibility.json` from four run files |
| `run_host.py` | The host runner: the flag variant of the 2026-09-03 `run_host.py`, with the same execution profile. It posts a round's request rows to the loopback SGLang server and writes one run file `<owner>-run<index>.json` |
| `build_fixtures.py` | Rebuilds `fixtures/` from committed data (`--check` reports drift) |
| `fixtures/worked_example_20260903.json` | The spec's §4.1 corpus: 55 validators with their legitimacy score, "not established" and domain-verified facts |
| `fixtures/round_28_candidates.json` | Testnet round 28's 61 candidates: incumbent, `domain_verified`, and the 2026-09-01 packet where one exists (20) |
| `test_identity_flag_pipeline.py` | Offline tests with stubbed model outputs |
| `test_run_host.py` | Offline tests of the runner with a stubbed backend |

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
  exactly two owners × two runs, or a run file that fails the checks under
  [Run](#run)), a manifest section that differs from the package's, and a
  changed sub-scorer or entry-profile file.
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

`run_host.py` has no pin of its own, because neither §6 nor `manifest_section()`
pins a runner; the request echo and the four-run byte comparison check its output.

**Decision, 2026-10-26.** The runner's SHA-256 is not added to the pins.

## Run

```bash
python3 -m pytest benchmarks/ai-governance/identity-flag-20261023 -q
python3 benchmarks/ai-governance/identity-flag-20261023/build_fixtures.py --check
```

A round, from this directory. On each GPU host, start the server with the
2026-09-03 `bootstrap_host.sh`, then run the round's requests twice:

```bash
python3 admissibility.py --round round.json --requests-out requests.json
python3 run_host.py --requests requests.json --owner ownerA --provider-host-id <id> --run-index 1
python3 run_host.py --requests requests.json --owner ownerA --provider-host-id <id> --run-index 2
# the same on the second owner's host, then, with the four files in outputs/:
python3 admissibility.py --round round.json --section section.json --out out/ \
    --run ownerA=outputs/ownerA-run1.json --run ownerA=outputs/ownerA-run2.json \
    --run ownerB=outputs/ownerB-run1.json --run ownerB=outputs/ownerB-run2.json
```

Each `results` row has `slot`, `request_sha256`, `content` and `finish_reason`,
plus `content_sha256` and `slot_check`. A truncated or invalid reply is written as
received. The `host` record holds the owner, provider host ID, run index, GPU,
Python and server settings.

`admissibility.py` checks the run files against spec §5. Each file's `host.owner`
must be the `--run OWNER=` label. Its run index must be 1 or 2, and differ from
the owner's other file. One owner's two runs must come from the same provider
host, the two owners' host IDs must differ, and a file without a `host` record fails. Any problem voids every run: the round is an outage
with zero flags, and the CLI prints the problems as `run_file_problems`.

**Decision, 2026-10-26.** These checks live in `admissibility.py`, so
`identity_flag_pipeline.py` and its SHA-256 are unchanged.

The runner refuses to start, before it sends any request, when:

- `prompt_v1.txt` or `response_schema_v1.json` does not have its pinned SHA-256;
- the request rows are not whole batches of 32, a row's body does not hash to its
  `request_sha256`, or the rows are not exactly what `build_requests` gives for
  their embedded packets (another prompt, schema or sampling setting);
- the owner label is not a plain name, the run index is not 1 or 2, or the run file
  already exists.

## Results on the fixtures (stubbed model outputs)

- **2026-09-03 corpus.** With the score-0 stand-in, the rule gives 13 flags,
  all XRPL. With the "not established" stand-in, it gives 0. "Legitimacy 0"
  alone would give 33.
- **Round 28.** There are 61 candidates. 20 have a packet and 41 do not, and
  those 41 are reported as coverage gaps. All 20 with a packet have verified
  domains, so a model that flags everyone still gives 0 flags. The 12 candidates
  without a verified domain are all among the 41 without a packet.

## Before the first GPU run

- [x] **Host runner.** `run_host.py` is the flag variant of the 2026-09-03
  runner. Its run files are what `admissibility.py --run` reads.
- [ ] **Packets.** A packet set is needed that covers the round's candidates and is
  frozen by the input freeze.
- [x] **Cost owner.** Named in the decision sheet on 2026-10-23.
