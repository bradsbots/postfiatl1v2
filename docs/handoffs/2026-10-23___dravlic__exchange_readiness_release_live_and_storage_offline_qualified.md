# Exchange readiness release live and storage offline qualified

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-23 UTC
- **Responding to:** the other lane's [2026-10-23 handoff][lane1023] and
  [2026-10-22 handoff][nazgul]. My previous handoff: [2026-10-22][previous].

## BLUF

The other lane's eight merged pull requests are reviewed, released and live.
They are #138–#144 and #49, merged at main `124a187b`; docs #146 was merged at
`5b2efe9d`.

- **Release.** `exchange-readiness-20261023` runs on all six validators: source
  `6b1a0585` (main `d9260e93` plus the release directory), executable
  `4085ac70…`, manifest `210544a8…`.
  - Installed 07:10–07:37Z, with grant blocks 1138–1143.
  - The account history index (schema v2) is built on all six.
- **Activation.** The three execution rules are active from height 1153, set by
  governance records the six validators signed:
  - `rejected_tx_fee_activation_height` at block 1144;
  - `require_memo_activation_height` at 1145;
  - `recipient_format_activation_height` at 1146, last, because it cannot be
    undone.

  Block 1144 needed a view change; seven grants then brought the tip to 1153.
- **Defects fixed on the way.**
  - Review XR-01/XR-02, in `6604c93e`.
  - The index build and the `account_tx` fallback scan stopped on this
    devnet's repeated governance receipt ids. Fixed in `d9260e93`. The
    deployed binary had the same defect, so the live nodes could not have
    served account history for this chain before today.
- **Storage.** The milestone is OFFLINE QUALIFIED and retired to the
  completed plans. The six-clone rehearsal that failed in August passed on the
  deployed binary.
- **Z2.**
  - Step 1a is complete.
  - Step 2's specification is locked (86.33), with prompt v1 pinned and the
    pipeline skeleton tested offline.
  - Step 3's rule module is in.
- **StakeHub rehearsal.** Our side is ready except your acceptance file.
- **SCT-08.** The evidence campaign has started: item 5 passes, and item 4 is
  partly done. Items 1–3 need records only Post Fiat and the Task Node
  maintainers hold.
- **Other.** #95 is merged, and the plan for the next release is drafted. The
  two issuer updates are still unsigned.

## Current state

**Fleet.** [Current State][state] has the deployment record.

- **Last observation:** 11:07Z today, read only. All six were at 1153, tip
  `db8b87b6…`, root `7141956e…`, on `4085ac70…`, with empty mempools.
- **Lineage:** release branch `release/exchange-readiness-20261023` at
  `f79438f2`; the source is `6b1a0585`, whose `crates/` and `Cargo.lock` equal
  main `d9260e93`.
- **Live probes today:** status, agreement and admission probes, and grants.
- **Merged on main but not deployed:**
  - `0ac2bc9b` and `56603e04`: the index follows block commits;
  - `62c0d56a` and `2d4da27c`: the FastSwap payload helpers;
  - `1b317fc4`: the entry-profile module, not called by consensus;
  - `bb742ec7`: #95, a wallet-proxy change.

**Review** (main `52b24db7`, [review][review]). Verdict CUT.

- **XR-01 (low, latent).** The Orchard deposit's funding transfer targets the
  41-character fee collector address. It runs outside the gated wrappers; the
  comment and a regression test are in `6604c93e`.
- **XR-02 (low).** `verify_mempool` lacked the `IssuedPaymentV2` arm. Fixed in
  `6604c93e`.
- **XR-03 (info).** A later amendment can postpone the fee-claim and
  require-memo heights. The recipient-format height cannot be postponed.
- **XR-04 (info).** The old binary rejects the new amendment kinds and the
  `account_set` and `issued_payment_v2` transactions. All six therefore had to
  run the new binary before any governance record.
- **XR-05 (info).** Without a v2 index, `account_tx` falls back to the archive
  scan.
- **Admission.** "Malformed" means any destination that is not `pf` plus 40
  lowercase hex characters. Every address in use passes, including all 58
  ledger accounts and all 646 destination values through height 1123. Only the
  fee sink `pffee0…` is refused, and it is never a mempool destination.

**Release cut** (release `8b0ea1f8`, then the merge `6b1a0585` and the
re-qualification `42b09cb2`; main `3e956ff1`, `0f852110`;
[packet][packet]).

- Two identical clean builds produced `4085ac70c7bb3c21b46cc67be8cb1bbb3556bfea9f49fbf6b128cdac2adcbef9`.
  The signed manifest is `210544a8…`, and the generated units are
  byte-identical to the previous release's apart from the release ID.
- The history checks passed on the 1131, 1123, 1115 and 1050 canaries and the
  six 2026-09-28 copies. The rotation and rollback rehearsal passed.
- Both exact replays the other lane asked for pass with the new binary:
  - height 924, legacy source: 972 receipts, receipts root `f2e27abe…`, all 14
    recorded fields;
  - the 1131 signed archive.
- **Admission probe.** Three malformed recipients are refused with
  `invalid_recipient_address`: 41 characters, a `PF` prefix, and
  `pf-exchange`. A valid mixed-case checksum address is refused with
  `noncanonical_recipient_address`.
- The activation heights are unset in the build.
- The index build works on the 1131 import, at 3.6 s per 1,000 blocks.
- CI is green on main `2cd26f4f`, whose `crates/` and `Cargo.lock` equal the
  release source: rust-ci `39910640663`, product-security-ci `39910640530`,
  docs-build `39910640670`.

**Index defect** (main `d9260e93`, [cause and rule][requal]).

- **Cause.** A governance receipt's `tx_id` is its amendment id, and a rejected
  governance operation may be retried under the same id in a later batch. On
  this devnet, `219306e6…` is accepted at 64 and 66. `c9acb974…` is rejected at
  940 and 941 and accepted at 945.
- **Fix.** `receipt_by_tx_id` (`crates/node/src/block_finality.rs:972` at
  `6b1a0585`) accepts a repeated id only when every linking block is a
  governance block and the receipt count equals the link count. `tx` returns
  the latest receipt, and ordinary repeats are still refused.
- **Scope.** Read path only; the exact replays' receipts roots show the bytes
  are unchanged.
- **Before the fix.** The index was absent on all six. The deployed binary's
  fallback scan fails the same way on the signed import; this was shown
  offline, not probed live.

**Release day** (release branch `35ae2287`, `65ec6d94`, `7c08f704`,
`5b0cba9e`, `cc7b4cbb`, `2c31d1b0`, `1287da78`, `f79438f2`; main `d1ad40ba`,
`5aa9b4d3`, `022bfde0`, `36158400`; [sheet][sheet]).

- **Before and canary.**
  - Before state: 1137 / `18a4dc86…` / `1277c76c…` on `eea96ba6…`.
  - Signed canary backup of validator-1 at 1137, manifest `3257115c…`. The new
    binary re-imported it and verified the checkpoint and a full replay.
  - Receipts, fees and sequences equal the 1131 record plus the six 2026-10-21
    grants.
  - The current-head harness replay passes ([record][canary]).
- **Rollout** 07:10:57–07:37:03Z, order 1, 0, 2, 3, 4, 5. Grants 1138–1143 were
  each certified identically on all six, and no rollback was needed.
- **After checks:**
  - all 12 processes on `4085ac70…`;
  - manifest verified and build `6b1a0585` on all six;
  - `demo-preflight.py` READY (60/0/0);
  - activation heights inactive;
  - admission probe passed on validator-0.
- **Index build** 08:02–08:23Z, one host at a time. Only the RPC unit was
  stopped, for 11–31 s per host. Each index holds 1,105 blocks, 970 rows and
  255 accounts.
- **Activation** 08:38–10:28Z, with H = 1143 + 10 = 1153. Each record had six
  authorizations, each signed on its own host.
  - **1144 at view 0 failed.** The default 5 s timeout expired before
    validator-5's reply arrived; replies on this fleet take up to about 20 s,
    and the sheet now passes 60 s ([first stop][stop1]). The retry was refused
    by validator-4's own vote-safety rule ([second stop][stop2]).
  - **The view change** followed sheet §8b, written from the deployed code
    first. Six timeout votes made a certificate with 6 of 6 votes (quorum 5).
    The view-1 proposal can only carry the locked block
    (`consensus_v2.rs:432-461`).
  - **1144 at view 1** (proposer validator-5) committed on validators 0–4 with
    six accepting votes. Validator-5 missed its own block: the round command
    sends the block to its own validator service while holding the store lock
    (`transport_protocol.rs:910-918`, `transport_runtime.rs:2838`).
  - **Validator-5 catch-up:** the same certified block was re-sent from
    validator-4 and applied on the first attempt. Validator-5's health is
    clean: load 0.87, 2.55 GB available, no restarts, no journal errors.
  - **1145 and 1146.** Block 1145 (require-memo, validator-5) and block 1146
    (recipient-format, validator-0) used the live scripts' flags
    `--quorum-early-full-propagation --local-apply-before-certified-send`.
  - **Grants to 1153:** seven grants at 1147–1153, each certified identically
    on all six.
  - **Probes at 1153:** a malformed recipient is refused and a canonical one
    passes. The fee-claim and require-memo rules are confirmed read-only,
    because the mempool refuses failing transfers and no account sets the
    flag.
  - **After state:** 1153 / `db8b87b6…` / `7141956e…`; `demo-preflight.py`
    READY.
- **Index rebuild after the activation.** All six were rebuilt to 1153:
  validator-1 at 10:32Z and the others 10:52–11:05Z. This release's index does
  not follow commits; the next release does.
- **Docs.** [Address format][addr] now notes that recipient-format cannot be
  undone, the required round flags and the view-change procedure.

**Storage** (main `9e4e267a`, `2cd26f4f`, `b055543c`, `475436b4`, `35d0d477`,
`a364eaed`, `4d8d2a72`, `8934f1f9`, `1ab8f514`, `22edd02e`;
[milestone][storage]).

- **Six-clone migration rehearsal:** PASS 04:15–06:09Z on `eea96ba6…`.
  - At 924, 925 and 928 all six validators agree.
  - Block 925 was accepted 6/6, where it failed in August.
  - The 932 activation passed with validator-5 held back and then caught up.
  - The incompatible old binary refused the activation round.
- **packet-r3** (`~/.cache/storage-packet-20261023/packet-r3/`, work server)
  verifies offline:
  - checksum manifest `357f06ee…`, verifier output `e4fba47e…`;
  - 178 files and 69 tamper cases;
  - the 1123 replacement is accepted;
  - ratios 1.0482 / 1.0637, and 0.350 / 0.450.
- **Verifier review.** The verifier changes are reviewed: ACCEPT WITH CHANGES
  ([review][svreview]). They cover the ported runner gates, the one tolerated
  slow round, the 5 ms growth floor and the binary exemption in the redaction
  scan. The three requested changes are applied in `4d8d2a72`.
- **Status:** OFFLINE QUALIFIED. That is not G6 or CLONE QUALIFIED, and not a
  deployment decision.
- **Testnet path.** A1, A4 and A5 are ticked, so section A is complete
  ([testnet path][testnet]). `state-and-storage.md`, the evidence index and the
  operator runbook are updated.

**Z2** (main `5b9f99a8`, `4e70747c`, `6ba024e4`, `1b317fc4`, `072a9e87`,
`428af589`; [plan][z2]).

- **Step 1a is complete.**
  - `subscorer_v3.py` is frozen at `f71f29dd…`.
  - Round 28 is reproduced: the published UNL, the final scores of all 61
    validators, no flips and overlap 24/25. Rounds 12–19 are unchanged.
  - Counted weekly rounds start on 2026-10-27.
- **Step 2's specification** ([spec][spec]) is locked: the first gate gave
  85.67; after one improvement pass the second gave 86.33 (GPT 85.40,
  Fable 85.60, GLM 88.00).
  - The flag rule raises a flag only when the model and the strict profile
    agree. On the 2026-09-03 example that is 13 flags instead of 33.
  - The ten open points are decided.
  - Prompt v1 is pinned.
  - The pipeline skeleton passes its 27 offline tests.
- **Step 3's `entry_profile_v1` module** sits in `consensus_cobalt` beside the
  live policy, with its Python mirror. All 263 shared fixture cases are
  byte-convergent, and consensus does not call it until step 4.
- **Cost of the weekly flag runs.** They are paid from your OpenRouter account,
  the one the server already uses, at about $5 per round. The runs use two
  rented GPU hosts, so how the rental is paid from that account is settled
  before the first run. Please say if you object.
- **Left:**
  - the rest of step 2: the flag variant of `run_host.py` (0.5 d), a frozen
    packet set for the round's candidates (1–2 d plus the §8 publication
    review), and the first two-owner GPU run (0.5 d);
  - step 1b (1.5–3 d);
  - step 3's frozen history input (0.5–1 d);
  - steps 4–5;
  - the counted rounds.

**StakeHub rehearsal preconditions** (StakeHub `6523eec`, `7d02df7`, `73bf102`,
`c424482`; main `62c0d56a`, `2d4da27c`; [rehearsal plan][rehearsal]).

- **Activation check.** Check 0c′ is written down with its expected line.
- **Activation payload.** `fastswap_bootstrap_payload --committee-file` writes
  the epoch-2 activation payload: SHA-256 `718fce15…`, policy `356e5cca…`,
  activation height 152, the ledger's.
- **Wallet helper.** It now builds payloads under the activation's committee
  epoch. It reads an epoch-2 or later payload only when `ACCEPTANCE.json` names
  its epoch, root and fingerprint. It refuses a committee that differs from the
  live one, before any deposit.
- **Binaries.** The three binaries are rebuilt: `bc1d9d17…`, `bdd68e22…` and
  `bce06fa2…`, with receipt `2df2ea38…`.
- **Remaining, on your machine:** install the payload and the binaries, and
  write your `ACCEPTANCE.json`. The commands are in the plan's row (a).
- **Steps 2 and 5** also need a proxy with a bridge route, which runs nowhere
  today, and a rented GPU host, which there is none of today.

**SCT-08** (main `0a0b5fa9`, `41d7a74a`, `2a82b837`, `3c67f72a`;
[campaign][sct08]).

- **Item 5 passes.** The native registry root `08a451e0…` at 1123, 1131 and
  1137 equals the root that the registry update activated at 924 set. All 213
  certificates 925–1137 carry it. The shadow runner now takes that root from a
  signed archive, and the 1137 derivation passes (report `6b2059a4…`).
- **Item 4 is partly done.**
  - Membership, keys and the Cobalt governance state derive from the archives.
  - Reliability is defined as accepted votes over a window of finalized
    heights, counted only from per-height vote records; certificate inclusion
    never stands in for a vote record. The node does not record those votes
    yet; that is a candidate in the [next release plan][next2].
  - Accountability, ρ, operator manifests, domain control and the model
    classification cannot run here.
- **Shadow report.** The committed 2026-09-04 report no longer reproduces byte
  for byte, because the SCT-02 fix added a field. All three verdicts still
  hold.
- **Items 1–3** need records that exist nowhere yet:
  - signed validator-to-wallet bindings (Post Fiat);
  - signed work digests and the publishing-key record (the Task Node
    maintainers);
  - the funding exclusion list (Post Fiat).

**Pull requests and plans.**

- #95 is merged: head `75ff3688`, merge `bb742ec7`, record `92c388c2`. It is not
  in today's release.
- The [next release plan][next2] (`33160188`) is the skeleton for the release
  after this one.
- The [current plan's][next] rows are updated.

**Devnet changes today.**

- **Rollout:** validator and RPC units restarted one host at a time, and six
  grant blocks.
- **Index builds:** two rounds, with the RPC unit stopped on each host.
- **Activation:** three governance blocks, 1144–1146, with a view change at
  1144, then seven grant blocks, 1147–1153.
- **PFT moved:** 13 PFT of grants plus fees.
- **Routes:** both routes are at authority epoch 1 (`57da3837…` /
  `b2817e68…`), as read at the 1137 before state, and no route transaction has
  run since. The issuer updates are not submitted.

**Task Node.** 21 tasks were rewarded today. The backend returned errors
several times, so three steps ran without an accepted task:

- the review: its task stayed proposed;
- sheet §0–§4: its task stayed proposed;
- the §7 index build: no task was created.

This handoff has no Task Node action.

**Work server.** About 100 GB free.

## Next decision or action

My next steps, in order:

1. **The next release** ([plan][next2]). It carries the index that follows
   block commits (`0ac2bc9b`, `56603e04`), the epoch-aware FastSwap payload
   helpers (`62c0d56a`, `2d4da27c`) and the round command's self-delivery fix.
   A bounded per-commit index rewrite is a candidate.
2. **Z2.** The rest of step 2, then step 1b, and the counted weekly rounds from
   2026-10-27.
3. **StakeHub rehearsal.** Once your acceptance file is in place: our proxy with
   a bridge route and the relay's GPU host, the remaining pieces before your
   run.
4. **SCT-08 item 4 on our side.** The per-height vote records, a next-release
   candidate.
5. **The validator-5 Ethereum checkpoint,** once the two issuer updates are in.

Only the other lane can provide these. I ask for them; each shows the date
first asked:

- **(g)** The two issuer signatures and submissions per the [sheet][issuer]
  (`release/fastlane-cap-20261014` `61e9b00c`; it reads the heights itself):
  A666 first, then BMNRC. This blocks the validator-5 checkpoint. 2026-09-25 /
  2026-10-01.
- **(f)** The on-chain registration of the reserve-proof candidate, after the
  StakeHub gates. #49 already regenerated the manifests and built the
  candidate. 2026-09-24.
- **The first StakeHub rehearsal** on your machine, when it suits you
  (2026-10-21). Its last precondition is your `ACCEPTANCE.json`, with the
  payload and binaries installed (2026-10-23).
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` secret. 2026-09-28.
- **SCT-08 items 1–3:** the signed bindings, the work digests with the
  publishing keys, and the exclusion list. 2026-10-23.
- **Product decisions.** The genesis supply and the website publication
  decisions the other lane named itself ([2026-10-23 handoff][lane1023]).

## References

- The other lane's [2026-10-23][lane1023] and [2026-10-22][nazgul] handoffs; my
  [2026-10-22 handoff][previous].
- Release: branch [`release/exchange-readiness-20261023`][branch], its
  [deploy sheet][sheet] and [qualification packet][packet].
- Reviews: [exchange readiness][review], [storage verifier][svreview],
  [SCT-08 campaign][sct08].
- Plans: [storage milestone (completed)][storage], [testnet path][testnet],
  [Z2][z2], [current release plan][next], [next release plan][next2]; StakeHub
  [rehearsal plan][rehearsal].
- [Current State][state]; [address format][addr].

[lane1023]: 2026-10-23___codex__chain_pr_merge_handoff.md
[nazgul]: 2026-10-22___nazgul__chain_p0_fixes_for_the_coinbase_review.md
[previous]: 2026-10-22___dravlic__reserve_proof_conditions_done_and_both_replays_in.md
[state]: ../status/chain-state-current.md
[review]: ../review/exchange-readiness-merge-review-20261023.md
[svreview]: ../review/storage-verifier-acceptance-review-20261023.md
[sct08]: ../review/sct08-evidence-campaign-20261023.md
[storage]: ../plans/completed/storage-scaling-milestone.md
[testnet]: ../plans/active/l1v2-public-testnet-path-milestone.md
[z2]: ../plans/active/z2-advisory-flag-execution-plan-20261022.md
[spec]: ../specs/identity-flag-pipeline-spec-20261023.md
[next]: ../plans/active/next-validator-release-plan-20261101.md
[next2]: ../plans/active/next-validator-release-plan-20261108.md
[addr]: ../wallets/address-format.md
[branch]: https://github.com/postfiatorg/postfiatl1v2/tree/release/exchange-readiness-20261023
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/release/exchange-readiness-20261023/deployments/exchange-readiness-20261023/DEPLOY-SHEET.md
[packet]: https://github.com/postfiatorg/postfiatl1v2/blob/release/exchange-readiness-20261023/deployments/exchange-readiness-20261023/qualification/README.md
[requal]: https://github.com/postfiatorg/postfiatl1v2/blob/release/exchange-readiness-20261023/deployments/exchange-readiness-20261023/qualification/README.md#re-qualification-6b1a0585
[canary]: https://github.com/postfiatorg/postfiatl1v2/blob/release/exchange-readiness-20261023/deployments/exchange-readiness-20261023/observed/canary-backup.json
[stop1]: https://github.com/postfiatorg/postfiatl1v2/blob/release/exchange-readiness-20261023/deployments/exchange-readiness-20261023/observed/activation/STOP-20261023.json
[stop2]: https://github.com/postfiatorg/postfiatl1v2/blob/release/exchange-readiness-20261023/deployments/exchange-readiness-20261023/observed/activation/STOP-20261023-retry-1.json
[issuer]: https://github.com/postfiatorg/postfiatl1v2/blob/61e9b00c8399907f45dff2be1ee44b8f1da431af/deployments/fastlane-cap-20261014/ISSUER-SIGNING-SHEET-20261020.md
[rehearsal]: https://github.com/postfiatorg/StakeHub/blob/c4244828a21e803dbe8f84645bf344369959f3b3/docs/review/testnet-rehearsal-plan-20261021.md
