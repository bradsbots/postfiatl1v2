# G4 Regression on the Deployed Release `8bed9b90`: Executable Plan

**Status:** Closed 2026-10-19: **PUBLIC TESTNET BLOCKED**. Attempt 2 (candidate `29824ed7`) ran
G1 through G4. The height-cost model and three ratio gates failed. The cause is a performance
regression since `f0013c29`. See [Result 2026-10-19](#result-2026-10-19).
**Date:** 2026-10-19
**Parent:** [Storage scaling milestone](storage-scaling-milestone.md)
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

- [ ] Fix the store handle lifetime, then one re-run
  ([next release plan](next-validator-release-plan-20261101.md#candidates);
  [STO-07](../../review/defect-inventory-20260910.md)).
