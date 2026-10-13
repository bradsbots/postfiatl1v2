# Contributor pull requests reviewed and relays as services

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-13 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. My previous handoff: [2026-10-12][previous].

## BLUF

The Ethereum relays on 28701 and 28702 now run as enabled systemd units on all
six validator hosts. The release preflight is READY with 60 PASS, 0 ATTENTION
and 0 FAIL, the first fully green preflight ([record][relays], release
`69073c33`; `main` `12731434`). I reviewed the bradsbots pull requests in full
in seven batches. For each I read the whole diff, checked the claims against
the code and its callers, ran the touched tests locally and showed that they
fail without the change. The verdicts are in the [triage table][triage]. 39 are
merged, two wait for the author, #63 waits for CI, and eleven class-B pull
requests are still unreviewed. Nothing was merged unread. The fleet itself is
unchanged ([Current State][state], 2026-10-13 section).

## Current state

- **Fleet.** Last observation: `demo-preflight.py` at 09:45:09Z. All six are on
  `signer-rotation-20261007` at height 1123, tip `bafcc6ef…`, root
  `942d1fc2…`. The relay units are the only change on the hosts. No live probe
  while writing this handoff.
- **Relays as services** ([record][relays]; [relay table][tools]).
  - 09:41–09:45Z, one host at a time (validator-5, 0, 2, 3, 4, 1). The
    hand-started python3 relays were replaced by the enabled units
    `navcoin-ethereum-rpc-28701.service` and `navcoin-ethereum-rpc-28702.service`.
    Validator-1 gained only 28702; its 28701 stays on its existing unit.
    Validator and RPC process ids and the other lane's watchdog user units did
    not change; no transaction was sent.
  - [Preflight][preflight] at 09:45:09Z: READY, 60 PASS, 0 ATTENTION, 0 FAIL.
  - Finding: the 28703 archive-relay units on all six hosts and validator-1's
    28701 unit are transient (`systemd-run`) and would not survive a reboot.
    The preflight cannot tell the difference. Follow-up for a later window of
    mine.
- **Contributor pull requests** ([triage table][triage]). Seven batches by
  area. Record commits: `9889f4db`, `a701024d`, `395d60a1`, `16a62899`,
  `d767359d`, `8bd4fa8c`, `5f4c3562`, `02a97fb4`, `0a3f3f52`.
  - 39 merged. Seven of them carry a small fix commit of mine on top, each
    with a test: `5b02fa8f` (#57), `92e6abd6` (#59), `ff56226d` (#65),
    `ed42d646` (#78), `47874faf` (#86), `40ce4f52` (#102), `834a21fd` (#104).
  - Left open with a comment: [#79][pr79] (rebase asked; two replies since) and
    [#72][pr72] (regenerated inventory asked).
  - Class B, node behaviour (#56, #60, #61, #62, #63: issue #27, CHO-05/06,
    SWP-04/05, SMG-05/06, MPL-02). Same standard, plus two questions: what
    changes for valid inputs, and which document asked for the change. Merged:
    #60 `a243aaf2`, #62 `16c3c0ef`, #61 `14850a7e`, #56 `d51f6ae7`.
    [Inventory][inventory]: Fixed 106; Recorded, not fixed 2 (STO-04, CHO-05).
    [#63][pr63] waits only for its CI `test` job, then a local merge. It
    conflicts with `main` on the CHO-05/06 rows; its triage row says how to
    resolve that.
  - Still unreviewed, class B: #76, #77, #80–#85, #95, #99, #103 (large
    `rpc_sdk` diffs, wallet-proxy routing and env semantics, bridge timeouts).
    I did not approve their held CI runs.
  - Decided today as technical matters: #106 (FastSwap TCP connect bounded by
    the transport timeout) and #107 (a 502 instead of a hang when the upstream
    closes mid-body). Each turns a hang into a bounded error and changes no
    default. Both are merged (`8bed8159`, `610636db`).
- **Deployment boundary.** Deployed source `0fa55d0b`. `main` was at `0a3f3f52`
  before this handoff; the release branch is at `69073c33`. Merged but
  undeployed: `9d837bef`, `51144786`, the size-cap and receipt fix `7f9d0d98`,
  and today's merges and fix commits.
  - Six of today's merges change how rpc-serve answers malformed requests:
    #87, #89, #90, #91, #92, #93. Wrong-typed, doubled or incomplete selectors
    and pins are now rejected instead of ignored.
  - No caller in the repository is affected. Outside clients that send null
    optional parameters by hand would be.
  - The plan's [already-on-main list][already] names #87, #89, #91 and #92;
    #90 and #93 are not in it yet.
- **Open findings from the review.**
  - `pft_to_atoms` rounds amounts with more than 28 significant digits before
    the six-decimal check. This is pre-existing and recorded in the #100 row.
  - After a deploy, a host env file with an out-of-range `WALLET_PROXY_*`
    value would stop the wallet proxy (#96, #97, #98). I have not checked the
    hosts.
  - Withdrawal jobs stored earlier with a non-plain amount would look missing
    (#101).
  - The #94 docstring finding closed when #93 was merged.
- **Devnet touched today:** only the relay units. No validator or RPC restart
  and no transaction.
- **Task Node.** Seven tasks Rewarded today, one per batch (11.59 PFT):
  `task_7aec4697…`, `task_ecd2c9a7…`, `task_1b9d7b88…`, `task_896c6fc6…`,
  `task_bd9e688d…`, `task_aa82440d…`, `task_b24a51f5…`. This handoff has no
  Task Node action.
- **CI on `main`** (`gh run list --branch main --limit 60`, read once at
  13:04Z, covering 20 commits from `d767359d` to `0a3f3f52`). No run has
  failed. docs-build passed on all 20. rust-ci passed on `d767359d`,
  `4473bba5` and `926d8a46`; product-security-ci passed on 13. The other 17
  rust-ci and 7 product-security-ci runs are in progress, and none is queued.

## Next decision or action

### My next steps, in order

1. Tomorrow: cut the next release from `main` with the size-cap fix and
   today's reviewed merges, then qualify it locally. Install it on the six
   validators with a fresh canary backup. Then finish the bridge half of the
   signer-group switch ([sheet §8.2–8.4][sheet8]) and hand the unsigned issuer
   update to the other lane.
2. The remaining open contributor pull requests. First the ones waiting for CI
   or the author (#63, #72, #79). Then the class-B ones that change validator
   behaviour, read in full to the same standard.
3. In a later window, make the transient 28703 relay units and validator-1's
   28701 unit proper units.
4. The `pft_to_atoms` rounding gap.

### Only the other lane can provide

I ask the other lane for the following; each shows the date first asked.

- **(a)** NEAR Intents question 2 ([note][near]). 2026-09-29.
- **(b)** The NAVCoin signer keys and the cycle inputs ([inputs][z3]).
  2026-09-22.
- **(c)** The Arc source row on the A666 route. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. 2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** The reserve-proof successor adoption and registration
  ([PR #49][pr49]). 2026-09-24.
- **(g)** Validator-5: the issuer signature on the bridge policy update. It
  becomes possible only after the next release admits the
  `ActivateCommittee`; there is nothing to sign yet. 2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The inventory rows SCT-10 and PI-16 ([inventory][inventory]).
  2026-09-10.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` repository secret. 2026-09-28.
- **(l)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(m)** FW-13. 2026-09-30.

## References

- My [2026-10-12 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Release branch `release/signer-rotation-20261007` at `69073c33`:
  [ethereum-relays-20261013.json][relays], [demo-preflight.py][preflight].
- `main` commits: `12731434`, the record commits and the fix commits above.
- [Next release plan][next]: [triage table][triage] with today's verdicts.
- [Ethereum relays on the validator hosts][tools]; [defect inventory][inventory].
- [Current State][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-12___dravlic__signer_groups_half_switched_and_size_cap_fixed.md
[state]: ../status/chain-state-current.md
[next]: ../plans/active/next-validator-release-plan-20261101.md
[triage]: ../plans/active/next-validator-release-plan-20261101.md#contributor-pull-requests-triaged-2026-10-12
[already]: ../plans/active/next-validator-release-plan-20261101.md#already-on-main-past-the-cut
[tools]: ../navcoins/pftl-tools.md#ethereum-relays-on-the-validator-hosts
[inventory]: ../review/defect-inventory-20260910.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[relays]: https://github.com/postfiatorg/postfiatl1v2/blob/69073c334c9a7a97511d2eb96fb9af69a52b8074/deployments/signer-rotation-20261007/observed/ethereum-relays-20261013.json
[preflight]: https://github.com/postfiatorg/postfiatl1v2/blob/69073c334c9a7a97511d2eb96fb9af69a52b8074/deployments/signer-rotation-20261007/demo-preflight.py
[sheet8]: https://github.com/postfiatorg/postfiatl1v2/blob/69073c334c9a7a97511d2eb96fb9af69a52b8074/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L190-L244
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr63]: https://github.com/postfiatorg/postfiatl1v2/pull/63
[pr72]: https://github.com/postfiatorg/postfiatl1v2/pull/72#issuecomment-6144433008
[pr79]: https://github.com/postfiatorg/postfiatl1v2/pull/79#issuecomment-6143856718
