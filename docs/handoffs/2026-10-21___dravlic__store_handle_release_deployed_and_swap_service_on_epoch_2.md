# Store handle release deployed and swap service on epoch 2

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-21 UTC
- **Responding to:** the other lane's [2026-10-20 handoff][nazgul]. My previous
  handoff: [2026-10-20][previous].

## BLUF

The next validator release, `store-handle-20261021`, was cut from main
`86706699`, qualified locally and installed on all six validators today (grant
blocks 1132–1137, after state 1137 / `18a4dc86…` / `1277c76c…`). It carries the
STO-07 store-handle fix (every batch the new executable accepted reports
`database_opens=0`), `fastswap-committee-migrate` and this week's reviewed
merges. The FastSwap committee migration then ran per host: the swap service of
all six validators now opens at committee epoch 2 (root `72836827…`,
`enabled: true`), validator-5 included. Its store had never applied the epoch-1
fence or the anchor, but its replayed state equalled the anchored drained
state, so the migration subsumed them. Each host's two units were stopped and
started once between 12:07 and 12:27Z: no block, no rollback. The storage G3
evidence moved: the release manifests of both height-924 copies verify (no
signed manifest covers the validator data), and the height-1123 replacement
archive is hashed and replays exactly through the evidence harness, which gained
a signed-archive mode. The issuer signing sheet is updated for the new state;
both issuer updates still wait for the other lane. Records: [Current State][state],
[deploy sheet][sheet7], [next release plan][next], [storage G3][g3].

## Current state

- **Fleet.** Live probe: my read-only RPC reads through all six hosts at
  12:50:58Z. Six on `store-handle-20261021` at 1137, tip `18a4dc86…`, root
  `1277c76c…`; `fastswap_capabilities` epoch 2, `72836827…`, enabled true on
  all six; A666 `57da3837…` and BMNRC `b2817e68…` unchanged, 0 claims,
  0 returns, not paused.
- **Deployment boundary.**
  - Deployed: source `86706699`, executable `eea96ba6…`.
  - Release branch `release/store-handle-20261021` is at `6692edf2`; `main`
    was at `f00ea237` before this handoff.
  - Merged but undeployed: nothing in `crates/` since the cut; on main only
    records and the replay harness (`2ebc7b13`).
- **Release `store-handle-20261021`** (cut `41cf2dde`, [qualification
  packet][qual], main record `55edef74`).
  - Source `86706699`; since `8bed9b90` only `crates/node` and
    `crates/storage` changed (26 files).
  - CI green on the cut commit: `docs-build` 39433228893, `rust-ci`
    39433228794 (its `test` job is `cargo test --workspace --locked`),
    `product-security-ci` 39433228932.
  - Two identical clean builds: executable
    `eea96ba6761ed223047d7781663100d34efe5641d36031bd50874bd9c8b41f36`.
    Signed manifest `8ce1da30…`, publisher `pfc531e0…`.
  - History: the 1123, 1115 and 1050 canaries and the six 2026-09-28 copies.
    The six 1020 originals went with the cache deletions; the 09-28 copies
    replaced them, and the governed rotation was not rerun.
  - The rollback build `fastlane-cap-20261014` (`b1b3dbb1…`) reads the new
    build's data. Units are byte-identical apart from the release id.
  - The migration command: its 15 tests, plus dry and real runs on scratch
    stores.
  - Task Node `task_fbead19768bb3fac38e418e864dbf5e0`: Rewarded, 2.5 PFT.
- **Release day** ([rollout record][rollout], chain-state record `e4577cef`).
  - Before state (`f6f3fc10`, [checks][before]): six on `fastlane-cap-20261014`
    at 1131 / `9b054f09…` / `a12e7c5f…`; both routes authority epoch 1, hashes
    `57da3837…` / `b2817e68…`.
  - Signed canary backup of validator-1 (`a7c03be0`, [record][canary]): manifest
    `df9b3847c2229b23e9c97627b9cf14447de6aab1f5d4cafa894f8eca4a108ef1`.
    Re-import, `verify-finalized-checkpoint` and the full `verify-state`
    replay all verified at 1131.
  - Rollout (`df673d84`): applies 11:15:17–11:38:16Z in the order 1, 0, 2, 3,
    4, 5. Grants at 1132–1137, proposers validator-4, 5, 0, 1, 2, 3, each
    certified at view 0 identically on all six. No divergence, no rollback.
    Moved: 6 PFT of grants plus 192 atoms of fees.
  - After checks (`9ed11203`, [record][after]): `RELEASE-ID.txt`
    `status=DEPLOYED`, `deployed_height=1137`; 12 processes on `eea96ba6…`;
    `deployment_manifest_verified` true and build `86706699` on all six; RPC
    units `--max-requests 100000`, `RestartSec=1`; `demo-preflight.py` READY,
    60 PASS / 0 ATTENTION / 0 FAIL; 16–27 GB free per host.
  - Task Node `task_9feafaf2e4867e4a745f4590dc7634fe`: Rewarded, 4 PFT.
- **FastSwap committee migration** (release `6692edf2`, main `f00ea237`;
  [sheet §7][sheet7], [per-host reports][reports]).
  - Order validator-5, 0, 1, 2, 3, 4, 12:07:44–12:27:08Z. Per host: both units
    stopped, dry run `would-migrate`, real run `migrated` with
    `service open: committee epoch 2, root 72836827…, enabled true`, units
    started (0 restarts, back at 1137 at the first poll, 11–18 s).
  - After each host: `fastswap_capabilities` epoch 2, enabled true;
    `fastswap_checkpoint_status` answers; six-way agreement before and after
    every host at 1137 / `18a4dc86…` / `1277c76c…`. Afterwards
    ([after-migration][aftermig], [demo preflight][demomig]): READY, 60 / 0 / 0.
  - Before the run: validators 0–4 reported epoch 1 with `enabled: false`, and
    validator-5 `fastswap_unavailable`.
  - validator-5's note: its base+WAL store (26 records, 0 fence and 0 anchor
    records) never applied the epoch-1 fence or the anchored drain checkpoint
    `355fe608…`; its replayed state equals the anchored drained state, so the
    migration subsumes them.
  - On every host: the pre-migration copy at
    `/var/lib/postfiat/fastswap-v1-epoch2-backup-validator-N`, and the two input
    files at `/var/lib/postfiat/fastswap-migration-20261021`.
  - The routes' `authority_epoch` is still 1, so Ethereum checkpoint signing
    is unchanged until the issuer updates land.
  - Task Node `task_f6bd15bc691ab411c9c1f65372765aa7`: Rewarded, 4 PFT. The
    first request failed inside Task Node's generator; a fresh request worked.
- **Storage G3 / testnet path A1–A3** (main `a17a1e50`, `40f9e66e`,
  `2ebc7b13`, `0db9a810`; [G3][g3], [testnet path][testnet]).
  - Height 924: the two copies (`~/.postfiat/deployments/storage-rollout-d0ae79f3`
    and `storage-rollout-10dd9f20`) each carry one signed manifest, the release
    manifest under `stage/rootfs/etc/postfiat/releases/…` (`55f4822d…` and
    `97c6518e…`, publisher `pfba2ba9…`). Both verify with
    `deployment-manifest-verify`, all 28 covered files match, and a tampered
    copy fails.
  - **No signed manifest covers the validator data** (54 GB, not
    hash-checked). The box is ticked with that limit written. The publisher
    key `pfba2ba9…` is not pinned in the repository.
  - Height 1123: the replacement archive
    (`~/.postfiat/deployments/fastlane-cap-20261014/evidence/pre-rollout-backup/backup-signed/`,
    manifest `d957141e…`) verifies against the `cobalt-activation-8694b99d`
    snapshot publisher key. Tree hash (`tree_sha256`)
    `724389ad583b36aa979b1497a8377babd724fa389686a2ee41765441f0934ee0`.
  - It replays exactly to 1123 / `bafcc6ef…` / `942d1fc2…` with the
    `eea96ba6…` binary through the new signed-archive mode of
    `benchmarks/storage-scaling/run_replay_evidence.py` (`--signed-archive-dir`;
    the 915/924 mode is unchanged). Six fail-first tests in
    `python/tests/test_storage_scaling_replay_evidence.py`. Receipt
    `~/.cache/g3-1123-replay-20261021/receipts/height-1123-harness/receipts/height-1123.json`,
    sha256 `c172d31e…`.
  - G3's 1123 box is ticked; A3 reads "1123 half done". The 924 half waits for
    a replay with the deployed STO-07 release, which is now possible.
  - Task Node `task_02b89fd890947d86c44964b7d5071924`: Rewarded, 3.5 PFT.
  - Pre-existing and untouched: `benchmarks/storage-scaling/SHA256SUMS.txt`
    carries a wrong `README.md` hash.
- **Issuer signing sheet** ([sheet][issuer], release/fastlane-cap-20261014
  `61e9b00c`).
  - It reads every height at the pre-check: current H, A666 at H+1, BMNRC at
    H+2. Today that is 1138 expected on validator-4 and 1139 on validator-5 by
    the observed rotation, confirmed with `block-proposer` before each
    submission.
  - It names the running release's executable for signing and for the proposer
    read, and keeps the activation-receipt check by RPC and the two file
    hashes (A666 `24aa2e28…`, BMNRC `5179d6f7…`).
  - Both routes unchanged at authority epoch 1; not submitted.
- **StakeHub** ([rehearsal plan][rehearsal], master `d8dd2c5`, linked from the
  readiness doc's open items).
  - The first rehearsal under custody rule (b), with FW-13: `pft
    fastpay-navswap` (`fastswap.py`), pfUSDC → a651, 100,000 atoms, on
    `postfiat-wan-devnet-2` against the venue inventory wallet.
  - A fresh single-use key: at most 1.00 pfUSDC and 1 PFT, its own owner-only
    passphrase file, never the venue wallet.
  - Step 3a, without the operator file, must be refused before any reservation
    or deposit; 3b, with the file, completes. Every key stays local, so rule
    (a) holds as well. 1.5–3 h once the preconditions hold.
  - **Finding.** On the repository's own terms the run moves mainnet-backed
    pfUSDC (real money, in dust amounts), while the custody proposal's option
    (b) assumes a chain without mainnet-backed assets. The run is therefore
    governed by custody rule (a) (decision of 2026-10-21, StakeHub `844d4b2`)
    and happens on the founder's machine in a shift of his.
  - Preconditions and owners (plan §6):
    - ours: the wallet's FastSwap activation file must match today's epoch-2
      committee (preflight check 0c reads it without sending; a stale file
      would leave two deposit objects behind); the binaries
      `fastswap_wallet_payload`, `postfiat-rpc-sdk` and `fastswap_live_driver`;
      the wallet proxy with its bridge relay, and the warm prover;
    - yours: the machine with the operator's `~/.pft` (venue inventory funds
      and the operator passphrase file), the six SSH tunnels to the validator
      RPCs, at most 1 USDC plus gas at the key's Ethereum address, and the go
      for the day.
- **Devnet.** Touched by the release (six validator and RPC units restarted
  one at a time; six grant blocks) and by the migration (both units of each
  validator stopped and started once, no block); evidence in the packet.
  Nothing else moved.
- **Task Node.** The four tasks above, 14 PFT (2.5 + 4 + 3.5 + 4). This handoff
  has no Task Node action.
- **Work server.** 164 GB free at 12:51Z. The release build trees are deleted;
  the binaries and the 1123 import stay under
  `~/.cache/release-store-handle-20261021/`.

## Next decision or action

### My next steps, in order

1. Once the two issuer updates are in: the next Ethereum checkpoint, 5 of 6,
   with validator-5.
2. The height-924 exact replay (G3's second half) with the deployed STO-07
   release on a scratch copy, then A4's packet.
3. StakeHub: the first testnet rehearsal per the [plan][rehearsal], once our
   preconditions are prepared and the founder has run it in a shift of his.
4. New bot pull requests, and [#95][pr95]/[#103][pr103] as their authors
   answer.
5. [PR #49][pr49] conditions 1–3 myself from 2026-10-22 (re-pin, the two red
   jobs, the re-review), unless its handoff says that work has started on its
   side.

### Only the other lane can provide

I ask the other lane for the following; each shows the date first asked.

- **(g)** The two issuer signatures and submissions per the updated
  [sheet][issuer] (`61e9b00c`): A666 first, then BMNRC; the sheet reads the
  heights itself. It blocks the validator-5 checkpoint. 2026-09-25 /
  2026-10-01.
- **(f)** [PR #49][pr49]: only the registration, signed on its host, after
  conditions 1–3 are done on my side. 2026-09-24.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` secret, after its local fork-test run.
  2026-09-28.
- Its review of its unpublished work, the delayed-precommit RED fix first.
  2026-10-20.
- **New:** the first StakeHub rehearsal, on your machine in a shift of yours,
  when it suits you. It uses your venue inventory wallet, your operator
  passphrase file and about a dollar of real funds, with the steps of the
  [plan][rehearsal] (§4). Custody is decided (rule (a), see End of session); we
  prepare our preconditions first. 2026-10-21.

## References

- The other lane's [2026-10-20 handoff][nazgul]; my [2026-10-20 handoff][previous].
- Release branch `release/store-handle-20261021`: `41cf2dde`, `f6f3fc10`,
  `a7c03be0`, `df673d84`, `9ed11203`, `6692edf2` ([packet README][packet],
  [deploy sheet][sheet7], [qualification][qual]).
- Main: `55edef74`, `e4577cef`, `a17a1e50`, `40f9e66e`, `2ebc7b13`,
  `0db9a810`, `f00ea237`.
- Release branch `release/fastlane-cap-20261014` `61e9b00c`: [issuer signing sheet][issuer].
- [Next release plan][next]; [storage scaling milestone][milestone];
  [testnet path milestone][testnet]; [Current State][state].
- StakeHub master `d8dd2c5`: [testnet rehearsal plan][rehearsal].

[nazgul]: 2026-10-20___nazgul__founder_lane_resync_and_answers_to_open_asks.md
[previous]: 2026-10-20___dravlic__answers_acted_on_and_store_handle_fix_qualified.md
[state]: ../status/chain-state-current.md
[next]: ../plans/active/next-validator-release-plan-20261101.md
[milestone]: ../plans/completed/storage-scaling-milestone.md
[g3]: ../plans/completed/storage-scaling-milestone.md#g3-exact-replay
[testnet]: ../plans/active/l1v2-public-testnet-path-milestone.md
[packet]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/README.md
[qual]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/qualification/README.md
[sheet7]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/DEPLOY-SHEET.md#7-fastswap-committee-migration-one-host-at-a-time--covered-by-the-operators-go-of-the-day
[rollout]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/observed/rollout-record.json
[before]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/observed/before-checks.json
[canary]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/observed/canary-backup.json
[after]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/observed/after-checks.json
[reports]: https://github.com/postfiatorg/postfiatl1v2/tree/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/observed/committee-migration
[aftermig]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/observed/after-migration.json
[demomig]: https://github.com/postfiatorg/postfiatl1v2/blob/6692edf29a8615cd389c2d7a52eed24d26f36032/deployments/store-handle-20261021/observed/demo-preflight-after-migration.json
[issuer]: https://github.com/postfiatorg/postfiatl1v2/blob/61e9b00c8399907f45dff2be1ee44b8f1da431af/deployments/fastlane-cap-20261014/ISSUER-SIGNING-SHEET-20261020.md
[rehearsal]: https://github.com/postfiatorg/StakeHub/blob/d8dd2c5ef820e2c8de6ac78478f47f32bb1c4264/docs/review/testnet-rehearsal-plan-20261021.md
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr95]: https://github.com/postfiatorg/postfiatl1v2/pull/95
[pr103]: https://github.com/postfiatorg/postfiatl1v2/pull/103

## End of session (13:10 UTC)

- **Two new external advisories, fixed on main.**
  `product-security-ci` was red on every main commit from `a17a1e50` to
  `7d967180` for these two advisories only: its jobs `rust-supply-chain` and
  `wallet-and-proxy` failed on all eight, every other job passed (on `f00ea237`
  and `7d967180` `open-reserve-proof-kit` was still running at 13:06Z).
  `docs-build` was green on all eight; `rust-ci` was green on the first five and
  still running on `e4577cef`, `f00ea237` and `7d967180` at 13:06Z. The deployed
  release is unaffected; both fixes go into the next release.
  - `79d5f909`, `rust-supply-chain`: RUSTSEC-2026-0382 (rustls-webpki
    0.103.15 → 0.103.16) and RUSTSEC-2026-0381 (webpki-roots 1.0.9 → 1.0.10)
    in the root `Cargo.lock`. Version and checksum lines only, no edge changed;
    both checksums equal the crates.io index and the downloaded crates.
    `cargo check --workspace --locked` and `cargo fmt --all -- --check` pass.
    The five `tools/*` locks and the frozen `tools/nav-reserve-proof/fuzz` lock
    also carry affected versions; they are unchanged and outside this gate.
  - `56be18af`, `wallet-and-proxy`: launch-editor (GHSA-698v-4r3x-3vcv,
    GHSA-r825-w8mm-5pxw, GHSA-587h-7wmj-h5pm), bundled by vite 8.1.4.
    `npm audit fix` (no `--force`) moved vite to 8.3.5 with its build tree,
    a wider change than the 2026-10-06 one (vite 8.1.6 is the first fixed
    version). The 36 license lines npm dropped are restored; `package.json` is
    unchanged. Audit 0 vulnerabilities, `npm test` 260/260, the build passes;
    the browser test commands were not run (no browser here).
  - Recorded in the [next release plan][next].
- **Live state.** Not probed again: this part had no host or RPC contact. Last
  observed at 12:50:58Z: six at 1137, swap service on committee epoch 2 on all
  six, both routes still on authority epoch 1.
- **Rehearsal custody, decided (2026-10-21).** The first StakeHub rehearsal
  runs under custody rule (a): every key stays on the founder's machine and the
  validators receive only signed objects, which the [plan][rehearsal] already
  meets. The capped single-use key and the dust amounts stay as hygiene, not as
  the authority for the run. Rule (b) does not apply: the repository has no
  asset that is not backed by mainnet value, so there is no testnet rehearsal
  in the proposal's sense. The run uses your machine, your venue inventory
  wallet and operator passphrase file and about a dollar of real funds, so it
  happens on your machine in a shift of yours. We prepare our preconditions
  first: check 0c, the three binaries, the wallet proxy with its relay and the
  warm prover. Recorded in StakeHub `844d4b2`.
- **[PR #49][pr49], from 2026-10-22.** I take conditions 1–2 (re-pin
  `candidate-identity.json` past `340d5de1`/`d14c703e`; make
  `open-reserve-proof-kit` and `public-tree-hygiene` pass) and condition 3 (the
  re-review of the 2026-10-15 fix) myself, so only the registration signature
  on the founder's host stays with the other lane. If that work is already in
  progress on its side, I ask it to say so in its handoff.
