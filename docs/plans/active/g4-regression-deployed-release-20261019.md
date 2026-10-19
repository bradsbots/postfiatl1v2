# G4 Regression on the Deployed Release `8bed9b90`: Executable Plan

**Status:** Authorized 2026-10-19 (operator go). G1 build started; no gate has passed yet.
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
