# Local qualification — signer-rotation-20261007, 2026-10-06

**Local checks only.** Nothing ran on a validator host, no live RPC was called,
no transaction was sent and nothing was deployed. Source tip
`0fa55d0b650731d8617d62284946c73f72641cb7` on `release/signer-rotation-20261007`.
Rollback executable: the deployed `combined-fastpay-20260928`
(`1f8b332d…`, copied from `~/.local/lib/postfiat/releases/combined-fastpay-20260928/` after its hash was checked).

Not done today: canary backup, fleet before-state, rollout, store conversion, activation.

## Results

| Check | Result | Evidence |
|---|---|---|
| CI on the tip (`gh run list --branch main`, 11:13Z and 11:31Z) | `docs-build` success; `rust-ci` and `product-security-ci` in progress; no failed workflow on `0fa55d0b`. The release branch has no runs (workflows run on `main` and pull requests). An earlier `product-security-ci` failure on `cf65b81e` (wallet dependencies job) predates the tip's wallet lock-file update. | [ci-main.json](ci-main.json), [ci-release.json](ci-release.json) |
| Two clean builds, separate worktrees and copied caches | PASS: both `decaa411376a125fb377a29037b6dd470afb2208a268d30a3ce8130f571b370f`, `cmp` identical, 62,692,328 bytes, GCC linker, no RPATH/RUNPATH, trees clean after build | [node-builds.json](../node-builds.json) |
| Canary backup 1050 (signed, validator-1, 2026-09-28): signed import, new build | PASS; a copy with a changed signature is rejected (exit 1) | [history-run.json](history-run.json) |
| Canary 1050, checkpoint verification, new build | PASS: 1050, tip `03a24230…`, root `13d9e652…` = recorded backup identity | same |
| Canary 1050, full-history replay, new build | PASS: `verified: true`, 1050 blocks, tip `03a24230…`, root `13d9e652…` = recorded | same |
| Six original copies, full-history replay through block 1011, new build | PASS ×6: 1020, tip `9d02b8ee…`, root `587c6526…` = recorded (2026-09-16 receipt) | same |
| Two saved V2 copies (validator-4, -5), full-history replay, new build | PASS ×2: 1021, tip `5323a2a5…`, root `d19264ca…` = recorded | same |
| Governed rotation on six disposable copies, new build | PASS: both start orders, rotation accepted on all six at 1021, convergence and restart (first attempt failed on a port held by this run's own test binary; rerun after the tests) | [receipt](v2-service-receipt.json), [log](logs/governance-gate.stdout) |
| Fresh V2 copies, full-history replay, new build | PASS ×6: 1021, tip `11427e60…`, root `fda2546f…` = the rotation receipt | [history-run.json](history-run.json) |
| Rollback: `combined-fastpay-20260928` on data written by the new build | PASS: checkpoint ×6 and full replay of validator-0 at 1021, tip `11427e60…`, root `fda2546f…`; the signed 1050 canary import (checkpoint and full replay, root `13d9e652…`); `rollback-one.sh` checks (checkpoint, identity) on all six. `validate-local-keys` not run: the archived copies have no faucet key file | same, [rollback core](logs/rollback-core.log) |
| `deployment_manifest_verified` from the verified record (`1bb15a78`) | PASS: `false` without the variable and without the record, `true` after `deployment-manifest-verify` wrote it, `false` for a record with a changed manifest hash | [log](logs/verified-record.log) |
| FastSwap store conversion on a copy of validator-5's July store (`d9c42a79`) | PASS: dry run `would-convert` 26/26 legacy records; convert `converted`, backup 33 files verified, normal open verified 26 records; second run `nothing-to-convert`; restored backup is legacy again | [store-migrate/](store-migrate/) |
| Stage, signed manifest, local preflight with signed gate | PASS: 33 generated files, four circuit artifacts, `deployment-manifest-verify` for all six (`PASS_SIGNED_LOCAL_INPUTS_ONLY`) | [local-preflight-signed.json](local-preflight-signed.json) |
| Generated units vs `combined-fastpay-20260928` | Only `--max-requests 100000`, `RestartSec=1` (six RPC units) and the `POSTFIAT_DEPLOYMENT_VERIFIED_RECORD` line (12 environment files) | [diff](logs/stage-vs-20260928.diff) |
| `systemd-analyze verify` (systemd 259) on the 12 units | PASS: no finding for any unit (8 unrelated lines about dangling dracut links in the copied host unit directory) | [log](logs/systemd-analyze-verify.log) |
| Focused suites for the changes after the 2026-10-05 suite | PASS: storage legacy migration 8, FastPay epoch boundary 12, FastSwap control signing 6, `account_tx` 10, Cobalt shadow 18, node FastPay 30, store-migrate CLI 1, JSON-storage acknowledgement 1, Python `account_tx` fallback 5 (first attempt lacked `PYTHONPATH=python`, as CI sets it) | [focused-suites.json](focused-suites.json) |
| The 2026-09-28 release suites | PASS: fix reproduce-first 1, view recovery 4, timeout votes 1, FastPay committee 22, fastpay-types 9, fastpay-execution 12, cobalt handoff 13, live replay supply 1; bridge policy update: types 1, execution 7 | [release-suites.json](release-suites.json) |
| Signer-rotation dry-run tests | PASS: execution 1, node 1 (six-validator fixtures) | [activation-suites.json](activation-suites.json) |
| Full workspace suite | Not rerun. It ran at `672b707c` on 2026-10-05 (`~/.cache/suite-20261005/cargo-test.log`, 84 groups). One failure, `long_running_validator_service_requires_explicit_json_storage_acknowledgement`, was a stale mode-664 `.integrity.key` in that worktree; that test passes here | same log |
| Gates on the release branch (packet staged) | PASS: `cargo fmt --all -- --check`, `scripts/test-proof-public-input-inventory` (7 systems, 150 public fields), `mkdocs build --strict`, `scripts/public-doc-links` (514 files), `scripts/public-secret-scan` (tracked tree) | `logs/release-*.log` |

## Method

The 2026-09-28 method ([packet](../../release-repair-20260928/README.md)) with these differences:

- Builds ran in parallel with `CARGO_BUILD_JOBS=6` (2 before); scheduling only. Same command, `SOURCE_DATE_EPOCH=1789514690`, `/usr/bin/gcc` linker and remap scheme with this run's directories. Caches: separate copies of the 2026-09-28 release-profile cache.
- History checks ran up to six at a time; each replay takes about 3.3 minutes.
- The canary is the signed 2026-09-28 backup (height 1050), the newest signed archive on this server. Today's fleet is past 1115; tomorrow's fresh backup closes that gap.
- Focused suites ran in the default test profile of the main checkout (2026-09-28: opt-level 2 test target).
- `rollback-one.sh` needs a host. Its checks (checkpoint, identity, local keys with the 2026-09-28 executable) ran on the six rotated copies; its unit hashes match the local 2026-09-28 stage; `bash -n` passes.

Drivers are in [`tools/`](tools/); per-command records are in `reports/` and `logs/`.
Disposable copies stay under `~/.cache/release-signer-rotation-20261007`.
`SHA256SUMS` covers every packet file except itself.

## Task Node

Task `task_0d3f8a1305cf45f387e22af5c3cfb16e` (request `req_3f5f2fae…`), generated by Task Node, inspected and accepted. Evidence is submitted after the push.
