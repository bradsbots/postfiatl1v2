# FastPay stall fixed live and main line caught up

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-09-28 UTC

## BLUF

The FastPay stall trigger left open on 2026-09-25 is repaired, qualified,
installed on all six validators and proven live. I implemented fix (a) from the
other lane's [r4 handoff][r4]. A registered validator that cannot sign for the
FastPay committee now runs the full certificate check, journals the effect
durably, signs nothing and returns an unsigned held-effect receipt. Its own next
proposal therefore anchors the effect. Committee, eligibility, quorum, signing,
block format and vote rules are unchanged ([design][design]; fix `c93b2137` on
`release/combined-fastpay-20260928`).

In the live check at 08:28–08:38Z, validator-5 proposed height 1061 at view 0
with the FastPay effect anchored and no timeout votes. On 2026-09-25 the same
situation at 1043 needed view 1. I also merged the other lane's two StakeHub
wallet branches after review. main now carries the installed line, and the
cause of main's red CI is found and cleared ([CI finding][ci]). The Z3 inputs
were re-read, two Z3 tooling items were repaired, and validator-1's disk was
cleaned. [Current State][state] records the deployment, the live check and the
cleanup.

## Current state

- **Qualification** ([packet][packet]):
  - Two identical builds, executable
    `1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a`.
  - 18 full-history checks PASS, including block 1011.
  - A fresh signed validator-1 canary backup at 1050 was verified and fully
    replayed.
  - PASS: the fix test, FastPay, view recovery, the governance gate and the
    rollback rehearsal with `d66cecc3…`.
  - Full workspace suite: 84 groups, 1,487 passed, 0 failed.
- **Deployment** ([README][deploy]; release branch `3aceeed1`, main note
  `c4cbf759`):
  - I installed `combined-fastpay-20260928` at 07:40–08:05Z, one validator at
    a time (validator-1 canary, then 0, 2, 3, 4, 5).
  - Each validator was confirmed with one 1 PFT devnet faucet grant (blocks
    1051–1056, all view 0, identical on all six). No rollback was needed.
- **Live check** ([record][live]; release branch `209d1535`, main note
  `e7c85996`):
  - I funded a throwaway wallet (1057) and made two grants (1058, 1059), a
    FastPay wrap (1060) and a 0.001 PFT FastPay payment to `testing`. The
    payment was signed by validators 0–4.
  - After the payment, all six validators held the same FastPay journal entry.
  - Height 1061: proposed by validator-5 at view 0, effect anchored, no timeout
    votes; tip `ab20666b…` and root `20d21e0e…` on all six.
  - I returned the throwaway wallet's PFT to the faucet (1062) and deleted its
    keys.
- **Fleet and repository boundary:**
  - **Last observed fleet state:** 2026-09-28T08:38Z, at the end of the live
    check. All six were on `combined-fastpay-20260928` at height 1062, tip
    `9d08fd3e…`, root `6324f86e…`.
  - **Deployed:** executable `1f8b332d…`, signed manifest `d2fdb687…`, source
    `c93b2137` on `release/combined-fastpay-20260928`.
  - **Rollback:** the `combined-fastpay-20260925` (`d66cecc3…`) executable and
    units with the data in place, or the signed 1050 backup.
  - **Repository:** `main` was `36230038` before this handoff.
    `release/combined-fastpay-20260928` is at `209d1535`, after `f6911294`
    (design), `c93b2137` (fix and tests), `94a48304` and `7d249c11` (packet)
    and `3aceeed1` (deployment, DEPLOYED 08:05Z).
    `release/combined-fastpay-20260925` is at `4d88956b` (disk inventory),
    after `1775ae33` (wallet configuration note).
  - **Merged but undeployed:** no node code. main's `crates/` are identical to
    `c93b2137`. main's later commits change only docs and the reserve-demo
    script.
  - **Live probe:** the live check above was the session's live probe. I made
    no fleet probe while writing this handoff.
- **Devnet transactions today:**
  - Ten 1 PFT faucet grants to `testing` or the throwaway wallet (1051–1059,
    1061).
  - One FastPay wrap of 1,001 atoms (1060), and one 0.001 PFT FastPay payment
    anchored at 1061.
  - One return transfer (1062).
  - The faucet went from 85.995400 to 76.994036 PFT. Nothing else moved.
- **StakeHub** ([review][sh-review]): I reviewed the other lane's two wallet
  branches and found 0 P1, 4 P2 and 7 P3. I repaired the four P2s with
  reproduce-first tests and recorded the P3s.
  - **Merges:** [PR #16][sh16] as `00a7596` (Pay transfer and stalled-proposer
    recovery; PT-01, PT-02, PT-03) and [PR #17][sh17] as `01db0f3` (wallet
    registry; PR-01).
  - **Test basis:** the full suite, 5,268 passed, with the same 84 environment
    failures as unchanged master.
  - **PT-04 (P3):** the SSH path to validators runs a small relay to the local
    RPC and asks for timeout votes and submission. It is not read-only, but no
    key material leaves the server.
  - **Wallet configuration:** `~/.pft/config.toml` on this server now points at
    `combined-fastpay-20260928` ([note][wallet-note]). `default_config.toml` in
    `pft_wallet` still carries r4 paths, which affects new configurations only.
- **main and CI** ([finding][ci]):
  - **Merge:** I merged the installed line as `6b8f6ea8`. Its code is identical
    to `c93b2137`, and main's newer docs were kept.
  - **Cause of the red CI (since 2026-09-16):** a Clippy error in
    `cobalt_handoff.rs` and unformatted FastPay cherry-picks. The merge cleared
    both.
  - **Green again:** rust-ci `check` and docs-build.
  - **Still running when this was written:** rust-ci `test` and
    `open-reserve-proof-kit` on `f6a78c96`.
  - **Red:** product-security-ci's `python-sdk` job on `f6a78c96` failed at
    dependency install because pip found no `ckzg==2.1.8`. The same job passed
    on `1ef5356a`. I have not started a rerun.
  - [PR #50][pr50] is marked merged.
- **Z3** ([inputs][z3], re-read `cfb67016`):
  - Rows 2, 3 and 9 are resolved. Row 14 still needs the other lane's live
    quote. The NAV profile blocker is unchanged.
  - Arc is not the active route of the pfUSDC family. The Ethereum route
    (epoch 10) is.
  - **Repaired today:**
    - `25610696`: the reserve-demo custody check reads an omitted
      `reservation_escrows` map as empty (27 + 70 tests).
    - `0aa5cc63`: the command sheet and the G1 lineage line are bound to
      `combined-fastpay-20260928` / `c93b2137` / `1f8b332d…`.
  - **Still open on this lane:** the Arc allowance is 0 (approval at cycle
    time). The other morning re-read values have not been re-checked on the
    20260928 release; its executable differs only by the FastPay fix.
- **`deployment_manifest_verified=false`** (`36230038`, explained in
  [Current State][state]): `status` never checks the publisher signature.
  - It hashes the manifest and checks only the bindings and runtime hashes
    (since `7095b393`, finding SRV-03).
  - The signature check runs in each unit's `ExecStartPre`, but its result is
    not passed to the node.
  - The name is misleading; the fleet is fine.
- **Disk** (inventory [before deletion][disk]; release branch `4d88956b`, main
  note `edacac0e`):
  - validator-1 now has 9.92 GB free, up from 2.95 GB. I removed only our
    rollout tool's old snapshot exports, staged binaries and one half-finished
    upload.
  - validator-0 has 7.7 GB free.
  - The 13.9 GB per host is one live, never-rotated event log,
    `transport-validator-events.ndjson`.
  - **Kept for the other lane:**
    - `/var/backups/postfiat` dumps: 10.6 GB on validator-1, 7.6 GB on
      validator-0.
    - `gate931`: 7.7 GB and 7.1 GB.
    - `gate926`: 5.5 GB and 4.9 GB.
    - Unknown-origin items: three
      `.a666-checkpoint-verifier-experimental.incoming*` binaries,
      `a666-opening-export-proof-h348` and
      `fastpay-committee-20260925-r3-retained-payment`.
- **Task Node, all Rewarded:**
  - Wallet branches: `task_4487e50c602b93db99fab3e937cb37b5`, 1.7 PFT.
  - Fix: `task_7fdcc6a65a11b1d782f507c618191638`, 4 PFT.
  - Qualification: `task_dcd3f64f4332d1935607847ea501cede`, 3.4 PFT.
  - Deployment: `task_394108ef…`, 3.3 PFT.
  - Main line and CI: `task_471d3d905d4a6cfe79e7f9d0eaa48e78`, 3.5 PFT.
  - No Task Node action was taken for this handoff.

## Next decision or action

### This lane's next steps

1. **Event log and status field.**
   - Rotate or cap the 13.9 GB event log on each validator. This is a
     host-side change and needs its own go.
   - For `deployment_manifest_verified`, either rename the field or pass the
     startup check's result into `status`. This is a node change for the next
     release.
2. **First Z3 cycle,** once the other lane's keys, inputs and Arc route step
   are in.
3. **StakeHub:**
   - The recorded P3s: 17 from last week and 7 from today.
   - The r4 paths in `default_config.toml`.
   - The proxy's harmless retry against validator-5, which never gets a signed
     acknowledgement. This is a small proxy change.
4. **Keep main green.**
   - Read the final verdicts with `gh run list --branch main --limit 3` and fix
     anything red, starting with the `python-sdk` install failure.
   - The `official-mainnet-fork` job runs vacuously because the repository has
     no `ETHEREUM_MAINNET_RPC_URL` secret. Only the repository owner can add
     it.
5. **Reserve-proof successor** ([PR #49][pr49]) once it is approved.

### Only the other lane can provide

Each item was asked again tonight.

1. **NAVCoin signer keys and custody,** and rows 4, 8, 11, 12, 13, 16 and 17 —
   first asked 2026-09-22.
2. **The Arc route step** — first asked 2026-09-28. It needs a route epoch of
   11 or more with a custody row for the Arc source on the primary route,
   signed by the A666 issuer key (`pffcb93…`).
3. **A compatible governed NAV profile with fresh proofs** — first asked
   2026-09-22.
4. **StakeHub custody Q1 and archive Q2** — first asked 2026-09-07
   ([proposal][custody]).
5. **Reserve-proof successor adoption, yes or no** — first asked 2026-09-24
   ([PR #49][pr49], [proposal][successor]).
6. **FastPay committee rotation for validator-5** (governance) — first asked
   2026-09-25. Liveness no longer needs it after today's fix, but validator-5
   still needs it to sign FastPay payments.
7. **Height-915 archive and height-924 custodian** — first asked 2026-08-30.
8. **AI-governance decision for Gate Zero Z2** — first asked 2026-09-03.
9. **Twelve [inventory][inventory] rows** — first asked 2026-09-10.
10. **Disk:** may the September 5–7 dumps, `gate931`, `gate926` and the three
    unknown-origin entries be deleted? First asked 2026-09-28.

## References

- This lane's [2026-09-25 handoff][previous] and the other lane's
  [r4 view recovery handoff][r4].
- [FastPay effect-anchoring design][design] and [main CI finding][ci].
- Release branch: [qualification packet][packet], [deployment README][deploy]
  and [live check record][live].
- [Current State][state] and [Z3 cycle-1 inputs][z3].
- StakeHub [PR #16][sh16], [PR #17][sh17] and the [review][sh-review].

[previous]: 2026-09-25___dravlic__merged_fastpay_and_combined_lines_qualified_and_deployed.md
[r4]: 2026-09-25___postfiatchad__r4_view_recovery_chain_unstuck.md
[state]: ../status/chain-state-current.md
[design]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/fastpay-effect-anchoring-fix-20260928.md
[ci]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/main-ci-red-20260928.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/z3-cycle1-inputs-20260922.md
[successor]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/nav-reserve-proof-successor-proposal-20260924.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[packet]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260928/deployments/release-repair-20260928/README.md
[deploy]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260928/deployments/combined-fastpay-20260928/README.md
[live]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260928/deployments/combined-fastpay-20260928/observed/live-fix-check.json
[wallet-note]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260925/deployments/combined-fastpay-20260925/README.md
[disk]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260925/deployments/combined-fastpay-20260925/observed/disk-inventory-20260928.json
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr50]: https://github.com/postfiatorg/postfiatl1v2/pull/50
[sh16]: https://github.com/postfiatorg/StakeHub/pull/16
[sh17]: https://github.com/postfiatorg/StakeHub/pull/17
[sh-review]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/pay-transfer-and-registry-review-20260925.md
[custody]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/custody-and-archive-decision-proposal-20260923.md
