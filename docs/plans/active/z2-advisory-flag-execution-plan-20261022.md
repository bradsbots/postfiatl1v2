# Z2 Advisory Flag Execution Plan

**Status:** Execution plan, 2026-10-22. Refreshed on 2026-10-23: see [Status on 2026-10-23](#status-on-2026-10-23). Step 1a is complete, the step-2 package and the step-3 rule module have landed, and the earliest production switch is the round of 2026-11-24.
**Date:** 2026-10-22
**Parent gate:** [L1v2 Public Testnet Path, Gate Zero Z2](l1v2-public-testnet-path-milestone.md#gate-zero-operator-preconditions-recorded-2026-08-30)
**Decision:** [AI governance direction of 2026-09-03](../../governance/ai-governance-direction-20260903.md), confirmed 2026-10-20 (row 1 of the [pending operator decisions](../../governance/pending-operator-decisions.md))
**Code read at:** this repository `main` `f50aeff1`; `dynamic-unl-scoring` `origin/main` `e70515d` (2026-10-17); `validator-scoring-sidecar` `origin/main` `c0389f8` (2026-10-15). Fork and sidecar line numbers below are at those commits.

## Status on 2026-10-23

**Done:**

- [x] **Step 1a is complete.** The v3 sub-scorer is frozen at `f71f29dd…` (`5b9f99a8`). Round 28, the newest v12-era round, was replayed (`4e70747c`): the internal control reproduces the published UNL, with 0 flips and 24/25 overlap. Rounds from 2026-10-27 count.
- [x] **Step 2's specification is locked** at 86.33/100 (`6ba024e4`). Prompt v1 is pinned at `e5a62a6d…`, and the pipeline skeleton has 27 offline tests (`072a9e87`). Step 2's acceptance check passes.
- [x] **Step 3's rule module** `entry_profile_v1` (`dd98970b…`) has landed with its Python mirror (`18191847…`) and 263 shared fixtures (`1b317fc4`). Consensus does not use it.
- [x] **Decisions of 2026-10-23:**
    - the ten spec leans are adopted ([spec Appendix A](../../specs/identity-flag-pipeline-spec-20261023.md#appendix-a-decisions-of-2026-10-23), `072a9e87`);
    - step 3 keeps its parameters and clean-round definition as implemented (step 3 record);
    - the inference-cost owner for the weekly flag runs is named ([decision sheet](../../governance/pending-operator-decisions.md), step 2 record).

**Remaining:**

| Item | Needs | Estimate |
| --- | --- | --- |
| 1b: fork module, manifest section, prompt v13, sidecar release | Code-owner review in the fork and sidecar repositories | 1.5–3 days |
| Flag variant of `run_host.py` | — | 0.5 day |
| Frozen packet set covering the round's candidates (41 of round 28's 61 have none) | The identity-packet runbook, then the §8 human publication review | 1–2 days, plus the review |
| First two-owner GPU run | The two rows above, and the payment path for the rented hosts (step 2 record) | 0.5 day, about $5 |
| Step 3: frozen history input (previous rounds' `final_scores.json` by hash) | Round artifacts | 0.5–1 day |
| Step 4: wire the flag through the entry profile | Steps 2 and 3 | 2–3 days |
| Step 5: `SHADOW_ONLY` guard and change-control register | Step 3 | 1–2 days |
| Step 6: four counted rounds, then the switch | Tuesdays 2026-10-27, 11-03, 11-10 and 11-17, then 1b deployed | Half a day per round, then 1.5–3 days for the switch |

**Earliest production switch: the round of 2026-11-24.** That date needs four things:

- all four counted rounds are clean;
- the Tuesday slot does not move;
- no module change restarts the count;
- the 1b set is deployed before that round: a devnet manual round and a sidecar that vendors the module.

## BLUF

1. **The long pole is step 6.** It needs four weekly shadow rounds, and the clock starts only when the sub-scorer module bytes are frozen (step 1a). Testnet rounds have run on Tuesdays (round 16 on 2026-07-28, round 26 on 2026-10-06). If the module is frozen by Monday 2026-10-26 and the slot does not move, the counted rounds are 10-27, 11-03, 11-10 and 11-17. The earliest production switch is then the round of 2026-11-24. The module was frozen on 2026-10-23, so these dates hold.
2. **Step 1 is partly done on the fork.** Since 2026-10-09 the fork computes diversity in code (diversity formula v1). The manifest pins it as `code.diversity_formula`, and sidecars vendor it. The v2 diversity band matrix is superseded. Under prompt v12 the model still supplies the other four sub-scores: consensus, reliability, software and identity.
3. **The v2 module is behind the fork.** It predates the minimum-safe-version software rule (2026-09-21), the 25-seat UNL (2026-09-24) and diversity formula v1. Its harness pins fork modules from a local clone that is 34 commits behind and ignores `code.diversity_formula`. The module that gets pinned is therefore v3: the v2 rules plus those two reconciliations. v2 stays as the record.
4. **Steps 2–5 are deterministic code and docs in this repository.** They run during the shadow weeks and do not block the switch. No flag binds anything: the flag and its strict-profile effect stay `SHADOW_ONLY` until the promotion gates below pass.
5. **No step is impossible, but one conflict must be fixed.** The existing l1v2 admission policy holds a candidate when the model output is missing (`crates/consensus_cobalt/src/validator_admission_policy.rs:334-341`, `:499-503`). That is the opposite of the decided rule. No live code calls it.
6. **Estimate:** 14–23 working days, plus the four-week shadow window, which overlaps steps 2–5. All six steps can be done by the end of November 2026 at the earliest.

## Steps

- [ ] **1. Pin the v3 sub-scorer in the round manifest** (content hash and manifest section)
    - *Today:* `benchmarks/ai-governance/dunl-subscorer-shadow-20260901/subscorer_v2.py:132` sets `SUBSCORER_VERSION = 2`. The rules are at `:176` (consensus), `:184-202` (reliability; chronic floor 40 at `:195`), `:213-223` (software), `:146-152` and `:261` (diversity bands) and `:271-276` (identity). The 2026-09-01 shadow evaluation lists the pin as open ([results](../../governance/dunl-subscorer-shadow-eval-20260901.md#v2-results)). The fork's `_build_code_manifest` (`scoring_service/services/ipfs_publisher.py:380-452`) pins the parser, `diversity_formula` (`:417-425`), `score_formula` (`:426-436`) and selector (`:437-447`) by `content_sha256` (`:259-265`). Selection runs `select_unl(apply_formula(apply_diversity_formula(...)))` (`orchestrator.py:763-768`). The diversity module is `diversity_formula.py:22`, commit `ffe7582`. Prompt v12 tells the model to score software 0 when `fails_minimum_safe_version` is set (`prompts/scoring_v12.txt:73`; collector `collector.py:62-72`, commit `d85a3e9`). v2 does not read that flag. On the sidecar side, `manifest.py:527-544` rejects unknown diversity hashes, and `scripts/check_vendor_freshness.py:49-50` vendors the two formulas.
    - *Missing:*
        - a fork module for the four model-owned dimensions, reconciled to the current era (minimum safe version gives software 0; v12 inputs; 25 seats), with diversity taken unchanged from `diversity_formula`;
        - a manifest section beside `code.diversity_formula` (name fixed in the PR) with module, `content_sha256`, version and parameters;
        - per-dimension model and computed values in `outputs/final_scores.json`;
        - sidecar vendoring, a prompt v13 that makes the four sub-scores advisory, and the explorer and governance-row updates;
        - decision lines for the reliability chronic floor (40) and the diversity curve (diversity formula v1, live since 2026-10-09).
    - *Deliverable:*
        - **1a, before the shadow clock:** `subscorer_v3.py` beside v2, with tests and golden vectors. Refresh `shadow_eval.py` so it reads `code.diversity_formula` and `outputs/final_scores.json`; today it pins only parser, selector and formula (`:142-146`, `:182`). Run it against a fork checkout at each round's pinned hashes. Write the module's SHA-256 into this plan.
        - **1b, before the switch:** fork module `scoring_service/services/subscore_rules.py` (or the name fixed in the PR) with `tests/test_subscore_rules.py`; the manifest section and `final_scores.json` fields; prompt v13 and its doc; a sidecar release that vendors the module and its supported-hash set; the explorer label; the `scoring-model-governance` row.
    - *Acceptance:*
        - **1a:** the harness internal control reproduces the published UNL on every v12-era round it replays. v3 shows no ineligible→eligible flip on rounds 12–19 or on the replayed v12 rounds.
        - **1b:** a devnet manual round publishes the new section with the frozen hash. A sidecar that vendors the module matches at RAW, PARSED and SELECTED_UNL.
    - *Estimate:* 3–5 days (1a 1.5–2, 1b 1.5–3).
    - *Depends on:* code-owner review in the fork and sidecar repositories. Nothing from the other lane.
    - *1a record (2026-10-23, fork clone pulled from `f18e6b4` to `e70515d`):*
        - [x] `subscorer_v3.py` is v2 plus the fork's current rules. Software is 0 when `fails_minimum_safe_version` is true (`subscorer_v3.py:138-140`, fork `d85a3e9`). Diversity is no longer scored (`DIMENSIONS`, `:70`); the comparison takes it from the round's `code.diversity_formula` (fork `ffe7582`). The 25 seats (fork `5f65bdf`) change no sub-score rule; they reach the comparison only through the manifest's `max_size`. Consensus, reliability and identity are v2's. Fail-first tests are in `test_subscorer.py:305-391`, and golden vectors are in `fixtures/subscorer_v3_golden.json`.
        - [x] **Frozen hash.** SHA-256 over the module bytes, the fork's `content_sha256` definition (`ipfs_publisher.py:259-265`): `f71f29ddf00c3825447fc19034340d4ef714b9668345c51e6872586a844c5dc5`. The hash covers one file: `benchmarks/ai-governance/dunl-subscorer-shadow-20260901/subscorer_v3.py`. Reproduce with `sha256sum benchmarks/ai-governance/dunl-subscorer-shadow-20260901/subscorer_v3.py`. The golden file carries the same hash, and `test_module_bytes_match_the_frozen_content_hash` fails on any byte change.
        - [x] `shadow_eval.py --scorer-version 3` verifies `code.diversity_formula` (hash, version, parameters) and computes diversity from `inputs/diversity_inputs.json`. It cross-checks `outputs/final_scores.json`, rejects a published UNL larger than the pinned `max_size` and refuses a fork clone that is not at `origin/main`. It also reports the automated part of the step 6 acceptance check. Tests: `test_shadow_eval.py:160-358`. The v1 and v2 outputs regenerate byte-identically.
        - [x] Rounds 12–19 (`results-v3.json`): the internal control reproduces the published UNL 8/8. There are 0 ineligible→eligible flips and 1 eligible→ineligible flip, the same round-12 validator as v2 (baseline 45, v3 29). Overlap is at least 19/20 in every round.
        - [x] `fetch_rounds.py` also fetches `inputs/diversity_inputs.json` (input route) and `outputs/final_scores.json` (`ERA_FILES`, `fetch_rounds.py:43-46`, `:106-124`) and pins them in `rounds-manifest.json` like every other file. Both are required when the round pins `code.diversity_formula`. Fail-first tests: `test_fetch_rounds.py:147-211`.
        - [x] **v12-era round, 2026-10-23:** round 28, the newest published (input frozen 2026-10-20, prompt v12, 25 seats, minimum safe version 1.0.9). It was fetched from the public testnet scoring service; all 9 files are pinned, with diversity inputs `77d35aff…` and final scores `2e819d57…`. The internal control reproduces the published UNL, and `outputs/final_scores.json` matches the pinned formula chain for all 61 validators. There are 0 flips in either direction and overlap is 24/25. The one swap comes from reliability: v3 gives 65 to a validator whose recent windows are just below clean, and the model gave 95, so its final drops from 95 to 89. Software matches the model for all 61, including the 23 that fail the minimum safe version. Rounds 12–19 are unchanged from the first replay.
    - *Left to do:*
        - Each counted round (Tuesdays from 2026-10-27): run `fetch_rounds.py --rounds N` once it publishes, then `shadow_eval.py --scorer-version 3`. This is step 6's half day per round.
        - 1b as above (1.5–3 days). The fork module must reproduce `fixtures/subscorer_v3_golden.json`. Manifests pin the fork file's hash, so record it here beside the v3 hash. The 1b PR must say whether a byte-different but vector-identical port restarts the count.
- [ ] **2. Specify the flag pipeline** (typed `identity_flag` `clear`/`flag`, pinned execution profile, two-owner byte-convergent replay)
    - *Today:*
        - The flag is defined in direction §2 (lines 57–94) and work-sequence step 1 (lines 269–274).
        - The reusable package is `benchmarks/ai-governance/identity-packet-replay-20260903/`. Its strict response schema is `build_package.py:81-114`. Its pinned profile is `:297-320`: `Qwen/Qwen3.8-27B-FP8` revision `017b9c7a…`, an SGLang image digest, deterministic inference, temperature 0, loopback only, two distinct-owner hosts × two runs. The loopback endpoint is `run_host.py:25`, response checks are `:114-135`, and the byte comparison is `compare_runs.py:40-69`. Result: PASS, 192/192, on 2026-09-03 for $4.83.
        - The packet corpus `validator-identity-packets-20260901` passes 55/55 strict checks. Its human publication review (runbook §8) has not been done.
        - No `identity_flag` exists in this repository, the fork or the sidecar (searched 2026-10-22).
        - The flag cannot simply be "legitimacy score 0". On 2026-09-03 that rule would have flagged 33/55 validators, including all 20 PostFiat validators and 23 identities the packets call established or likely (package `README.md`).
    - *Missing:* the typed schema, a flag prompt, batch and padding rules, the admissibility rule, outage semantics, artifact names and hashes.
    - *Deliverable:*
        - `docs/governance/identity-flag-pipeline.md` (new) defines schema `postfiat.identity_flag.v1`: `validator_id`, echoed `packet_sha256`, `identity_flag` ∈ {`clear`, `flag`}, sorted non-empty `cited_fields` taken from the packet, and reason codes from a closed list. It also fixes the prompt bytes and hash and reuses the 2026-09-03 profile unchanged.
        - A flag is admissible only if it is byte-identical across both owners and all runs. A parse failure, truncation, wrong echo, missing slot or divergence means no flag for that operator. A whole-run outage means zero flags.
        - A package skeleton under `benchmarks/ai-governance/identity-flag-<date>/` reuses the builder, host runner and comparator and adds `admissibility.py` (writes `flags.json` and `admissibility.json`). Offline tests use recorded fake responses. There is no GPU run in this step.
    - *Acceptance:* the builder emits identical request bytes on two runs. Tests show that each failure class yields no flag for that operator and changes nothing else. The note passes the doc gates.
    - *Estimate:* 2–3 days.
    - *Depends on:* nothing, to write it. A live GPU run (not part of this step) needs the inference-cost row in the decision sheet answered, which is open today, and a frozen packet set covering the round's candidates.
    - *Step 2 record (2026-10-23, Task Node `task_46fd38ab1cc6f8aea2707ef707c6039b`):*
        - [x] Specification written and locked: [identity flag pipeline specification](../../specs/identity-flag-pipeline-spec-20261023.md). It is in `docs/specs/` rather than the `docs/governance/identity-flag-pipeline.md` named above. The Text Improvement Harness full gate gave 86.33/100 (GPT 85.40, Fable 85.60, GLM 88.00), after a first gate of 85.67 and one improvement pass. It covers the schemas (`postfiat.identity_flag.model_response.v1`, `postfiat.identity_flag.v1`), the reason codes and the cited-field list (§11, leans).
        - [x] Flag rule (§4). A flag needs an admissible model `flag` **and** the deterministic strict-profile result "not met". Until step 3 lands, that result uses the frozen v3 identity rule (`f71f29dd…`): a verified domain or not. On the 2026-09-03 corpus the rule gives 13 flags with the score-0 stand-in and 0 with the "not established" stand-in. "Legitimacy 0" alone gives 33. No PostFiat validator is flagged under the rule (§4.1).
        - [x] Admissibility (§5, §9). Two distinct-owner hosts × two runs, byte-identical content per slot. A divergent, missing, truncated, invalid or wrong-echo slot means no flag for that operator. A padding divergence means no flag for its batch. An outage or a stale pin means zero flags. The same applies in shadow and binding mode, and model deletion is the no-op branch.
        - [x] Pinned execution profile (§6). It is the 2026-09-03 profile unchanged, plus the prompt, schema, input, sub-scorer and entry-profile hashes, recorded in the round manifest's flag section.
        - [x] Data contract with step 3 (§7: `flags.json`, `admissibility.json`, `strict_profile_rule`, `none`/`clear`/`flag`). `SHADOW_ONLY` invariant (§8). Acceptance test names (§10).
    - *Step 2 record, package (2026-10-23, Task Node `task_c017701be2a10d059b39598cbae6ed4d`):*
        - [x] Prompt `postfiat.identity_flag.prompt.v1` (open point 1): [`prompt_v1.txt`](https://github.com/postfiatorg/postfiatl1v2/blob/main/benchmarks/ai-governance/identity-flag-20261023/prompt_v1.txt). It asks the direction document's two questions and gives the five-field typed output, with no legitimacy or score text. SHA-256 `e5a62a6db15443cea8dbb8b1c048309f10d4e7e87c4050b946cfb9941d443f19`. The response schema [`response_schema_v1.json`](https://github.com/postfiatorg/postfiatl1v2/blob/main/benchmarks/ai-governance/identity-flag-20261023/response_schema_v1.json) has canonical-JSON SHA-256 `2e383bc3057b1ce7f9a66f351286640470645893c57be8e2a8addc6825b8a609`.
        - [x] Package skeleton [`benchmarks/ai-governance/identity-flag-20261023/`](https://github.com/postfiatorg/postfiatl1v2/blob/main/benchmarks/ai-governance/identity-flag-20261023/README.md):
            - `identity_flag_pipeline.py` holds the typed flag, the execution profile (SHA-256 `2b16e247…`) and its manifest section, the builder (the 2026-09-03 layout: exact packet bytes between markers, batches of 32, fixed padding), the slot checks, the four-run comparison, the failure table and the `SHADOW_ONLY` guard. Any binding use raises `ShadowOnlyViolation`.
            - `admissibility.py` writes `flags.json` and `admissibility.json`, or the request rows for the host runner.
            - `build_fixtures.py` builds the fixtures: the 2026-09-03 worked example (55 validators) and round 28 (61 candidates).
            - The strict check is the step-3 mirror under `interim_domain_only`. Pinned with it: v3 `f71f29dd…`, entry profile `dd98970b…` (`1b317fc4`).
        - [x] Offline tests, with stubbed model outputs and no model call: `python3 -m pytest benchmarks/ai-governance/identity-flag-20261023 -q`. All 27 pass. Before the implementation, against a stub module, the first 26 gave 9 failed, 15 errors and 2 passed (the two data checks). The prompt-hash and locked-spec tests failed until the spec appendix and this record existed. The tests cover:
            - the 19 package tests of §10;
            - the prompt, schema, profile, fixture and locked-spec pins;
            - the `SHADOW_ONLY` guard;
            - the CLI.
            - **Acceptance check met.** The builder emits identical request bytes on two runs, including from shuffled input. Each failure class (divergent, missing, truncated, invalid, wrong echo, stale) gives no flag for its operator and leaves every other operator's row byte-identical. An outage, a changed manifest pin or a changed sub-scorer file gives zero flags.
            - **Results.** The worked example gives 13 flags with the score-0 stand-in (all XRPL) and 0 with "not established". Round 28 gives 0 flags even with a model that flags everyone: all 20 candidates with a packet have verified domains. The 41 without a packet are reported as coverage gaps.
        - [x] Decision lines for the ten open points: all leans adopted on 2026-10-23, and the model-deletion rule confirmed. They are recorded as the spec's dated [Appendix A](../../specs/identity-flag-pipeline-spec-20261023.md#appendix-a-decisions-of-2026-10-23). AGENTS.md does not allow a locked spec to be rewritten, so the text above the appendix is byte-identical to `6ba024e4`, and a test checks this.
    - *Left to do (step 2), all before the first GPU run; none blocks step 3 or 4:*
        - [ ] A flag variant of the host runner `run_host.py`. Today it checks the legitimacy prompt and schema. Its output shape is what `admissibility.py --run` reads. Estimate: 0.5 day.
        - [ ] A packet set frozen by the round's input freeze that covers the round's candidates. 41 of round 28's 61 have no packet. Building them with the identity-packet runbook takes 1–2 days, and the corpus also needs its human publication review (runbook §8).
        - [x] **Inference-cost owner (decided 2026-10-23):**
            - The founder's OpenRouter account pays, the account whose key the server already holds. That is about $5 per weekly round.
            - It is recorded in the [decision sheet](../../governance/pending-operator-decisions.md). He is informed in the 2026-10-23 handoff and may object.
            - The pinned profile runs on two rented GPU hosts and calls no OpenRouter API (spec §6; the 2026-09-03 runs used Vast.ai). How the rental is paid from that account is settled before the first run.
        - [ ] The first two-owner GPU run (about $5) and its record. Estimate: 0.5 day, once the three items above are done.
- [ ] **3. Build the strict entry profile** as a versioned deterministic rule module with a Python mirror and fixtures
    - *Today:*
        - Only the proposed defaults exist (direction lines 72–82): a verified domain is mandatory, four consecutive clean rounds are required, and there is no seat (fork) or trust-view membership (l1v2) until then. The five fixture cases are listed at lines 275–281.
        - Neighbouring module: `validator_admission_policy.rs` (schemas `:1-3`, policy `:33-46`, `controlled_testnet_v1` `:49-64`, `evaluate_validator_admission` `:175`, included at `lib.rs:4`, tests `tests.rs:4790-4917`).
        - Rust/Python mirror pattern: `crates/types/src/genesis_registry.rs` ↔ `python/postfiat_rpc/genesis_registry.py:1-9`, with golden vectors in `benchmarks/genesis-registry/fixtures/`.
    - *Missing:*
        - the module itself;
        - the definition of a "clean round";
        - a frozen history input (the fork input package freezes only the previous UNL, so the module takes the four previous rounds' `final_scores.json` by hash);
        - parameter values and a content hash.
    - *Deliverable:*
        - `crates/consensus_cobalt/src/validator_entry_profile.rs` (new) under schema `postfiat.validator_entry_profile.v1`. It is a pure integer function of (parameters, frozen N-round history with hashes, domain verified, incumbent, flag ∈ {none, `clear`, `flag`}) that returns the profile (standard or strict), whether the operator may take a new seat, and the reasons.
        - `python/postfiat_rpc/validator_entry_profile.py` (new) mirrors it and shares no code with the Rust module.
        - Shared golden fixtures cover the five direction cases plus boundaries: three clean rounds, a gap, domain lost in round four, and a flag that clears.
        - A decision line for the parameters goes in the step 5 register.
    - *Acceptance:* Rust and Python give identical canonical bytes and content hashes on every fixture. The five direction cases pass. Tests stay focused: `cargo test -p postfiat-consensus-cobalt validator_entry_profile` and `pytest python/tests/test_validator_entry_profile.py`.
    - *Estimate:* 3–5 days.
    - *Depends on:* the recorded parameter decision. The defaults are pre-filled, so "confirmed" is enough. Code can start on the defaults; fixture hashes change if the decision does.
    - *Step 3 record (2026-10-23, Task Node `task_3329e1bced76ef3b625ba2326d9a0265`):*
        - [x] Rule module `crates/consensus_cobalt/src/validator_entry_profile.rs`, `postfiat.validator_entry_profile.v1`, version 1, SHA-256 `dd98970b92d284cace99efbc4992e1025600d04a74a045d45966576fed44c83f`. It is a `pub mod` of the cobalt crate, registered in `lib.rs` beside `validator_admission_policy.rs`. Consensus never calls it, and the admission policy is unchanged, including its `require_model_classification` hold (`:334-341`, `:499-503`), which step 4 replaces.
        - [x] Rules, as the [identity flag pipeline specification](../../specs/identity-flag-pipeline-spec-20261023.md) states them (§3, §4, §7):
            - `meets_strict_profile` never reads a flag. Under `entry_profile_v1` it needs a verified domain and four consecutive clean rounds ending at the previous round. Under `interim_domain_only` it needs a verified domain.
            - `identity_flag` is `flag` only when the model says `flag` and the strict profile is not met.
            - `resolve_flag_input` gives `none` for a missing artifact, a wrong schema, a non-shadow artifact, a pin mismatch, an absent or duplicated operator, or an unknown value.
            - `none` and `clear` select the standard profile, and `flag` the strict one. A flag only withholds a new seat; an incumbent keeps its seat.
            - Malformed history is refused with stable error codes.
        - [x] Python mirror `python/postfiat_rpc/validator_entry_profile.py`, SHA-256 `18191847385dc2f52b9479e9a6e822b43e4866b6570704e8239b47f594bcff00`. It shares no code with the Rust module.
        - [x] Shared fixtures `benchmarks/ai-governance/validator-entry-profile-20261023/fixtures/` (263 cases, `cases.json` SHA-256 `a7cbfc6f…`, pins in `modules.json`):
            - 31 hand-checked direction and boundary cases;
            - the spec's 2026-09-03 worked example (110 cases: 13 flags and 0);
            - round 28 (122 cases, 61 operators under both rules).
        - [x] Fail-first, then convergence:
            - Rust: with the three rule functions stubbed, 5 of 6 tests failed (156 of 263 cases mismatched). After: 6 of 6 pass, byte for byte on all 263.
            - Python: with the same stub, 6 of 7 failed. After: 7 of 7 pass, with the same bytes and their SHA-256.
            - Gates: `cargo fmt --all -- --check` and clippy `-D warnings` on `postfiat-consensus-cobalt` are clean.
        - [x] **Decision line, 2026-10-23.** The parameters and the clean-round definition stay as implemented in `entry_profile_v1` (`1b317fc4`).
            - **Parameters:** a verified domain, and four consecutive clean rounds ending at the previous round.
            - **A clean round:** the operator is present in the round's final scores, its domain is verified, and its final score is at or above the cutoff.
            - **Pins:** the fixtures and the hashes stand (`dd98970b…`, `18191847…`).
            - **Register:** the line goes into the change-control register when step 5 creates it.
        - [ ] Pin the module hash in the change-control register (step 5) and in the round manifest's flag section (1b).
    - *Left to do (step 3):*
        - A frozen history input: the previous rounds' `final_scores.json` by hash, assembled from the round artifacts (0.5–1 day).
        - The shadow report command over a real round: step 4 (0.5 day).
        - The binding-mode guard: step 5.
- [ ] **4. Wire the advisory flag:** it only switches entry to the strict profile; divergent or missing output yields no flag
    - *Today:*
        - The rule is in direction lines 83–94 and the [validity review](../../governance/ai-governance-validity-review.md), decision 5.
        - The only existing consumer of model output does the opposite. `controlled_testnet_v1` sets `require_model_classification: true` (`validator_admission_policy.rs:58`). A missing output is a hold (`:334-341`, `:499-503`), and three of the four classifications hold (`:526-545`). It has no caller outside tests.
        - Nothing on the fork reads a flag.
    - *Missing:* the flag → profile input; a shadow report that names who would be held; the fix for the conflicting hold.
    - *Deliverable:*
        - A flag input in both modules: an admissible `flag` selects the strict profile. `clear`, missing, divergent, truncated or an unknown version selects the standard profile. The flag is never an input to scores, the formula, the selector or incumbents.
        - A shadow-report command in the Python mirror. It reads a fork round's frozen artifacts plus the flag artifacts and writes a "would hold" list marked `SHADOW_ONLY`.
        - Admission policy version 2 with `require_model_classification: false` and the flag routed through the entry profile, or a dated note retiring version 1.
    - *Acceptance:* tests show the following.
        - Final scores and the selected UNL are byte-identical with and without flags.
        - No flag file gives zero flags.
        - Divergent replay gives no flag.
        - A flagged incumbent keeps its seat.
        - A flag can only withhold a new seat, never grant one.
    - *Estimate:* 2–3 days.
    - *Depends on:* steps 2 and 3.
- [ ] **5. Keep flags and legitimacy scores `SHADOW_ONLY`** until the recorded promotion gates pass
    - *Today:*
        - The rule holds only because nothing reads a legitimacy score or a flag. The labels exist: the replay `manifest.json` has `"shadow_only": true` and `"consensus_input": false`; the [legitimacy scoring](../../governance/institution-legitimacy-scoring.md) runtime boundary (line 12) applies; and `tasknode_unl_schema.py:15` (`SHADOW_MODE`) is the pattern.
        - On the fork the model's overall score (since v8) and diversity (since v12) are advisory.
        - The gates exist only as prose: direction §4 (lines 112–126) and the validity review (lines 234–250).
        - There is no change-control register (direction work-sequence step 4) and no gate record (step 6).
    - *Missing:* a guard in code, the register and the gate record.
    - *Deliverable:*
        - A `SHADOW_ONLY` default in the entry-profile module. Binding mode is accepted only with a promotion record whose hash matches a recorded decision. Otherwise everyone is on the standard profile and the output is a report.
        - `docs/governance/ai-governance-change-control-register.md` (new) lists each of the following with its version, hash and a dated decision line: formula, sub-scorer, diversity formula, selector parameters, strict-profile parameters, flag model, prompt and execution profile.
        - The gate list below goes in the register as the single recorded list, all unchecked.
    - *Acceptance:* a test shows that binding mode without a record falls back to shadow. The register's hashes match the switch-round manifest. The doc gates pass.
    - *Estimate:* 1–2 days.
    - *Depends on:* step 3. Step 1 hashes are filled in as they land.
- [ ] **6. Run v3 beside the model for four weekly shadow rounds on the fork, then switch the production rounds**
    - *Today:*
        - Testnet runs weekly (`SCORING_CADENCE_HOURS=168`, fork `.env.testnet:24`).
        - The offline harness is `fetch_rounds.py:38-40` (fork clone path, rounds 12–19 by default; `--rounds 28` fetched the first v12-era round), which drives the fork's `scripts/replay_model_candidate.py`, and `shadow_eval.py:662` (`--scorer-version`, 1–3). Since 2026-10-23 the local fork clone is at `e70515d`, and `_verify_code_pins` (`:197-220`) also checks the `diversity_formula` pin, so v12-era rounds can be evaluated (step 1a record).
        - The rollout pattern exists: diversity formula v1 went main → devnet manual round → testnet slot, deployed outside the three-hour `AWAITING_COMMIT_CLOSE` window, with the sidecar image, explorer and governance row shipped alongside (fork `docs/DeterministicDiversity.md:77`).
        - Fork dry runs (`docs/ScoringOperations.md:136-166`) stop after selection and publish nothing.
    - *Missing:* counted rounds, a weekly record and the switch.
    - *Deliverable:*
        - For each counted round: `results-<round>.json`, plus a dated row in `docs/governance/dunl-subscorer-shadow-weekly-2026.md` (new) with flips, overlap, per-dimension deltas and the internal-control result.
        - After four clean rounds: the 1b set deployed (a devnet manual round, then the testnet slot) and the Z2 status updated.
    - *Acceptance:*
        - These criteria are fixed here before the first counted round: the internal control passes every round; there is no ineligible→eligible flip; every eligible→ineligible flip and seat change is explained from the scores; UNL overlap is at least 24/25.
        - Any module change restarts the count.
        - The switch is done when the first production round's manifest carries the frozen hash and a vendoring sidecar matches at all three levels.
    - *Estimate:* 3–5 days, spread over at least four weeks (about half a day per round, plus 1.5–3 days for the switch).
    - *Depends on:* 1a for the clock, 1b for the switch, and the testnet slot staying put.

| Step | Estimate (working days) |
| --- | --- |
| 1 Pin | 3–5 |
| 2 Flag spec | 2–3 |
| 3 Strict profile | 3–5 |
| 4 Wire flag | 2–3 |
| 5 Shadow guard | 1–2 |
| 6 Shadow rounds and switch | 3–5 over ≥ 4 weeks |
| **Total** | **14–23**, with steps 2–5 inside the shadow window |

Each step is requested as a Task Node task before work on it starts. Direction work-sequence step 5 (the packet replay read-out) is done ([results, 2026-09-03](../../governance/identity-packet-replay-results-20260903.md)). Step 7 (authority-map CLI and status page) follows these six.

## Not before

- No shadow round counts before the 1a module hash is written into this plan. Rounds frozen earlier are calibration only.
- No switch before four consecutive clean counted rounds, a devnet manual round, and a published sidecar image that vendors the module.
- No switch deploy between a round's input freeze and its publication.
- No strict-profile parameter set is final before its decision line exists. The line for `entry_profile_v1` was recorded on 2026-10-23.
- No GPU flag run before the inference-cost owner is named and a frozen packet set covers the round's candidates. The owner was named on 2026-10-23; the packet set is open.
- No flag, legitimacy score or strict-profile result enters the fork's selector, the l1v2 registry or any trust view before every gate below is recorded as passed.

## Promotion gates

From the direction (§4, adopting the [validity review](../../governance/ai-governance-validity-review.md) list). Model-derived output stays `SHADOW_ONLY` until all of these pass:

- [ ] Signed reconstructable observations
- [ ] Three independent observers and replayers
- [ ] An open proposal lane
- [ ] A pre-registered held-out evaluation with material lift and no unsafe positive admission
- [ ] Hold/no-op on model deletion
- [ ] Published replay cost
- [ ] The drill set

For the flag itself (direction §3 and the first counterargument):

- A candidate flag model or prompt replaces the incumbent only if it beats it by the margin on a pre-registered, held-out set.
- Promotion from flag to weighted input, still under the formula and never to direct authority, needs a model that beats the deterministic baseline on a pre-registered, held-out, independently constructed set of fabrications and obscure real operators. It also needs every lane valid, no real operator in a fabrication band, determinism across distinct-owner hosts, and a published replay cost.

## Does not change

- **Consensus:** Cobalt, finality, block production and the fork's postfiatd consensus are untouched. There is no node binary, release, transaction or Orchard boundary. Tests stay focused: the harness, the mirror and `postfiat-consensus-cobalt` entry-profile tests, not the workspace or Orchard suites.
- **The validator set:** the l1v2 registry and trust graph are untouched. On the fork the same formula and selector (cutoff 40, size, gap 3) keep deciding the UNL. At the switch only the source of four sub-scores changes. No flag seats or removes anyone.
- **The fee rules:** unchanged on l1v2 and on the fork. Fee votes stay read-but-neutral in the sub-scorer.
