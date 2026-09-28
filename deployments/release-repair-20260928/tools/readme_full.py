from runner import *
import runpy
FINAL = len(sys.argv) > 1 and sys.argv[1] == 'final'
PACKET = REPO/'deployments/release-repair-20260928'
g = runpy.run_path(str(ROOT/'tools/readme.py'), run_name='readme')
def read(p, d=None):
    p = ROOT/p
    return json.loads(p.read_text()) if p.exists() else d
def rep(n): return read(f'reports/{n}.json', {})
b = read('node-builds.json', {}); hashes = [x.get('binary_sha256', 'pending') for x in b.get('builds', [])] + ['pending']*2
o0 = rep('original-validator-0').get('observed', {})
v2 = read('v2-service-receipt.json', {})
fin = v2.get('finality_statuses', [{}])[0] if v2.get('finality_statuses') else {}
c = read('canary-backup/result.json', {}); co = c.get('observed', {}); rb = c.get('rollout_backup', {})
rs = read('canary-backup/rollout-state.summary.json', {})
fix = rep('fix-reproduce-first')
fs = rep('full-workspace-tests')
task = read('task-node.json', {})
guard = (ROOT/'logs/disk-guard.log').read_text() if (ROOT/'logs/disk-guard.log').exists() else ''
deleted = sorted(set(re.findall(r'post-v2/validator-(\d)', guard))) if (re := __import__('re')) else []
status_line = '**Final.' if FINAL else '**Checkpoint (75 minutes); a final push follows.'
status_line += ' Nothing was deployed. No source was repaired.**'
if FINAL:
    import re as _re
    _t = (ROOT/'logs/full-workspace-tests.stdout').read_text(errors='replace')
    _groups = len(_re.findall(r'^test result: ', _t, _re.M)); _fail = len(_re.findall(r'^test \S+ \.\.\. FAILED$', _t, _re.M))
    _done = len(_re.findall(r'^test \S+ \.\.\. (?:ok|ignored)', _t, _re.M))
    status_line += ('\nEvery check that ran locally passed. The full workspace test suite was still running when the time box ended and is recorded as '
                    f'**PENDING**: {_groups} test-result groups had finished, {_done} tests had passed or been skipped as ignored, {_fail} had failed '
                    '(log: `logs/full-workspace-tests.stdout`, partial). warm-latency timed out in its first 5-minute budget while compiling and passed on a rerun.')
canary_text = 'PENDING'
if c:
    canary_text = (f"{c.get('result')}: signed backup at height {rb.get('height')}, tip `{str(rb.get('tip'))[:8]}…`, root `{str(rb.get('state_root'))[:8]}…`. "
                   f"New build: finalized-checkpoint verification {'PASS' if co.get('checkpoint_verified') else 'FAIL'}; full-history `verify-state` "
                   f"`verified: {str(co.get('replay_verified')).lower()}`, `block_count: {co.get('replay_block_count')}`, tip `{str(co.get('replay_tip'))[:8]}…`, root `{str(co.get('replay_root'))[:16]}…`"
                   f" ({c.get('steps', {}).get('verify-state-signed', {}).get('elapsed_seconds')} s). A copy with a changed signature was rejected.")
fs_text = 'PENDING'
if fs.get('status') == 'RUNNING': fs_text = f"still running at packet time (started {fs.get('started_at','')[11:19]}Z); the partial log is [logs/full-workspace-tests.stdout](logs/full-workspace-tests.stdout)"
elif fs: fs_text = f"{fs.get('status')} ({fs.get('started_at','')[11:16]}Z–{fs.get('completed_at','')[11:16]}Z): {fs.get('groups')} test-result groups, {fs.get('tests_passed')} passed, {fs.get('tests_failed')} failed, {fs.get('tests_ignored')} ignored" + (f"; failed: {', '.join(fs.get('failed_tests', []))}" if fs.get('failed_tests') else '')
text = f"""# FastPay effect-anchoring release tip qualification, September 28, 2026

{status_line}

Source tip: `c93b213755f5889565fd1f77b9e45c149a07193a` (`c93b2137`) on `release/combined-fastpay-20260928`.
It is the deployed code `f60e9639` (executable `d66cecc3…`) plus the FastPay effect-anchoring fix; see
[the design record](../../docs/status/fastpay-effect-anchoring-fix-20260928.md).
The evidence commit that follows adds only this packet.

Executable SHA-256, build 1: `{hashes[0]}`.
Executable SHA-256, build 2: `{hashes[1]}`.
Reproducibility: **{b.get('result', 'PENDING')}**. `cmp` compared the two executables byte for byte.
Each build came from its own clean worktree and its own copy of the September 22 release cache
(not empty-cache builds). Both used the GCC linker (`/usr/bin/gcc`, GCC in `.comment`, no Zig), the same
remap arguments and `SOURCE_DATE_EPOCH=1789514690`. Neither has RPATH or RUNPATH.

{(ROOT/'readme-table.md').read_text()}
Per-node verifier stdout and stderr are in `history/`. Commands, timings, memory limits and
exit codes are in `receipts/`. See also [qualification.json](qualification.json) and
[the exact commands](verification-commands.md).

## Block 1011

The new build replays the full archived history through block 1011 and on to the certified
tips: 1020 for originals and 1021 for both V2 sets. Original validator-0 reports
`verified: true`, `block_count: {o0.get('block_height', 'pending')}`, tip `{o0.get('block_tip_hash', 'pending')}`
([report](history/original-validator-0.stdout.json)). The six originals, restored rollback validator-0,
all twelve V2 copies and the height-1050 canary backup replay past 1011 with no error.

## Current-chain replay

Fresh signed validator-1 canary backup, taken with `scripts/postfiat-safe-rollout backup` only:
{canary_text}

- Rollout state for release `combined-fastpay-20260928` is prepared, not applied (`applied: []`):
  `~/.postfiat/deployments/combined-fastpay-20260928/` (state SHA-256 `{str(rs.get('rollout_state_sha256'))[:8]}…`, stage binary `{str(rs.get('stage_binary_sha256'))[:8]}…`,
  signed manifest `{str(rs.get('signed_manifest_sha256'))[:8]}…`, publisher key and snapshot keys by path).
  Preflight: fleet at height {rs.get('preflight', {}).get('fleet_height')}, six-way agreement, six signer rosters valid, 0 deletions, order 1, 0, 2, 3, 4, 5.
  The stage matches the September 25 stage byte for byte after the release-ID change, except the executable and the manifest
  ([compare](canary-backup/stage-compare.json)). [Summary](canary-backup/rollout-state.summary.json), [commands](canary-backup/prepare_rollout.sh).
- Local backup: `~/.postfiat/deployments/combined-fastpay-20260928/evidence/pre-rollout-backup/` (`backup-signed`, manifest `{str(rb.get('signed_manifest_sha256'))[:8]}…`).
- Fleet writes: validator-1 only, by the backup step: the unsigned export
  `/var/lib/postfiat/pre-rollout-snapshots/combined-fastpay-20260928-validator-1-finalized-checkpoint`
  (written by the running executable) and a copy of the new executable beside it. No apply, no restart, no transaction.
- The height covers the six faucet-grant blocks 1045–1050 produced by the deployed release.

## Fix behaviour

`fastpay_non_signer_view_zero_proposer_anchors_held_effect`
(`crates/node/src/tests/fastpay_non_signer_anchor.rs`): a FastPay payment, then validator-5 (registered,
not an eligible signer) proposes at view 0; all six vote, the block certifies at view 0 with the effect
anchored, and all six have the same tip, state root and ledger. Result: {g['sws']('fix-reproduce-first')}.
The FastPay committee suite now includes the fix's invariant tests in `fastpay_payment_safety`
(forged, duplicate and wrong-domain votes; non-signer never signs; idempotent re-apply; restart).

## Rotation and rollback

The governance gate ran the unchanged `deployments/release-repair-20260916/run_local_governance_gate.py`
on disposable copies with isolated local signers and a six-peer loopback topology: both startup orders,
one certified rotation accepted on every node, convergence and a restart.
""" + (f"""Start orders: {', '.join(f"{k} {v}" for k, v in (v2.get('start_orders') or {{}}).items()) or 'see receipt'}.
Fresh certified tip: `{fin.get('block_tip_hash')}`, root `{fin.get('state_root')}`, height {fin.get('block_height')}.
""" if fin else "Result pending.\n") + f"""
The rollback executable is the deployed `d66cecc36426ce05ced8730b2439a27285c6b404688acd13dc23594b884eabd6`,
copied from `~/.local/lib/postfiat/releases/combined-fastpay-20260925/` after its hash was checked. On six
restored originals it ran checkpoint verification and a service start and restart; the new build then
fully replayed restored validator-0. This is pre-activation rollback only.

## Full workspace suite

`cargo test --workspace --locked -j 2 --no-fail-fast` in `source-1` (`CARGO_TARGET_DIR=target-1`), started in the
background after both builds: {fs_text}.

## CI

`gh run list --branch release/combined-fastpay-20260928` returns no runs ([observation](ci-observation.json)).
`rust-ci`, `docs-build` and `product-security-ci` run only on pushes to `main` and on pull requests.

## Notes

- Task Node: task `{task.get('task_id', 'pending')}` (request `{str(task.get('request_id', ''))[:12]}…`) was generated by Task Node, inspected and accepted. Evidence is submitted after the final push.
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
"""
(PACKET/'README.md').write_text(text)
print('README written', len(text))
