# Verification commands and scope

Started 2026-09-28T05:43Z with a 100-minute limit. The start commands were:

```sh
git fetch origin
git rev-parse origin/release/combined-fastpay-20260928   # c93b213755f5889565fd1f77b9e45c149a07193a
git worktree add --detach ~/.cache/qualify-20260928 origin/release/combined-fastpay-20260928
```

The qualified source is `c93b213755f5889565fd1f77b9e45c149a07193a`: the deployed
code `f60e9639` plus the FastPay effect-anchoring fix
([design](../../docs/status/fastpay-effect-anchoring-fix-20260928.md)). No pre-step and no source change.

## Limits

```sh
export CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 CARGO_TERM_COLOR=never
export TMPDIR=/home/postfiatchad/.cache/release-repair-20260928/tmp
export RUST_TEST_THREADS=2 RAYON_NUM_THREADS=2 OMP_NUM_THREADS=2 MALLOC_ARENA_MAX=2
ulimit -v 20971520
ulimit -c 0
```

Foreground Cargo commands ran one at a time; the runner waits while any other `cargo`
process exists. The one exception is the full workspace suite, which was started in the
background as instructed and ran beside the foreground gates in its own target directory.
A command stops if available memory drops below 4 GiB, and a replay needs 8 GiB free
before it starts. At most two replays ran at once (two workers). Verifier stdout goes straight to disk.

## Builds

Two clean detached worktrees at the source commit, built one at a time from separate
copies of the September 22 release caches (`~/.cache/qualify-fix-20260922/target-{1,2}`, the same origin as on September 25):

```sh
cargo build --release --locked -p postfiat-node --bin postfiat-node
```

Both builds used `SOURCE_DATE_EPOCH=1789514690`, the `/usr/bin/gcc` Rust linker, and the
September 25 remap scheme with this run's directories:

```text
--remap-path-prefix=<root>/source-1=/src/postfiatl1v2 --remap-path-prefix=<root>/source-2=/src/postfiatl1v2
--remap-path-prefix=<root>/target-1=/target --remap-path-prefix=<root>/target-2=/target
```

`<root>` is `/home/postfiatchad/.cache/release-repair-20260928`. `readelf -d` and
`readelf -p .comment` are logged for each executable, and `cmp` compares the two.

## History, rotation and rollback

Disposable copies were made with `cp -a`, then each database pointer was moved with
MAC-authenticated relocation (only `database_directory` changes):

- `working/`: originals from `~/.cache/combined-release-20260915/raw`, height 1020.
- `post-v2/`: saved September 16 V2 copies from `~/.cache/release-repair-20260916/working`, height 1021.
- `rollback/`: originals again.

```sh
candidate-1 verify-state --data-dir working/validator-N        # original, 1020 (through 1011)
candidate-1 verify-state --data-dir post-v2/validator-N        # saved V2, 1021
# governance-prepare + local governance gate rotate working/ to a fresh 1021
candidate-1 verify-state --data-dir working/validator-N        # fresh V2, 1021
rollback    verify-finalized-checkpoint --data-dir rollback/validator-N
# rollback services: deployed executable, six services, startup and restart
candidate-1 verify-state --data-dir rollback/validator-0
```

`rollback` is the deployed executable `d66cecc3…`, copied from
`~/.local/lib/postfiat/releases/combined-fastpay-20260925/postfiat-node` after its SHA-256 was
checked. The governance gate is the unchanged
`deployments/release-repair-20260916/run_local_governance_gate.py` with copied isolated
signers and the retained six-peer 127.0.0.1 topology. The rollback wrapper uses
`deployments/signing-fix-qualification-20260909/run_local_service_gate.py`.

## Rollout state and canary backup

[`prepare_rollout.sh`](canary-backup/prepare_rollout.sh) follows
`deployments/combined-fastpay-20260925/DEPLOY-SHEET.md` §2–5 for release
`combined-fastpay-20260928`: stage from the local r4/combined layout, sign the manifest
(publisher key by path), `postfiat-safe-rollout preflight`, then `postfiat-safe-rollout backup`
(snapshot keys by path). No `apply-next`, no restart, no transaction.
[`run_canary.py`](canary-backup/run_canary.py) then replays the signed backup with the new build:

```sh
candidate-1 snapshot-import-signed-finalized-checkpoint --data-dir signed-import --snapshot-dir backup-signed \
  --trusted-publisher-key-file snapshot-publisher.public.json --node-id validator-1
candidate-1 snapshot-import-signed-finalized-checkpoint ... --snapshot-dir tampered-signed   # must be rejected
candidate-1 verify-finalized-checkpoint --data-dir signed-import
candidate-1 status --data-dir signed-import
candidate-1 verify-state --data-dir signed-import
```

## Software

[software-gates.json](software-gates.json) records every command; each receipt under
`receipts/` has the full argument vector. Focused tests use the existing September 18 test
cache at opt-level 2 with debug assertions and overflow checks on. The fix test:

```sh
cargo test --locked -p postfiat-node --lib fastpay_non_signer_view_zero_proposer_anchors_held_effect -- --test-threads=2
```

The full workspace suite ran in `source-1` with `CARGO_TARGET_DIR=target-1`:

```sh
cargo test --workspace --locked -j 2 --no-fail-fast
```

## Publication

```sh
.venv-docs/bin/mkdocs build --strict
scripts/public-doc-links
scripts/public-secret-scan
```
