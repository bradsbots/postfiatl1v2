# FastPay effect-anchoring release tip qualification, September 28, 2026

**Final. Nothing was deployed. No source was repaired.**
Every check that ran locally passed. The full workspace test suite was still running when the time box ended and is recorded as **PENDING**: 26 test-result groups had finished, 798 tests had passed or been skipped as ignored, 0 had failed (log: `logs/full-workspace-tests.stdout`, partial). warm-latency timed out in its first 5-minute budget while compiling and passed on a rerun.

Source tip: `c93b213755f5889565fd1f77b9e45c149a07193a` (`c93b2137`) on `release/combined-fastpay-20260928`.
It is the deployed code `f60e9639` (executable `d66cecc3…`) plus the FastPay effect-anchoring fix; see
[the design record](../../docs/status/fastpay-effect-anchoring-fix-20260928.md).
The evidence commit that follows adds only this packet.

Executable SHA-256, build 1: `1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a`.
Executable SHA-256, build 2: `1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a`.
Reproducibility: **PASS**. `cmp` compared the two executables byte for byte.
Each build came from its own clean worktree and its own copy of the September 22 release cache
(not empty-cache builds). Both used the GCC linker (`/usr/bin/gcc`, GCC in `.comment`, no Zig), the same
remap arguments and `SOURCE_DATE_EPOCH=1789514690`. Neither has RPATH or RUNPATH.

| Check | Result | Evidence |
|---|---|---|
| Two matching node executables | PASS | [Build records](node-builds.json) |
| Six original full-history checks, height 1020 (through block 1011) | PASS | [History run](history-run.json) |
| Six saved V2 full-history checks, height 1021 | PASS | [History run](history-run.json) |
| Six fresh V2 full-history checks, height 1021 | PASS | [Fresh V2 history](fresh-v2-history-run.json) |
| Current-chain replay, fresh signed validator-1 canary backup | PASS: checkpoint verified, full history replayed to 1050, root `13d9e652…` | [Result](canary-backup/result.json) |
| Fix: reproduce-first test (non-signer view-0 proposer anchors the held effect) | PASS: 1 passed | [Log](logs/fix-reproduce-first.stdout) |
| Timeout vote and view recovery, node bin tests | PASS: 4 passed | [Log](logs/view-recovery-bin.stdout) |
| Timeout votes form a timeout certificate, node lib test | PASS: 1 passed | [Log](logs/timeout-votes-lib.stdout) |
| FastPay committee, non-signer anchor, recovery and checkpoint restore, node lib tests | PASS: 22 passed | [Log](logs/fastpay-committee-lib.stdout) |
| node-fastpay (all node lib `fastpay` tests) | PASS: 24 passed | [Log](logs/node-fastpay.stdout) |
| Local governed rotation: both startup orders, convergence, restart | PASS | [Gate log](logs/governance-gate.stdout), [receipt](v2-service-receipt.json) |
| Rollback: six checkpoint verifications, deployed `d66cecc3…` | PASS | [History run](history-run.json) |
| Rollback: deployed services start and restart on six copies | PASS_STARTUP_AND_RESTART_ONLY | [Log](logs/rollback-services.stdout), [receipt](old-binary-service-receipt.json) |
| Rollback: new build full replay of restored validator-0 | PASS | [Receipt](receipts/final-candidate-on-rollback-validator-0.json) |
| Workspace check | PASS | [Log](logs/workspace-check.stderr) |
| Rust formatting | PASS | [Log](logs/format.stdout) |
| Proof public-input inventory | PASS | [Log](logs/proof-input-inventory.stdout) |
| Workspace Clippy, `-D warnings` | PASS | [Log](logs/workspace-clippy.stderr) |
| fastpay-types | PASS: 9 passed | [Log](logs/fastpay-types.stdout) |
| fastpay-execution | PASS: 11 passed | [Log](logs/fastpay-execution.stdout) |
| cobalt-handoff-tests | PASS: 13 passed | [Log](logs/cobalt-handoff-tests.stdout) |
| live-replay-supply | PASS: 1 passed | [Log](logs/live-replay-supply.stdout) |
| warm-latency | DEFERRED (5-minute budget, still compiling); rerun with a longer budget: PASS: 1 passed | [Log](logs/warm-latency.stdout), [rerun](logs/warm-latency-rerun.stdout) |
| Full workspace test suite (background, local) | PENDING: still running at packet time (started 06:06Z) | [Log](logs/full-workspace-tests.stdout), [receipt](receipts/full-workspace-tests.json) |
| mkdocs build --strict | PASS | [Log](logs/strict-docs.stdout) |
| public-doc-links | PASS | [Log](logs/public-doc-links.stdout) |
| public-secret-scan | PASS | [Log](logs/public-secret-scan.stdout) |

| Validator copy | Original, 1020 | Saved V2, 1021 | Fresh V2, 1021 | Rollback checkpoint (`d66cecc3…`) |
|---|---|---|---|---|
| validator-0 | PASS | PASS | PASS | PASS |
| validator-1 | PASS | PASS | PASS | PASS |
| validator-2 | PASS | PASS | PASS | PASS |
| validator-3 | PASS | PASS | PASS | PASS |
| validator-4 | PASS | PASS | PASS | PASS |
| validator-5 | PASS | PASS | PASS | PASS |

Per-node verifier stdout and stderr are in `history/`. Commands, timings, memory limits and
exit codes are in `receipts/`. See also [qualification.json](qualification.json) and
[the exact commands](verification-commands.md).

## Block 1011

The new build replays the full archived history through block 1011 and on to the certified
tips: 1020 for originals and 1021 for both V2 sets. Original validator-0 reports
`verified: true`, `block_count: 1020`, tip `9d02b8eecb78408e8f1de12ae1e2607ad4987c2c8d883f1718593df7c2d9ca529f0707bd581e3e414361f202b1768feb`
([report](history/original-validator-0.stdout.json)). The six originals, restored rollback validator-0,
all twelve V2 copies and the height-1050 canary backup replay past 1011 with no error.

## Current-chain replay

Fresh signed validator-1 canary backup, taken with `scripts/postfiat-safe-rollout backup` only:
PASS: signed backup at height 1050, tip `03a24230…`, root `13d9e652…`. New build: finalized-checkpoint verification PASS; full-history `verify-state` `verified: true`, `block_count: 1050`, tip `03a24230…`, root `13d9e652392be49f…` (197.1 s). A copy with a changed signature was rejected.

- Rollout state for release `combined-fastpay-20260928` is prepared, not applied (`applied: []`):
  `~/.postfiat/deployments/combined-fastpay-20260928/` (state SHA-256 `4d3a7586…`, stage binary `1f8b332d…`,
  signed manifest `d2fdb687…`, publisher key and snapshot keys by path).
  Preflight: fleet at height 1050, six-way agreement, six signer rosters valid, 0 deletions, order 1, 0, 2, 3, 4, 5.
  The stage matches the September 25 stage byte for byte after the release-ID change, except the executable and the manifest
  ([compare](canary-backup/stage-compare.json)). [Summary](canary-backup/rollout-state.summary.json), [commands](canary-backup/prepare_rollout.sh).
- Local backup: `~/.postfiat/deployments/combined-fastpay-20260928/evidence/pre-rollout-backup/` (`backup-signed`, manifest `a40d6a99…`).
- Fleet writes: validator-1 only, by the backup step: the unsigned export
  `/var/lib/postfiat/pre-rollout-snapshots/combined-fastpay-20260928-validator-1-finalized-checkpoint`
  (written by the running executable) and a copy of the new executable beside it. No apply, no restart, no transaction.
- The height covers the six faucet-grant blocks 1045–1050 produced by the deployed release.

## Fix behaviour

`fastpay_non_signer_view_zero_proposer_anchors_held_effect`
(`crates/node/src/tests/fastpay_non_signer_anchor.rs`): a FastPay payment, then validator-5 (registered,
not an eligible signer) proposes at view 0; all six vote, the block certifies at view 0 with the effect
anchored, and all six have the same tip, state root and ledger. Result: PASS: 1 passed.
The FastPay committee suite now includes the fix's invariant tests in `fastpay_payment_safety`
(forged, duplicate and wrong-domain votes; non-signer never signs; idempotent re-apply; restart).

## Rotation and rollback

The governance gate ran the unchanged `deployments/release-repair-20260916/run_local_governance_gate.py`
on disposable copies with isolated local signers and a six-peer loopback topology: both startup orders,
one certified rotation accepted on every node, convergence and a restart.
Start orders: validator-0 transport-first, validator-1 rpc-first, validator-2 transport-first, validator-3 rpc-first, validator-4 transport-first, validator-5 rpc-first.
Fresh certified tip: `35ab6fbc3546f1e1bf387d10e68d1e314c9ed0a90ec4940e5f41c0fcc79759456fc1f5d8718fbd734a41b779b876f535`, root `b01a98e539f8b101d10c22cf78efe6d205cdf291a44b47fbbed05cb315ad7518651b59959d3c38af8a71713030c63091`, height 1021.

The rollback executable is the deployed `d66cecc36426ce05ced8730b2439a27285c6b404688acd13dc23594b884eabd6`,
copied from `~/.local/lib/postfiat/releases/combined-fastpay-20260925/` after its hash was checked. On six
restored originals it ran checkpoint verification and a service start and restart; the new build then
fully replayed restored validator-0. This is pre-activation rollback only.

## Full workspace suite

`cargo test --workspace --locked -j 2 --no-fail-fast` in `source-1` (`CARGO_TARGET_DIR=target-1`), started in the
background after both builds: still running at packet time (started 06:06:04Z); the partial log is [logs/full-workspace-tests.stdout](logs/full-workspace-tests.stdout).

## CI

`gh run list --branch release/combined-fastpay-20260928` returns no runs ([observation](ci-observation.json)).
`rust-ci`, `docs-build` and `product-security-ci` run only on pushes to `main` and on pull requests.

## Notes

- Task Node: task `task_dcd3f64f4332d1935607847ea501cede` (request `req_6b28e544…`) was generated by Task Node, inspected and accepted. Evidence is submitted after the final push.
- Disk: 3.4 GB was free at the start. The September 25 disposable copies, build trees and targets under
  `~/.cache/release-repair-20260925/` were removed (worktrees removed, targets with `cargo clean`); `canary-backup-1036`,
  its binaries and all receipts were kept. At 06:11Z the background suite's debug build brought free space down to 1.9 GB.
  The disk guard ([log](logs/disk-guard.log)) then looped on a failed `cargo clean` of `target-2`; it was stopped, the
  verified saved-V2 copies validator-0, validator-1 and validator-2 were deleted by hand, and the fixed guard deleted this
  run's `target-2` (build 2 already hashed) and the verified copy validator-3. Saved-V2 validator-4 and validator-5 are kept.
  The deleted copies can be recreated from `~/.cache/release-repair-20260916/working`. The guard was stopped before the final push.
- The first build and copy drivers were killed when their tool session ended. The build-1 Cargo process kept
  running and finished; build 1 was then rerun with the identical command in the same tree and target (it recompiled
  only `postfiat-node`, because `crates/node/build.rs` watches `.git/HEAD`). The partial copy of `working/validator-1`
  was deleted and redone ([interrupted logs](logs/interrupted-build-driver-first.log)).
- Limits: one foreground Cargo process at a time (the full suite ran beside it in the background, as instructed),
  `CARGO_BUILD_JOBS=2`, two test threads, at most two replays at once, a 20 GiB address-space limit and a disk-backed `TMPDIR`.
  Disposable copies stay under `/home/postfiatchad/.cache/release-repair-20260928`. The protected release checkout was not accessed.
- Checkpoint push: `94a48304` at 06:46Z (63 minutes), with everything above complete except warm-latency and the full suite. The final commit supersedes it.
- Driver scripts are in [`tools/`](tools/); the canary scripts are in [`canary-backup/`](canary-backup/).
- `SHA256SUMS` covers every packet file except itself.
