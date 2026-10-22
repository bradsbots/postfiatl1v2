# Z2 Advisory Flag Execution Plan

**Status:** Execution plan, 2026-10-22. No step has started; work begins 2026-10-23. No step has been requested as a Task Node task yet.
**Date:** 2026-10-22
**Parent gate:** [L1v2 Public Testnet Path, Gate Zero Z2](l1v2-public-testnet-path-milestone.md#gate-zero-operator-preconditions-recorded-2026-08-30)
**Decision:** [AI governance direction of 2026-09-03](../../governance/ai-governance-direction-20260903.md), confirmed 2026-10-20 (row 1 of the [pending operator decisions](../../governance/pending-operator-decisions.md))
**Code read at:** this repository `main` `f50aeff1`; `dynamic-unl-scoring` `origin/main` `e70515d` (2026-10-17); `validator-scoring-sidecar` `origin/main` `c0389f8` (2026-10-15). Fork and sidecar line numbers below are at those commits.

## BLUF

1. **The long pole is step 6.** It needs four weekly shadow rounds, and the clock starts only when the sub-scorer module bytes are frozen (step 1a). Testnet rounds have run on Tuesdays (round 16 on 2026-07-28, round 26 on 2026-10-06). If the module is frozen by Monday 2026-10-26 and the slot does not move, the counted rounds are 10-27, 11-03, 11-10 and 11-17. The earliest production switch is then the round of 2026-11-24.
2. **Step 1 is partly done on the fork.** Since 2026-10-09 the fork computes diversity in code (diversity formula v1). The manifest pins it as `code.diversity_formula`, and sidecars vendor it. The v2 diversity band matrix is superseded. Under prompt v12 the model still supplies the other four sub-scores: consensus, reliability, software and identity.
3. **The v2 module is behind the fork.** It predates the minimum-safe-version software rule (2026-09-21), the 25-seat UNL (2026-09-24) and diversity formula v1. Its harness pins fork modules from a local clone that is 34 commits behind and ignores `code.diversity_formula`. The module that gets pinned is therefore v3: the v2 rules plus those two reconciliations. v2 stays as the record.
4. **Steps 2–5 are deterministic code and docs in this repository.** They run during the shadow weeks and do not block the switch. No flag binds anything: the flag and its strict-profile effect stay `SHADOW_ONLY` until the promotion gates below pass.
5. **No step is impossible, but one conflict must be fixed.** The existing l1v2 admission policy holds a candidate when the model output is missing (`crates/consensus_cobalt/src/validator_admission_policy.rs:334-341`, `:499-503`). That is the opposite of the decided rule. No live code calls it.
6. **Estimate:** 14–23 working days, plus the four-week shadow window, which overlaps steps 2–5. All six steps can be done by the end of November 2026 at the earliest.

## Steps

- [ ] **1. Pin the v2 sub-scorer in the round manifest** (content hash and manifest section)
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
- [ ] **6. Run v2 beside the model for four weekly shadow rounds on the fork, then switch the production rounds**
    - *Today:*
        - Testnet runs weekly (`SCORING_CADENCE_HOURS=168`, fork `.env.testnet:24`).
        - The offline harness is `fetch_rounds.py:32-34` (fork clone path, rounds 12–19), which drives the fork's `scripts/replay_model_candidate.py`, and `shadow_eval.py:448` (`--scorer-version`). The local fork clone is at `f18e6b4` (2026-08-21), so `_verify_code_pins` (`:174-198`) correctly stops on v12-era rounds.
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
- No strict-profile parameter set is final before its decision line exists.
- No GPU flag run before the inference-cost owner is named and a frozen packet set covers the round's candidates.
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
