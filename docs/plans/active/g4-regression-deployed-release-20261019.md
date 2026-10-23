# G4 Regression on the Deployed Release `8bed9b90`: Executable Plan

**Status:** **Attempt 4 CLOSED 2026-10-22: PASS** on the deployed executable `eea96ba6…` (source `86706699`); see
[Result 2026-10-22](#result-2026-10-22-attempt-4-deployed-binary).
**CLOSED 2026-10-20: PASS.** Attempt 3 (candidate `8644f0af`, the STO-07 fix) meets the
G4 criteria; see [Result 2026-10-20](#result-2026-10-20-attempt-3-after-the-fix). Attempt 2
(`29824ed7`, 2026-10-19) was **PUBLIC TESTNET BLOCKED** by the regression since `f0013c29`; see
[Result 2026-10-19](#result-2026-10-19).
**Date:** 2026-10-19
**Parent:** [Storage scaling milestone](../completed/storage-scaling-milestone.md)
**Predecessor:** [Model-floor G4 plan](model-floor-g4-campaign-plan.md) (PASS on `d0ae79f3`, 2026-08-30)

## Purpose

The deployed release `fastlane-cap-20261014` (source `8bed9b90`, live since
2026-10-15) descends from the `d0ae79f3` line that passed G4. This campaign
checks that the code now running still meets the G4 criteria. It is a
regression check only: it changes no milestone label. G3/G5 still need the
height-915 archive and the height-924 custodian, and G6 still needs fresh
copies and a separate decision. Everything runs on the work server. There is no
validator-host contact and no transaction.

## Frozen identities

| Item | Value |
| --- | --- |
| Candidate source | `8bed9b9073f97d0c45d0babb9756636516a2e3f7` on `origin/main`; tree `9cd9c0dffe5eed8eea5ee475f4174d306103376b` |
| Candidate checkout | `~/.cache/storage-g4-20261019/source` (clean, detached) |
| Runner/verifier | `ae6ec9cbc4781e9a0127ea2a8f95b41949e16589` (`postfiatchad/corrected-g4-vote-lock-gate`), clean detached checkout at `~/.cache/storage-g4-20261019/runner` |
| Prepared input | manifest `ec5a4715…98c3` (unchanged); height-5,000 fleet `4e2f24b7…4086`, tip `d246148a…4930`, state root `b3d2f5eb…a5f8` |
| Rollback binary (G2) | `0ac4e190` release, SHA-256 `7cb88119…69de`, `~/repos/postfiat-storage-g2-binaries-0ac4e190/rollback/release/postfiat-node` |
| Output root | `~/.cache/storage-g4-20261019/` (private) |

**Runner choice:** `main` is not used. At `8bed9b90`, the scripts in `benchmarks/storage-scaling/` do
not include the certified-send work gate, the vote-lock work gate, the
round-coverage gate, the 5 ms height-model floor, or
`--derive-from-prepared-input-manifest`. Those scripts would not run the gates
that passed, so the passing runner `ae6ec9cb` is used. That runner requires the
batch helper to embed the runner revision, so the helper is rebuilt from the
`ae6ec9cb` checkout. Its hash is compared with the hash bound by the passing run,
`bdff4bd8…f7f6`.

**Prepared-input finding (2026-10-19):** The manifest's source tree,
`~/repos/postfiat-storage-g4-428fe7c9-ae658441-v4`, no longer exists. The runner's
own source verification fails because its private bundle is missing. The
directory `~/repos/postfiat-storage-g4-4f976290-ae658441` contains fleets only
up to height 1,550. The only remaining copy of every bound input is the input
imported into the passing run, `P=~/repos/postfiat-storage-g4-measurement-ae6ec9cb-d0ae79f3-v1`.
That run must never be deleted and is read from only.

## Gates (in order; `C=~/.cache/storage-g4-20261019`, `S=8bed9b9073f97d0c45d0babb9756636516a2e3f7`)

| Gate | Commands and inputs | Pass |
| --- | --- | --- |
| G1 build | In `$C/source`: `cargo build --release --locked -p postfiat-node`. In `$C/runner`: `cargo build --release --locked -p postfiat-bench --bin postfiat-storage-corpus-batches`. Use Rust 1.95.0. `POSTFIAT_ZIG=~/.local/zig-0.17.0-dev.1857/zig`; `CC`, `CXX`, `AR` and the linker are set to the checkout's `scripts/zig-*` wrappers. The log is `$C/build.log`. | Both builds exit 0 with zero warnings. The node embeds `8bed9b90`/`release`. Both SHA-256 hashes are recorded. |
| G1 freeze | In `$C/source`: `cargo test -p postfiat-node {completed_index,certified_send,vote_lock,transactional_verify_only} --locked`. Copy both binaries, mode 0555, into `$C/freeze/`. Write `$C/freeze/g1-candidate-manifest.json` with the schema `postfiat.storage.corrected_g1_candidate.v1`. | All four filters pass. The manifest binds the source, tree, binary, and `Cargo.lock`. |
| G2 safety | Run `run_rollback_rehearsal.py --node-bin $C/freeze/postfiat-node --rollback-node-bin <0ac4e190 binary> --expected-source-revision $S --rollback-source-revision 0ac4e190aa3e7dbb7781bb5d8628474eecb47ef5 --output-dir $C/g2/rollback`. Then run `run_tamper_evidence.py --expected-source-revision $S --rollback-report $C/g2/rollback/compatible-rollback-report.json --output-dir $C/g2/tamper`. Both scripts come from `$C/runner`. | Both reports have status `PASS`, six validators converge, and the tamper matrix has no uncovered requirement. |
| Input restore | Copy each bound input from `P` back to its bound path under `~/repos/postfiat-storage-g4-428fe7c9-ae658441-v4`. Advances 1–5 come from `P/prepared-input/advances/advance-000N-{receipt,report}.json` and go to `canonical/{receipts,normalized}/`. The fleets for heights 50 and 5,000 come from `P/prepared-fleets/`. The height-50 and height-5,000 corpora come from `P/corpora/`. `P/canonical/snapshots/height-50.snapshot` becomes `canonical/snapshots/advance-1-to-50.snapshot`. `P/shared/{snapshots/height-1.snapshot,topology.json,private}` go to `shared/`. The copy takes about 20 GB. | — (the next gate verifies the copy) |
| Rebind | Run `run_paired_campaign.py --derive-from-prepared-input-manifest ~/repos/postfiat-storage-model-floor-prepared-input-d0ae79f3/prepared-input-manifest.json --candidate-build-manifest $C/freeze/g1-candidate-manifest.json --node-bin $C/freeze/postfiat-node --batch-builder-bin $C/freeze/postfiat-storage-corpus-batches --expected-source-revision $S --output-dir $C/prepared-input`. | Every SHA-256 bound in `ec5a4715` matches again, and the derived manifest is written. |
| Chain opens | Run `run_prepared_fleet_preflight.py --source <restored canonical-height-5000> --expected-sha256 4e2f24b7… --workspace $C/preflight --report $C/preflight.json`. Then run `$C/freeze/postfiat-node status --data-dir $C/preflight/…/validator-N --expect-height 5000` for N = 0…5. | The report passes, and all six clones report height 5,000 with tip `d246148a…`. |
| G4 run | Run `timeout --signal=INT --kill-after=120s 7200s python3 -u run_paired_campaign.py --node-bin $C/freeze/postfiat-node --batch-builder-bin $C/freeze/postfiat-storage-corpus-batches --expected-source-revision $S --prepared-input-manifest <derived> --output-dir $C/measurement`. The run uses the 5+5+5 matrix, 50 rounds per window. | See the criteria below. |

**G4 pass criteria (unchanged):** At height 5,000, p95 consensus-round time and
p95 wallet-to-final time are each ≤1.10× their height-50 values. Every literal
receipt matches and is final, and all six validators agree on every window. The
`redb` and certified-send work and the vote-lock work stay bounded. There are
zero full-history reads. Every coverage gate passes, along with the height-model
gate with its 5 ms floor. The final report records `evidence_eligible = true`.

## Stop conditions and the one-run rule

- Any failed gate stops the campaign. One diagnosis follows from the gate's own
  artifacts. There is no fix and no retry.
- If the prepared chain does not open on the new binary, the campaign stops and
  reports. Rebuilding the height-5,000 chain takes about 4 hours, and that
  decision belongs to the operator.
- If free disk space is below 15 GB at the start of any gate, the campaign stops.
  Before Input restore, rebuildable `target/` directories may be removed. This
  happens only after `$C/freeze/` holds the hashed binaries.
- The 2-hour `timeout` stops G4. An interrupted run counts as the run.
- The binary stays fixed from G1 until G4 ends. There is exactly one G4 run. A
  further attempt needs a new plan and an explicit operator go.

## Reported at the end

The report gives:

- the source, tree, and binary/helper SHA-256 values;
- the G1 manifest and G2 report hashes;
- the derived manifest hash;
- both ratios with their raw p95 values;
- the per-gate verdicts;
- the campaign report and checkpoint SHA-256;
- elapsed time;
- free disk space.

PASS or FAIL is stated plainly. A failure includes its one diagnosis. Private
material stays in `$C/`.

## Bound re-derivation 2026-10-19

Attempt 1's G2 rollback rehearsal stopped on `reads=74/64` for the proposal.
The per-round page cost of `8bed9b90` is fixed and higher than that of `d0ae79f3`. `f0013c29`
re-validates the generation pointer on every handle lookup, which adds one metadata
read per state read. `d8f65885`/`943c4ca7` make `read_fastpay_ledger` do about 11
lookups where it did 2. The old figures come from the `d0ae79f3` G2 (round 1 of all
three phases) and from the `ae6ec9cb` G4 packet (all 250 selected-lane rounds,
identical at heights 50 and 5,000). The new figures come from the attempt 1 G2
current-post-activation round 1. Each bound keeps its old headroom and is
rounded up to a multiple of 16 (`benchmarks/storage-scaling/run_campaign.py`).

| Constant | Governs | Old bound | Old obs | Headroom | New obs | New bound |
| --- | --- | --- | --- | --- | --- | --- |
| `MAX_PROPOSAL_PAGE_READS_PER_ROUND` | proposal | 64 | 29 | 2.21× | 74 | 163.3 → 176 |
| (same constant) | validator reconstruction | 64 | 35 | 1.83× | 80 | 146.3 → 160 (176 covers it) |
| `MAX_APPLY_PAGE_READS_PER_VALIDATOR_ROUND` | local + certified apply | 64 | 34 | 1.88× | 79 | 148.7 → 160 |
| `MAX_APPLY_PAGE_WRITES_PER_VALIDATOR_ROUND` | apply writes | 32 | 8 | 4.0× | 8 | 32 (unchanged) |

The bounds remain per-round constants that do not depend on height, and
`full_history_*` must still be 0. The follow-up that caches the pointer
validation is a candidate in the
[next release plan](next-validator-release-plan-20261101.md#candidates).

**2026-10-20, back down after the fix.** `8644f0af` reuses the validated pointer binding while a
handle is open, so the per-lookup pointer read is gone. The extra `read_fastpay_ledger` lookups
remain: 8 more read transactions per stage than August (450 against 354 per round). The observed
figures are the same in the attempt 3 G2 current-binary phases and in all 250 G4 rounds at heights
50 and 5,000. They are lower than attempt 2's but not equal to August's, so 64 / 64 / 32 is not
restored. The same headroom rule gives:

| Constant | Governs | Aug obs | Attempt 2 obs | Attempt 3 obs | Bound (was 176 / 160 / 32) |
| --- | --- | ---: | ---: | ---: | --- |
| `MAX_PROPOSAL_PAGE_READS_PER_ROUND` | proposal | 29 | 74 | 37 | 37 × 64/29 = 81.7 → **96** |
| (same constant) | validator reconstruction | 35 | 80 | 43 | 43 × 64/35 = 78.6 → 80 (96 covers it) |
| `MAX_APPLY_PAGE_READS_PER_VALIDATOR_ROUND` | local + certified apply | 34 | 79 | 42 | 42 × 64/34 = 79.1 → **80** |
| `MAX_APPLY_PAGE_WRITES_PER_VALIDATOR_ROUND` | apply writes | 8 | 8 | 8 | **32** (unchanged) |

The G2 rollback binary `0fa55d0b` still reads 74 / 80 / 79 in its rollback phase. That is
inside the new bounds, with apply at 79 of 80. The runner branch `g4-runner-bounds-20261019`
(`51a19272`) stays as the record of the 176 / 160 bounds.

## Deviation 2026-10-19

Operator decision: the harness design is unchanged and the bounds are committed.
The deployed bytes cannot carry the new bounds, because the candidate's G2
scripts require their checkout's HEAD to equal the binary's embedded revision.
The campaign therefore qualifies the next release candidate rather than the
exact deployed `8bed9b90` binary.

- [x] Candidate: the `main` commit that adds this section (`S` above becomes that commit).
  Its node code is the deployed source `8bed9b90` plus the crate changes merged since:
  - `2737f080` offline `fastswap-committee-migrate` command (`crates/node/src/fastswap_committee_migration.rs`, `crates/storage/src/fastswap_store/committee_migration.rs`);
  - `4bc5dca3` (#131, merged by `b18e4e02`): unique `cobalt_handoff` fixture temp root, test code only (`crates/node/src/cobalt_handoff.rs`).
- [x] Runner: `51a1927220637158f26a3b1383be1065e7f1ada4` on `g4-runner-bounds-20261019`,
  which is `ae6ec9cb` plus the same bound change. The helper is rebuilt from it.
- [x] The harness scripts bind to these same commits. No script is modified outside its tree.
- [x] Unchanged from attempt 1: the rollback binary `signer-rotation-20261007`
  (`0fa55d0b`, SHA-256 `decaa411…370f`), the G2 scripts taken from the candidate checkout, and the prepared input.
- [x] Attempt 2 runs from G1 tests through G4. Attempt 1's G1 and G2 records are
  kept as attempt 1 in `$C/status.json`.

## Result 2026-10-19

- [x] G4 run: 10:52:46–12:03:29Z (3,975 s), output `~/repos/postfiat-storage-g4-regression-20261019` (work server, private).
- [x] Verdict: **PUBLIC TESTNET BLOCKED**, `evidence_eligible = false`. No devnet or network contact.

| Item | Value |
| --- | --- |
| Candidate `C` | `29824ed7becc634ab33679a4c8bcb5516856c00e`; node SHA-256 `df0114a2…b6ac` |
| Runner `R` | `51a1927220637158f26a3b1383be1065e7f1ada4`; helper SHA-256 `fb83d467…5f13` |
| `frozen-binaries.json` | `47a38dfc…db08` |
| G1 manifest / G2 rollback / G2 tamper | `71497ca5…6261` / `6f0a88b2…5da2` / `570c22ed…0ca8` (37 tests) |
| Derived prepared-input manifest | `f0072483…4c51` (from `ec5a4715…98c3`) |
| `campaign-report.json` | `94188f3ce5b294e898deeee9c34cee89ca05e748e3c691a34f7aa5e07206140e` |
| `campaign-checkpoint.json` | `d1bb6e977cb7d878cf4475d9c6d5a265660abadb6cdd4525b886f516e4fed831` |
| Free disk at close | 20 GB |

### Gates

| Gate | Result | Figures |
| --- | --- | --- |
| G1 build, freeze, tests | PASS | four filters pass; manifest `71497ca5…` |
| G2 rollback, tamper | PASS | six validators converge; 37 tamper tests, no uncovered requirement |
| Input restore, rebind | PASS | every bound SHA-256 matches; derived manifest `f0072483…` |
| Chain opens | PASS (attempt 2b) | six clones at height 5,000, tip `d246148a…`, root `b3d2f5eb…` |
| Receipts, agreement, coverage | PASS | 15/15 windows: literal receipts exact, six validators converge, round coverage passes |
| Certified-send, vote-lock, backend work | PASS | every selected window within bounds; zero full-history reads |
| Consensus round, 5,000 vs 50 | PASS (barely) | p95 1,635.8 / 1,487.9 ms = 1.0994 (≤1.10) |
| Wallet-to-final, 5,000 vs 50 | **FAIL** | p95 1,735.2 / 1,570.9 ms = 1.1046 (>1.10) |
| Height 50 vs legacy (consensus, wallet) | **FAIL** | 1.531, 1.600 (>1.10; August 0.345, 0.356); legacy 972.0 / 981.9 ms |
| Height-cost model, 5 ms floor | **FAIL** | `certified_sends_ms`: per-window p95 median 662.8 → 842.4 ms, fitted +170 ms, threshold 150.1 ms, r² 0.76 |

The runner's `release_pass` requires all of these (`run_paired_campaign.py:3376-3388` at `R`).

### Per-stage p95 (per-window median, ms): August `d0ae79f3` vs today `29824ed7`

| Stage | Aug h50 | Today h50 | Aug h5000 | Today h5000 | Height-material today |
| --- | ---: | ---: | ---: | ---: | --- |
| `certificate_ms` | 167.4 | 762.8 | 172.1 | 770.3 | no |
| `certified_sends_ms` | 80.2 | 662.8 | 81.1 | 842.4 | **yes** |
| `local_vote_ms` | 40.2 | 440.6 | 42.7 | 478.6 | no |
| `vote_requests_ms` | 65.3 | 586.1 | 69.2 | 718.0 | no |
| `proposal_ms` | 31.6 | 93.9 | 32.4 | 99.4 | no |
| `post_apply_status_ms` | 0.9 | 27.7 | 0.9 | 29.2 | no |
| `local_apply_ms` | 31.7 | 38.9 | 33.2 | 42.8 | no |
| `write_commit_ms` | 8.1 | 8.1 | 9.2 | 8.8 | no |

The legacy lane did not change (height-50 p95 992.5 → 972.0 ms consensus; 336 → 338 MB written per
window), so the host environment is not the cause.

### Mechanism

- `f0013c29` (bounded writer lease) replaced the always-open store with a weak-registry lease
  (`crates/storage/src/transactional.rs:97`, `shared_transactional_store` at `:2664`). A lookup
  reuses a live handle only while another caller holds one (`:2683`). Otherwise it reopens the
  database (`:2686`), and the database closes when the last `Arc` drops.
- On every close, redb 4.2.0 writes the allocator-state (free-space) table and trims the file
  (`redb-4.2.0/src/db.rs:1325` `ensure_allocator_state_table_and_trim`, `:1352` `close_database`,
  `:1366` `Drop for Database`). This cost grows with the database size.
- Disk bytes written per selected window: 0.47 GB in August at height 50 → 10.9 GB today (23×).
  At height 5,000: 3.3 GB → 36.8 GB (78× the August height-50 figure). Logical writes are the same.
- Lookups per window went from about 17,700 to 44,700 (`f0013c29` pointer re-validation, plus
  `d8f65885`/`943c4ca7` in `read_fastpay_ledger`), so the number of reopens grew as well.

### Harness gap

The runner's work counters count only the application's own fsyncs (`fsync_count`,
`run_campaign.py:935`). They do not count redb's writes at close time. The work gates therefore
passed while the bytes written per window grew 23×. The fix adds an open/close counter.

### Pipeline-glue fixes (before the run; records in `~/.cache/storage-g4-20261019/status.json`)

- [x] Attempt 1 (`8bed9b90`): stopped at G2 on the page bound. Bounds were re-derived at `29824ed7`
  ([above](#bound-re-derivation-2026-10-19)).
- [x] Attempt 2: the pipeline's helper up-to-date check was corrected.
- [x] Attempt 2a: chain-open stopped because the copied pointers named the original database
  directory. Attempt 2b rebases the pointers the way G4 does (`run_campaign.py:271`), then opens
  all six validators. PASS.
- [x] No node, runner, or gate script changed. The binary stayed fixed from G1 to the end of G4.

### Next

- [x] Fix the store handle lifetime ([Fix 2026-10-20](#fix-2026-10-20)).
- [x] One re-run on the fix commit: PASS
  ([Result 2026-10-20](#result-2026-10-20-attempt-3-after-the-fix);
  [next release plan](next-validator-release-plan-20261101.md#candidates);
  [STO-07](../../review/defect-inventory-20260910.md)).

## Fix 2026-10-20

`transport-validator-serve` now holds one store handle per request (it also covers the next status
read and is released before the connection blocks), the round driver holds one per round, and
`status` holds one for its body (`crates/node/src/store_lease.rs`, `transport_runtime.rs`). While a
handle is open, lookups reuse it and its validated pointer binding without reading the pointer file;
the next open re-validates (`crates/storage/src/transactional/generation.rs`). The ≥50 ms backoff
remains for another process holding the file; a close still running in this process is polled every
1 ms (`crates/storage/src/transactional/lease.rs`). Disk format, pointer file, consensus and execution
are unchanged. In one six-validator round
(`transactional_six_validator_round_opens_each_database_a_bounded_number_of_times`), database opens
per validator fell from 126 to 8, and on the proposer from 163 to 5. Each stage's `storage_work`
now reports `database_opens`/`database_closes`, and `run_campaign.py` on main adds them next to
`page_reads`; the runner `R` stays at `51a19272`, so in the re-run they appear only in the raw stage
reports. The re-run freezes `S` and `C` on the fix commit, reuses `R` and the inputs at the manifest
paths, keeps the per-round page bounds from `29824ed7`, and must pass the unchanged G4 criteria. It
should also show per-window disk writes back near August's (0.47 GB at height 50, 3.3 GB at height
5,000), per-stage p95 near the August column above, and stage `database_opens` near zero.

## Result 2026-10-20 (attempt 3, after the fix)

- [x] G1 tests through G4 on the fix commit; G4 campaign 12:22:22–13:17:10Z (3,288 s; gate
  12:17:41–13:17:10Z), output `~/repos/postfiat-storage-g4-regression-20261020` (work server, private).
- [x] Verdict: **PASS**, `evidence_eligible = true`, `no_positive_linear_height_relationship = true`.
  No validator-host contact, no transaction (`network_contacted = false`).
- [x] Campaign **CLOSED**.

| Item | Value |
| --- | --- |
| Candidate `C` | `8644f0afdab472c62db803c0b663b207dd08fcdb` (tree `0b85cf52…9f81`); node SHA-256 `d1799edb…3e93b` |
| Runner `R` | `51a1927220637158f26a3b1383be1065e7f1ada4`; helper SHA-256 `fb83d467…5f13` (attempt 2's binary) |
| Rollback binary | `signer-rotation-20261007` (`0fa55d0b`), SHA-256 `decaa411…370f` |
| `frozen-binaries.json` | `818d071c…efba4` |
| G1 manifest / G2 rollback / G2 tamper | `8fd73286…9dde` / `83340ab9…dcaae` / `410e8478…19cf` (37 tests) |
| Derived prepared-input manifest | `247e31f2…27df` (from `ec5a4715…98c3`) |
| `campaign-report.json` | `d1e9b39c6498558da7c2bd3aa979ec2a71fd6cffd0a3c9abe376c513ebb0aac0` |
| `campaign-checkpoint.json` | `0b6608e3fb3a49e614a5d44dcebf7d900c1cee38bf59f023f448b0427b54ec11` |
| Free disk at close | 175 GB |

### Gates

| Gate | Result | Figures |
| --- | --- | --- |
| G1 build, freeze, tests | PASS | `completed_index` 28, `certified_send` 48, `vote_lock` 19, `transactional_verify_only` 2 passed |
| G2 rollback, tamper | PASS | six validators converge; 37 tamper tests, no uncovered requirement |
| Input restore, rebind | PASS | every bound SHA-256 matches; derived manifest `247e31f2…` |
| Chain opens | PASS | six clones at height 5,000, tip `d246148a…`, root `b3d2f5eb…` |
| Receipts, agreement, coverage | PASS | 15/15 windows: literal receipts exact, six validators converge, round coverage passes |
| Certified-send, vote-lock, backend work | PASS | every selected window within bounds; zero full-history reads |
| Consensus round, 5,000 vs 50 | PASS | p95 338.5 / 329.9 ms = 1.0261 (≤1.10; August 1.0581) |
| Wallet-to-final, 5,000 vs 50 | PASS | p95 453.0 / 438.7 ms = 1.0326 (≤1.10; August 1.0623) |
| Height 50 vs legacy (consensus, wallet) | PASS | 0.340, 0.447 (August 0.345, 0.356); legacy 970.5 / 980.8 ms |
| Height-cost model, 5 ms floor | PASS | no stage material; largest fitted delta `vote_requests_ms` +3.7 ms (threshold 7.7 ms) |

### Per-stage p95 (per-window median, ms; height 50 / height 5,000)

| Stage | August `d0ae79f3` | Attempt 2 `29824ed7` | Attempt 3 `8644f0af` |
| --- | ---: | ---: | ---: |
| `certificate_ms` | 167.4 / 172.1 | 762.8 / 770.3 | 156.3 / 152.9 |
| `certified_sends_ms` | 80.2 / 81.1 | 662.8 / 842.4 | 81.5 / 82.7 |
| `local_vote_ms` | 40.2 / 42.7 | 440.6 / 478.6 | 39.0 / 38.6 |
| `vote_requests_ms` | 65.3 / 69.2 | 586.1 / 718.0 | 69.3 / 71.9 |
| `proposal_ms` | 31.6 / 32.4 | 93.9 / 99.4 | 33.1 / 33.0 |
| `post_apply_status_ms` | 0.9 / 0.9 | 27.7 / 29.2 | 0.7 / 0.6 |
| `local_apply_ms` | 31.7 / 33.2 | 38.9 / 42.8 | 31.3 / 30.0 |
| `write_commit_ms` | 8.1 / 9.2 | 8.1 / 8.8 | 7.9 / 8.1 |

### Disk writes and lookups per selected window (height 50 / height 5,000)

| Measure | August | Attempt 2 | Attempt 3 |
| --- | --- | --- | --- |
| Disk bytes written (median of 5) | 0.47 / 3.3 GB | 10.9 / 36.9 GB | 1.03 / 3.68 GB (ranges 1.00–1.04, 3.01–3.76) |
| Read transactions (lookups) | ~17,700 | 44,700 / 44,700 | 22,500 / 22,500 |
| Page reads | — | 47,400 / 47,400 | 25,200 / 25,200 |
| Page reads per round: proposal / reconstruction / apply | 29 / 35 / 34 | 74 / 80 / 79 | 37 / 43 / 42 (8 writes) |
| Stage `database_opens` / `database_closes` | — | not reported | 0 / 0 in all 6,000 stage reports (500 rounds × 12 stages) |

Runner `R` does not total the open counters, so the last row comes from the raw stage reports
(`lanes/selected-indexed/*/round-*/iterations.jsonl`). The height-5,000 writes are back near
August's (1.1×). The height-50 writes are 2.2× August's, though 10.6× below attempt 2. This is
recorded only: it is not a gate, the cause is not yet known, and the August packet is no longer
on disk to compare against. The legacy lane is unchanged (970.5 ms p95, 0.34 GB per window).

### What it proves

- The running code line with `8644f0af` meets the unchanged G4 criteria. The regression from
  `f0013c29` is gone, and every stage is back at the August level.
- The deployed release `fastlane-cap-20261014` (`8bed9b90`) does **not** contain the fix. It
  still has STO-07 until the next release
  ([next release plan](next-validator-release-plan-20261101.md#candidates)).
- No milestone label changes. G3 (the height-924 replay with our custody copy, plus the 915
  replacement) can start after that release.

### Pipeline-glue fixes (today; records in `~/.cache/storage-g4-20261019/status.json`)

- [x] Copy gate sources: `P` was deleted on 2026-10-20 with the other lane's approval, so attempt 3
  stopped at the copy gate (12:03:42Z). The gate now takes each input from `P` if it exists.
  Otherwise it hash-checks the copy already at the manifest path. For the private bundle and the
  topology only, it falls back to attempt 2's G4 output and hash-checks before and after the
  copy. The expected hashes are still `ec5a4715`'s.
- [x] Resume labels: a resumed run now takes its label from the frozen attempt
  (`attempt 3 continued`), not the hard-coded `attempt 2a`/`2b`. The G1 and G2 PASS records were kept.
- [x] No node, runner, or gate script changed. The binary stayed fixed from G1 to the end of G4.
- [x] Page bounds re-derived down after the run
  ([Bound re-derivation](#bound-re-derivation-2026-10-19)).

## Attempt 4 (2026-10-22, deployed binary)

Operator decision (2026-10-22): the storage packet qualifies the running code. The packet needs G1,
G2, G4, the exact replays and the migration rehearsal on one source and one binary
([G5](../completed/storage-scaling-milestone.md#g5-offline-qualification-packet)), and the replays ran on the
deployed executable. G1 tests, G2 and G4 are therefore re-run with attempt 3's procedure, with the
node binary replaced.

| Item | Value |
| --- | --- |
| Candidate `C4` | `86706699f646405743385beabf609c6771a518a3` (tree `03e927ad04b65b110829d78135db9e3e5f15a331`), release `store-handle-20261021`, on all six validators since 2026-10-21; `Cargo.lock` `45bb2ca0…4fce` (same as attempt 3) |
| Node | **the deployed executable**, SHA-256 `eea96ba6761ed223047d7781663100d34efe5641d36031bd50874bd9c8b41f36`, from the release stage `~/.postfiat/deployments/store-handle-20261021/stage/rootfs/opt/postfiat/releases/store-handle-20261021/postfiat-node`. Not rebuilt. It embeds `86706699`/`release`, the pipeline's acceptance check. The release build is `cargo build --release --locked -p postfiat-node --bin postfiat-node` with default features, Rust 1.95.0, 0 warnings (`~/.cache/release-store-handle-20261021/node-builds.json`). |
| Runner `R` / helper | `51a19272` (`g4-runner-bounds-20261019`), helper `fb83d467fddc0ef1c414df082c71f5f42b7bda8011cee6df9324620310725f13`, unchanged. Main carries 96 / 80 / 32 in `run_campaign.py`, but main's runner lacks the work, coverage and derivation gates of `R`, and no pushed `R`-line commit carries 96 / 80 / 32. G4 therefore runs with `R`'s 176 / 160 / 32 and is checked against 96 / 80 / 32 at closure. G2 runs `C4`'s own scripts, which already carry 96 / 80 / 32 (`0293e00d` is in `86706699`). |
| Rollback binary | `signer-rotation-20261007` (`0fa55d0b`), SHA-256 `decaa411376a125fb377a29037b6dd470afb2208a268d30a3ce8130f571b370f` |
| Inputs | the 18 inputs of manifest `ec5a4715…98c3`, all present at the manifest paths under `~/repos/postfiat-storage-g4-428fe7c9-ae658441-v4`; the copy gate hash-checks them in place |
| Output | `~/repos/postfiat-storage-g4-regression-20261022` (work server, private) |
| Pipeline glue | `~/.cache/storage-g4-20261019/refreeze-attempt-4.sh`: moves the source checkout to `C4`, freezes the deployed executable, moves attempt 3's records to `attempt-3/`. `pipeline.sh`: only `OUT` changed (backup `pipeline.sh.attempt4.bak`) |

Unchanged: the gates, the G4 criteria, the stop conditions and the one-run rule above. There is no
validator-host contact and no transaction.

## Result 2026-10-22 (attempt 4, deployed binary)

- [x] G1 tests through G4 on `C4` with the deployed executable, which the pipeline accepted unchanged.
  The pipeline ran 11:09:42–12:32:01Z; the G4 gate ran 11:32:31–12:32:01Z (campaign 3,276 s).
  Output: `~/repos/postfiat-storage-g4-regression-20261022` (work server, private).
- [x] Verdict: **PASS**, `evidence_eligible = true`, `no_positive_linear_height_relationship = true`,
  `network_contacted = false`. No validator-host contact and no transaction.
- [x] Pipeline glue only: `refreeze-attempt-4.sh` and `OUT` in `pipeline.sh`. No gate failed and nothing
  was resumed. The binary stayed fixed from G1 to the end of G4.

| Item | Value |
| --- | --- |
| Node | `eea96ba6761ed223047d7781663100d34efe5641d36031bd50874bd9c8b41f36` (deployed; embeds `86706699`/`release`) |
| Helper / rollback | `fb83d467…5f13` (`R` = `51a19272`) / `decaa411…370f` (`0fa55d0b`) |
| `frozen-binaries.json` | `b5f8eb37f574b2f6f585b44f1249a2410187cde4e8197769867c6bc65ec11bc2` |
| G1 manifest / G2 rollback / G2 tamper | `df6534a0…74ffc` / `c64882e6…e0ee1` / `6eff6241…9b30` (37 tests) |
| Derived prepared-input manifest | `1dd2b96b…edcc9` (from `ec5a4715…98c3`) |
| `campaign-report.json` | `7aa8d72ce4579be61321dc5bd624da720c8804301d5b6ac8edf7bb6f6166dfb0` |
| `campaign-checkpoint.json` | `ce48959d15edf5819a591f0fc4541c211e1c14079fd51e590e74f89a4e131eb4` |
| Free disk at close | 121 GB |

| Gate | Time (UTC) | Result | Figures |
| --- | --- | --- | --- |
| G1 tests | 11:09:42–11:10:59 | PASS | `completed_index` 28, `certified_send` 48, `vote_lock` 19, `transactional_verify_only` 2 passed |
| G2 rollback, tamper | 11:10:59–11:22:00 | PASS | six validators converge; 37 tamper tests, no uncovered requirement; `C4`'s scripts check 96 / 80 / 32 |
| Copy (in-place check) | 11:22:01–11:23:17 | PASS | all 18 inputs already at the manifest paths, hashes match `ec5a4715` |
| Rebind | 11:23:18–11:25:45 | PASS | derived manifest `1dd2b96b…` |
| Preflight | 11:25:46–11:31:07 | PASS | fleet `4e2f24b7…` before and after |
| Chain opens | 11:31:07–11:32:30 | PASS | six clones at height 5,000, tip `d246148a…`, root `b3d2f5eb…` |
| G4 receipts, agreement, coverage | 11:32:31–12:32:01 | PASS | 15/15 windows: literal receipts exact, six validators converge, round coverage, certified-send, vote-lock and backend work gates pass; zero full-history reads |
| Consensus round, 5,000 vs 50 | | PASS | p95 357.8 / 341.3 ms = **1.0482** (≤1.10; attempt 3 1.0261, August 1.0581) |
| Wallet-to-final, 5,000 vs 50 | | PASS | p95 471.7 / 443.5 ms = **1.0637** (≤1.10; attempt 3 1.0326, August 1.0623) |
| Height 50 vs legacy (consensus, wallet) | | PASS | 0.350, 0.450 (attempt 3 0.340, 0.447); legacy 974.2 / 984.7 ms |
| Height-cost model, 5 ms floor | | PASS | no stage material; largest fitted delta `certified_sends_ms` +2.8 ms (threshold 8.2 ms) |

Per-stage p95 (per-window median, ms; height 50 / height 5,000):

| Stage | August `d0ae79f3` | Attempt 3 `8644f0af` | Attempt 4 `eea96ba6` |
| --- | ---: | ---: | ---: |
| `certificate_ms` | 167.4 / 172.1 | 156.3 / 152.9 | 159.6 / 162.8 |
| `certified_sends_ms` | 80.2 / 81.1 | 81.5 / 82.7 | 81.8 / 84.9 |
| `local_vote_ms` | 40.2 / 42.7 | 39.0 / 38.6 | 41.0 / 41.0 |
| `vote_requests_ms` | 65.3 / 69.2 | 69.3 / 71.9 | 71.5 / 72.0 |
| `proposal_ms` | 31.6 / 32.4 | 33.1 / 33.0 | 34.6 / 35.1 |
| `post_apply_status_ms` | 0.9 / 0.9 | 0.7 / 0.6 | 0.7 / 0.6 |
| `local_apply_ms` | 31.7 / 33.2 | 31.3 / 30.0 | 31.9 / 31.8 |
| `write_commit_ms` | 8.1 / 9.2 | 7.9 / 8.1 | 8.7 / 8.9 |

| Measure (selected lane) | Attempt 3 | Attempt 4 |
| --- | --- | --- |
| Page reads per stage: proposal / reconstruction / apply (max over 6,000 stage reports) | 37 / 43 / 42, 8 writes | 37 / 43 / 42, 8 writes: inside **96 / 80 / 32** (and `R`'s 176 / 160 / 32) |
| Stage `database_opens` / `database_closes` | 0 / 0 | 0 / 0 in all 6,000 stage reports (500 rounds × 12 stages) |
| Disk bytes written per window (median, range) | 1.03 / 3.68 GB | 1.04 (1.03–1.05) / 3.58 (3.38–3.76) GB; legacy 0.34 GB |

The figures come from `campaign-report.json` and the raw stage reports
(`lanes/selected-indexed/*/iterations.jsonl`). The read-only closure script is
`~/.cache/storage-g4-20261019/attempt-4-analysis/analyze.py`; run on the attempt 3 output, it
reproduces that attempt's table.

**What it proves:** the code the fleet runs, the deployed executable `eea96ba6…`, meets the
unchanged G4 criteria. Its storage work equals attempt 3's (same page counts, no database opens per
stage). Both ratios stay below 1.10, with about 2 to 3 points more height-5,000 tail than attempt 3,
and inside August's range. G1 tests, G2 and G4 are now on the same source and binary as the 924 and
1123 replays. No milestone label changes: the storage packet still needs the items in
[G5](../completed/storage-scaling-milestone.md#g5-offline-qualification-packet).
