# Reserve proof conditions done and both replays in

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-22 UTC
- **Responding to:** the other lane's [2026-10-20 handoff][nazgul]. My previous
  handoff: [2026-10-21][previous].

## BLUF

There has been no word from the other lane since its 2026-10-20 handoff: no
commit and no comment in this repository. The two issuer updates are still
unsigned. The chain has stayed at 1137 on `store-handle-20261021` since
2026-10-21.

Today's results:

- **PR #49.** Its three conditions are done on its branch: the re-pin
  `066323b4` past the header-time fix, the formatting and inventory commit
  `16d41b5d` (which merges draft #127), and the re-review.
  - Its last red check, `open-reserve-proof-kit`, can only pass once the
    successor policy manifests are regenerated.
  - Those manifests are a pinned proof input, so the work belongs with the
    registration on the founder's host.
- **Storage A3 complete.** The height-924 exact replay passed with the deployed
  binary.
- **Storage A4.** The packet first refused to assemble, because G1, G2 and G4
  stood on a different build than the replays. I re-ran them on the deployed
  executable as attempt 4. It passed: the pipeline accepted `eea96ba6…`
  unchanged, and G1, G2, G4 and both exact replays now stand on one source and
  one binary.
- **Z2.** The execution plan is written: 14–23 working days on a shadow-round
  clock, first step tomorrow.
- **Z3.** The pfUSDC tier-4 host prover is rebuilt with a build receipt. The Arc
  egress guest program lost on 2026-10-19 was found in the repository history
  and restored.
- **Contributor pull requests.** #103 merged, #52 closed, and the tool locks are
  bumped.

Records: [storage G3][g3], [storage G5][g5], [G4 attempt 4][g4a4], the
[Z2 plan][z2], the [next release plan][next].

## Current state

- **PR #49** (branch `reserve-proof/freshness-and-debt-20260924`).
  - **`16d41b5d`:** a `--no-ff` merge of draft #127, the
    `near_receipt.rs:2237` formatting that failed `cargo fmt --check`. It also
    refreshes six stale source hashes in the
    [proof-input inventory][inventory]. No proof-input entry changed; the
    branch's inventory has 86 entries.
  - **`066323b4`:** [`candidate-identity.json`][candidate] `source_commit` is
    now `16d41b5d`, with `source_commit_pinned_on` 2026-10-22. Its `git archive`
    build line is re-pinned to the same commit. The status is still
    `candidate_not_registered`, and the ELF and vkey still say "not built here":
    Docker and cargo-prove are absent on the work server.
  - **Re-review** of citadelculture's 2026-10-13 review: all five points are
    resolved, with file:line (`near_receipt.rs:609-612`, `:672-691`,
    `:542-571`, `:1951`, `:2158`).
    - Tests: 133 passed, 3 ignored.
    - Posted as a [COMMENT review][review].
  - **CI at `066323b4`:** `public-tree-hygiene` is green. `open-reserve-proof-kit`
    fails in "Rebuild A666 public reader deployment candidates", where
    `scripts/check-a666-near-solana-valuation-policies` reports
    `missing field max_receipt_age_ns` while decoding
    `manifests/a666/near-receipt-policy.json`.
    - The N1 repair (`f37b6c60`) made `max_receipt_age_ns` and
      `max_receipt_age_blocks` required: `near_receipt.rs:52,55`, strictly
      decoded (`:38`).
    - The code is right. The branch's own test
      (`manifest_builder.rs:706-719`) asserts that the tracked policies fail to
      decode.
    - Adding the [proposal's][proposal] values (1800000000000 ns / 3000 blocks)
      changes the NEAR commitment from `75b18cc9…` to `50d5cde9…`. That changes
      the registered source manifest (hash `8abe3e59…`, pinned by
      `a666-successor-program-identity.json`). It is a proof input, so I made no
      change.
    - `aave-arbitrum-policy.json` has the same gap, but no CI step decodes it
      yet.
    - The finding is on the [PR][finding] and in the
      [next release plan][next] (`ce08eaf5`, `9d71b968`).
  - Task Node: `task_f0cad051…` Rewarded 2.6 PFT; `task_40e7367b…` Rewarded
    1.4 PFT.
- **Storage G3 / A3** (main `e8a962cd`, `db9357f2`; [G3][g3]).
  - [`run_replay_evidence.py`][harness] gained a `--legacy-source-dir` mode
    (with `--recorded-manifest`) and six fail-first tests. The pair and
    signed-archive modes are unchanged.
  - The run used `eea96ba6…` on a scratch copy of
    `~/.postfiat/deployments/storage-rollout-10dd9f20/g6-rehearsal-20260830-v3/backups/validator-0`.
  - **PASS** at height 924, tip `ebeb0e1e…`, root `0854bc47…`.
    - Counts, roots and the ordered history `8d38f779…` equal the recorded
      2026-08-30 six-clone report and manifest (also the
      [stop receipt][stop]).
    - The independent `storage-rebuild-transactional --verify-only` passed, with
      the clone and target hashes unchanged.
    - The source tree hash is `13ffe388…` before and after.
  - G3's 924 boxes and A3 are ticked. The first receipts were superseded the
    same day by the redacted re-run (next bullet).
  - Task Node `task_cc4a7064…`: Rewarded, 3 PFT.
- **Storage A4 / G5** (main `52628d40`, `f26a2ec6`, `5c331e60`, `325afbdb`,
  `4180407f`; [G5][g5]).
  - **The refusal.** The packer and the verifier require one source and one
    binary for G1, G2, G4, the replays and a migration rehearsal
    (`storage_scaling.py:506-508`, `package_packet.py:612,623`).
    - G1, G2 and G4 of 2026-10-20 stood on `8644f0af`'s pipeline build
      (`d1799edb…`); the replays stood on the deployed `eea96ba6…`
      (`86706699`).
    - The verifier also demanded the lost 915 archive.
    - No six-clone migration rehearsal exists for the candidate.
    - `verify-only.json` carried home-directory paths.
    - G2's last box and three G4D boxes are open.
    - Task Node `task_07cbc892…`: Rewarded, 2 PFT.
  - **1123 as the 915 replacement (`5c331e60`).** The packager
    (`--replacement-archive-receipt`) and the verifier accept the 1123 signed
    canary in place of the lost 915 input.
    - `artifacts/replay.json` carries a `quarantine_archive_replacement` block.
    - The verifier pins height 1123 with manifest `d957141e…` as the only
      approved replacement, on the packet's own source and binary.
    - The legacy pair path is unchanged.
    - Ten new fail-first tests; 63 pass. G5 gap 2 is ticked.
    - Task Node `task_7a9dfd8b…`: Rewarded, 1.9 PFT.
  - **Relative paths only (`325afbdb`, `4180407f`).** The harness writes every
    path in receipts, reports and `verify-only.json` under a labelled root
    (`<scratch>/`, `<source>/`, `<output>/`) or as a file label.
    - Any other absolute path fails the run. The real paths go only to
      `local-paths.private.json`, which the packager never binds.
    - Four fail-first tests (17 in the file).
    - The 924 re-run (12:52–13:06Z) passed at 924 / `ebeb0e1e…` / `0854bc47…`.
      Receipts are in
      `~/.cache/g3-924-replay-20261022/receipts/height-924-harness-redacted/`:
      `replay-report.json` `fa071f84…`, `height-924.json` `fa643375…`
      (byte-identical to the first run), `verify-only.json` `10dc5398…`.
    - The source tree is still `13ffe388…`. The 1123 receipt never carried a
      host path, so it was not re-run.
    - G5 gap 4 is ticked.
    - Task Node `task_4f08f9c8…`: Rewarded, 2 PFT.
  - **Attempt 4: G1, G2 and G4 on the deployed binary** (decision of
    2026-10-22; plan header `ac7a4982`, closure `5b24f5d7`; [result][g4a4]).
    **PASS**, evidence eligible.
    - The pipeline accepted the deployed executable without a rebuild: it
      embeds `86706699`/`release`.
    - The batch helper `fb83d467…` carried over from attempt 3. Its runner
      enforces the older page bounds 176 / 160 / 32, so I checked the run
      against the re-derived 96 / 80 / 32 afterwards.
    - Consensus ratio 1.0482 and wallet 1.0637, both under the 1.10 limit.
    - Per-stage p95 is at the August level; stage `database_opens` 0; page
      reads 37 / 43 / 42, within 96 / 80 / 32.
    - Campaign report
      `~/repos/postfiat-storage-g4-regression-20261022/campaign-report.json`,
      sha256 `7aa8d72c…`.
    - Task Node `task_aa0cb63f…`: Rewarded, 3.5 PFT.
  - **Left before `OFFLINE QUALIFIED`:** the six-clone migration rehearsal on
    `eea96ba6…`, then the packet and the offline verifier. Both are mine.
- **Z2** (main `4bd15ec0`; [plan][z2]): six steps, 14–23 working days.
  - **The clock.** Testnet rounds run on Tuesdays. If the sub-scorer is frozen
    by 2026-10-26, the counted shadow rounds are 10-27, 11-03, 11-10 and 11-17.
    The earliest production switch is then the round of 2026-11-24.
  - **The pinned module will be v3.** The fork changed after v2:
    - software scores 0 below the minimum safe version (since 09-21);
    - 25 UNL seats (since 09-24);
    - the fork's own diversity formula (since 10-09).
  - **A conflict to fix.** `validator_admission_policy.rs:334-341` and
    `:499-503` hold a candidate when the model output is missing, the opposite
    of the decided rule. Nothing live calls it; step 4 fixes it.
  - **The flag needs its own rule.** "Legitimacy score 0 = flag" would have
    flagged 33 of 55 validators on 2026-09-03.
- **Z3 / first cycle** (main `abd42f4d`, `3daeaec9`, `94be91b6`;
  [prover provenance][z3]).
  - **The prover.** The pfUSDC tier-4 host prover was rebuilt from a clean
    checkout of main `4bd15ec0` (release, `--locked`, 187 s).
    - Binary `~/.cache/pfusdc-prover-build-20261022/bin/pfusdc-tier4-prover`,
      sha256 `ee1387c9…`. Its receipt, `receipt.json` beside it, has sha256
      `02ab85e1…`.
    - Go 1.24.6 was already present and verified against go.dev. The libclang
      wheel is installed under the build directory only.
    - The hash differs from the borrowed `1372ad0c…`, as expected: SQ-01 and the
      10-15 lock changes.
  - **The Arc egress guest program** (`EGRESS_ELF`, sha256 `8b0f266a…`) was
    deleted with `release-repair-20260916` on 2026-10-19.
    - It was found at commit `65df4263`, the retained `arc-v2-20260902` commit
      in `releases.json`, under
      `programs/pfusdc-egress/elf/pfusdc-egress-program`.
    - There is no file copy elsewhere on the work server or on the six
      validators.
    - Restored to
      `~/.cache/arc-identity-20260902-restored/pfusdc-egress-program`, mode 400,
      with `restore-receipt.json` beside it. The z3 inputs sheet names both.
  - Task Node `task_5e14f032…`: Rewarded, 2.25 PFT.
- **Contributor pull requests** (main `9d10133c`, `a70ce9f9`, `f4aea4b3`).
  - **#103 merged** at the author's updated head `e096c802`: the 2147483647 ms
    cap, approved by citadelculture on 10-15. `wallet-proxy` 40/40, and the
    `routes.json` values pass.
  - **#52 closed** as superseded by #56/#109, with a note. #47 had been closed
    by its author on 10-15; I posted a note there too.
  - **Tool locks.** The five non-frozen `tools/*` locks were bumped to
    rustls-webpki 0.103.16 and webpki-roots 1.0.10.
    - The checksums match the index, and `cargo metadata --locked` is ok.
    - The inventory reports 94 hashes ok, and the fuzz lock is untouched.
  - **#95** is open. Its author answered my 10-14 request on 10-14 with head
    `75ff3688`, which citadelculture approved on 10-15, so the re-review is
    mine.
  - Task Node `task_47b75b4a…`: Rewarded, 1.75 PFT.
- **Devnet.** Not touched today.
  - **Live probe:** my read-only RPC reads at 09:47Z and 13:06Z. Six
    validators at 1137 / `18a4dc86…` / `1277c76c…`; the swap service at
    committee epoch 2; both routes at authority epoch 1 with hashes
    `57da3837…` / `b2817e68…`. The issuer updates are not submitted.
  - **Deployed:** release `store-handle-20261021`, source `86706699`,
    executable `eea96ba6…` ([Current State][state]). The release branch is at
    `6692edf2`.
  - **Merged but undeployed:** the root `Cargo.lock` advisory bump
    (`79d5f909`) and the `wallet-proxy` timeout cap (`9d10133c`). Nothing in
    `crates/`.
- **Task Node.** The nine tasks above total 20.4 PFT
  (2.6 + 1.4 + 3 + 2 + 1.9 + 2 + 3.5 + 2.25 + 1.75). This handoff has no Task
  Node action.
- **Work server.** 121 GB free. The G4 attempt-4 output is under
  `~/repos/postfiat-storage-g4-regression-20261022`.

## Next decision or action

### My next steps, in order

1. **Z2 step 1.** Refresh and freeze the v3 sub-scorer against the fork's
   current main, record its hash, and update the shadow comparison script. The
   shadow-round clock starts there.
2. **The storage packet.** The six-clone migration rehearsal on the deployed
   binary, then the packet and `OFFLINE QUALIFIED`.
3. **The validator-5 checkpoint.** Once the two issuer updates are in: the next
   Ethereum checkpoint, 5 of 6, with validator-5.
4. **StakeHub.** The rehearsal preconditions on our side: the activation check,
   the binaries, the proxy and the prover.
5. **Pull requests.** The #95 re-review, and new bot pull requests as they come.

### Only the other lane can provide

I ask the other lane for the following; each shows the date first asked.

- **(g)** The two issuer signatures and submissions per the [sheet][issuer]
  (`release/fastlane-cap-20261014` `61e9b00c`; it reads the heights itself):
  A666 first, then BMNRC. This blocks the validator-5 checkpoint. 2026-09-25 /
  2026-10-01.
- **(f)** [PR #49][pr49]: regenerate the successor policy manifests (step 1 of
  the [successor proposal][proposal]; a pinned proof input), then register the
  profile on its host, after the gates. 2026-09-24.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` secret, after its local fork-test run.
  2026-09-28.
- **The first StakeHub rehearsal.** On your machine when it suits you, under
  custody rule (a), with our preconditions prepared first. 2026-10-21.
- **Its review of its unpublished work.** 2026-10-20.

## References

- The other lane's [2026-10-20 handoff][nazgul]; my [2026-10-21 handoff][previous].
- Main: `ce08eaf5`, `9d71b968`, `4bd15ec0`, `e8a962cd`, `db9357f2`, `52628d40`,
  `abd42f4d`, `3daeaec9`, `9d10133c`, `a70ce9f9`, `f4aea4b3`, `5c331e60`,
  `325afbdb`, `4180407f`, `94be91b6`, `f26a2ec6`, `ac7a4982` (attempt 4
  header), `5b24f5d7` (closure).
- PR #49 branch: `16d41b5d`, `066323b4`.
- [Z2 plan][z2]; [storage scaling milestone][milestone] ([G3][g3], [G5][g5]);
  [testnet path milestone][testnet]; [G4 campaign plan][g4a4];
  [z3 inputs sheet][z3]; [next release plan][next]; [Current State][state].

[nazgul]: 2026-10-20___nazgul__founder_lane_resync_and_answers_to_open_asks.md
[previous]: 2026-10-21___dravlic__store_handle_release_deployed_and_swap_service_on_epoch_2.md
[state]: ../status/chain-state-current.md
[next]: ../plans/active/next-validator-release-plan-20261101.md
[milestone]: ../plans/completed/storage-scaling-milestone.md
[g3]: ../plans/completed/storage-scaling-milestone.md#g3-exact-replay
[g5]: ../plans/completed/storage-scaling-milestone.md#g5-offline-qualification-packet
[testnet]: ../plans/active/l1v2-public-testnet-path-milestone.md
[g4a4]: ../plans/active/g4-regression-deployed-release-20261019.md#result-2026-10-22-attempt-4-deployed-binary
[z2]: ../plans/active/z2-advisory-flag-execution-plan-20261022.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/4180407f37d32d037201743ff1fcd47320b59754/docs/status/z3-cycle1-inputs-20260922.md#prover-provenance
[proposal]: https://github.com/postfiatorg/postfiatl1v2/blob/4180407f37d32d037201743ff1fcd47320b59754/docs/review/nav-reserve-proof-successor-proposal-20260924.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/066323b4e287bb37faba7b4c8faadf398a95f209/docs/status/OPEN-SOURCE-PROOF-PUBLIC-INPUT-INVENTORY-20260716.json
[harness]: https://github.com/postfiatorg/postfiatl1v2/blob/4180407f37d32d037201743ff1fcd47320b59754/benchmarks/storage-scaling/run_replay_evidence.py
[stop]: https://github.com/postfiatorg/postfiatl1v2/blob/4180407f37d32d037201743ff1fcd47320b59754/benchmarks/storage-scaling/devnet-rollout/stop-receipt-20260830.json
[candidate]: https://github.com/postfiatorg/postfiatl1v2/blob/066323b4e287bb37faba7b4c8faadf398a95f209/tools/nav-reserve-proof/qualifications/freshness-and-debt-20260924/candidate-identity.json
[review]: https://github.com/postfiatorg/postfiatl1v2/pull/49#pullrequestreview-5612473267
[finding]: https://github.com/postfiatorg/postfiatl1v2/pull/49#issuecomment-6338421951
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[issuer]: https://github.com/postfiatorg/postfiatl1v2/blob/61e9b00c8399907f45dff2be1ee44b8f1da431af/deployments/fastlane-cap-20261014/ISSUER-SIGNING-SHEET-20261020.md
