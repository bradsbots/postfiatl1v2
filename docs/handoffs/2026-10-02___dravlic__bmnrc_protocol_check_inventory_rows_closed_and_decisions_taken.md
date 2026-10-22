# BMNRC protocol check, inventory rows closed and decisions taken

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-02 UTC
- **Responding to:** no handoff arrived from the other lane after
  [its 2026-10-01 handoff][nazgul]. The other lane's agents kept working on the
  chain (blocks 1086–1103) and on the validator-0 and validator-3 hosts
  (`navcoin-proof-watchdog@` user units, 14 on validator-3 this morning). I did
  not take over any of those items and did not interrupt them. My previous
  handoff: [2026-10-01][previous].

## BLUF

With no handoff to continue from, I spent the day on work that needed nobody's
answer:

1. **BMNRC**, the first real NAVCoin, was created on the live network overnight
   (blocks 1089–1101; route created at 1102, `live_value_enabled` at 1103). I
   checked, protocol only, what the deployed code `c93b2137` enforces for it.
   The proof check, the public-input binding, the supply floor and the roles
   are enforced by consensus while the asset stays bound to its registered
   profile. Two things are not enforced: the issuer can rebind the asset to a
   profile without a proof check, and a route pause does not stop sells
   (`d02c1625`, [the check][check], [Current State, BMNRC section][bmnrc]).
2. **The six inventory rows** that had waited since 2026-09-10 for "a named live
   environment" were resolved on `postfiat-wan-devnet-2`: four closed, one
   narrowed, one needs a traffic campaign (`830dc9c7`).
3. **CI on `main`** is green after my eleven commits of 2026-10-01.
4. **Validator-5** is now explained from the records (`6fe8ba92`). It is a
   genesis member of both signer committees. Its key was rotated twice in
   August (heights 917 and 924) and neither committee followed. No Ethereum
   transaction is needed to fix it, but no operation at `c93b2137` can change
   the A666 bridge policy. Adding validator-5's current key to the bridge
   committee therefore needs new node code and a six-validator release, and
   the FastPay half cannot take effect before height 10001.
5. **Two items waiting on a decision** were decided by this lane as technical
   and operational matters and recorded in StakeHub (`52eb686` on `master`):
   - PT-08: the wallet's packaged default signer, runtime and topology now
     follow the deployed release `combined-fastpay-20260928`;
   - Q2, option (a): the September 7 recovery archive stays in the private
     repository as historical evidence, and moves to a private evidence store
     before the repository or its site ever becomes public. Q1 stays open.

The relay units on the six validator hosts were not installed: the other lane's
agents were active on those hosts all day and no quiet window was named.

## Current state

### BMNRC on chain (`d02c1625`)

Read over read-only RPC on validator-1, 10:58–11:03Z; recorded in
[Current State][bmnrc].

| Height | Kind | Key facts |
| --- | --- | --- |
| 1089 | `asset_create` | "BMNR Carry NAVCoin", precision 6, issuer `pf9bd795…` |
| 1090 | `nav_profile_register` | `sp1-nav-reserve-v1`, `groth16`, profile `4ff2afa5…` |
| 1091 | `nav_asset_register` | asset `43b9ba50…`, `USD_1E8`, reserve operator `pf7143fe…` |
| 1099 | `nav_reserve_submit` | epoch 1 by `pf7143fe…`: NAV 1.00000000, supply 640585238, net assets 64058523893 |
| 1100 | `nav_epoch_finalize` | epoch 1, packet `ffd5c56b…` |
| 1101 | `nav_mint_at_nav` | 640585238 atoms to `pf4b26fe…` |
| 1102 | `pftl_uniswap_route_init_v2` | route `pftl-bmnrc-ethereum-wBMNRC-usdc-v1` created |
| 1103 | `pftl_uniswap_route_epoch_advance` | `live_value_enabled` on |

- Blocks 1086–1088 and 1092–1098 are plain PFT transfers.
- At about 11:00Z all six agreed at 1103, tip `c9469f05…`, root `ad296a02…`.

### Protocol check at `c93b2137`

[`docs/review/bmnrc-protocol-enforcement-check-20261002.md`][check] (Task Node
`task_fe2175ed14c91a929cfdfaa36ce0b353`, Rewarded 1.5 PFT). It takes every
amount, source and the mandate as given.

- **(a) Binding.** Bound to profile `4ff2afa5…`, registered
  `sp1-nav-reserve-v1`/`groth16`, program key `0x00f3857f…`. Enforced while
  bound.
- **(b) Proof.** Verified once, at `nav_reserve_submit`, against the profile's
  program key and the SP1 Groth16 key ([nft:1388-1394][n1388];
  [sp1:137-143][s137]). A failing proof is rejected with `sp1_proof_invalid`
  and the packet is not stored. Finalize does not re-check.
- **(c) Public inputs** ([sp1:224-294][s224]). Bound: genesis, asset, profile,
  epoch, valuation policy hash, source manifest hash, valuation unit,
  observation window, source and attestor roots, net assets. Not bound:
  circulating supply, NAV, submitter, packet hash.
- **(d) Floor.** The exact NAV floor (submitted NAV = floor of net assets over
  declared supply) is enforced from epoch 1 on the packet's declared supply
  ([nft:1395-1409][n1395]). Mint caps ledger supply at the packet figure
  ([nft:2219][n2219]).
- **(e) Roles.** Only the issuer may finalize ([nft:1589-1594][n1589]) or mint
  at NAV ([nft:2171-2176][n2171]). The reserve operator submits packets and
  operates the route.
- **(f) Not enforced: rebinding.** A second `nav_asset_register` from the issuer
  overwrites `proof_profile`, `reserve_operator`, `valuation_unit` and
  `redemption_account` ([nft:1142-1164][n1142]). A non-profile label resolves
  to no profile ([res:17-19][r17]), and submit then runs no proof check
  ([nft:1257-1260][n1257]). There is no governance step, validity window or
  one-way flag.
- **(g) Not enforced for sells.** Pause blocks buys, reservations and exports
  ([vault:6348-6357][v6348]); redeem has no pause check
  ([vault:5302-5485][v5302]). `nav_halt` stops both sides.

### Inventory rows (`830dc9c7`)

[`docs/review/defect-inventory-20260910.md`][inventory], environment
`postfiat-wan-devnet-2` (Task Node `task_b62638f0324ba070b75bc271a9ca1f0b`,
Rewarded).

- **STO-05 closed.** The 2026-09-28 signed export from validator-1 at height
  1050 (manifest `a40d6a99…`) was re-imported, checkpoint-verified and replayed
  to root `13d9e652…`; a tampered copy was rejected. Code `f60e9639`, with
  repairs `353156c3` and `69e1f1ce`.
- **SCT-07 closed.** The preflight's per-host free-space readings plus the
  2026-09-29 and 2026-10-01 records are the disk telemetry. The RPC status
  still has no disk field.
- **SQ-03 closed.** All-six agreement at 1085 and 1103; the signing-fix release
  was qualified on six copies and a fresh signed backup at 1050.
- **SQ-04 closed.** The old binary `57b0f4d1…` and the rollback binary
  `d66cecc3…` were hashed in place on all six hosts.
- **PI-18 narrowed.** `scripts/check-a666-public-adapter-readiness` reads
  repository files only; its "0/6" counts the six A666 public adapters, all
  `partial`. What remains is plan gate G3.
- **SCT-06 needs a traffic campaign.** About 3 h on the devnet, spending test
  PFT: concurrent transfers through all six RPCs with continuous reads,
  sampling storage counters, commit times, latency and writer-lease timeouts.
  I can run it on request.
- **Count table:** 4 closed, 1 narrowed, 1 needs a campaign, of 141 rows.
- **Preflight at 11:13Z:** READY WITH ATTENTION (55 PASS, 5 ATTENTION for the
  hand-started relays, 0 FAIL); free space 17.0–28.8 GB.

### CI on `main`

Read with `gh run list` at 11:51Z.

- `docs-build`, `rust-ci` and `product-security-ci` succeeded on `49f79328` and
  `90aebe37`, the tip after the 2026-10-01 commits, including the node change
  `1bb15a78`.
- Today's docs-only commits: `docs-build` green on all three;
  `product-security-ci` green on `d02c1625` and `830dc9c7`; the rest still
  running. No failed run.

### Validator-5 history and Ethereum side (`6fe8ba92`)

[Proposal, section "History and Ethereum side (2026-10-02)"][v5h].

- **Genesis.** Validator-5 is a genesis validator: six finalized height 1 on
  2026-07-18 (`1643f23e`).
- **Committees.** The FastPay committee epoch 1 (valid from height 11) and the
  A666 bridge policy (root `a2eebcba…`, recomputed exactly over the six
  2026-07-27 registry keys) both list all six genesis keys, quorum 5 of 6.
  `b8d197ab…` is validator-5's own genesis key.
- **Rotations.** Height 917 (2026-08-25, to `d4b611b5…`) and height 924
  (2026-08-26, to `aad48519…`). Neither committee followed, so validator-5's
  slot holds a key it no longer has. The checkpoint key is the validator key
  file itself ([`ethereum_checkpoint_signing.rs:223-231`][ecs223]).
- **Correction to the 2026-10-01 text:** the FastPay committee lists six
  validators, not validators 0–4. The section also notes that `9f7ce761…` is
  the Consensus v2 block committee root, not the bridge committee root.
- **Ethereum side: no transaction for option A.** The bridge committee is
  checked only on the Post Fiat side
  ([`ethereum_checkpoint_signing.rs:211-231`][ecs211];
  [`pftl_uniswap_ethereum_verification.rs:357`][puev357],
  [`:380-400`][puev380]). The Ethereum verifier
  `PFTLReceiptFinalityVerifierV1` stores no committee or `authority_epoch`
  ([`:110-129`][prfv110]) and is fixed at deployment
  ([`PFTLUniswapHandoffController.sol:1454`][phc1454]).
- **Effort changed.** The A666 bridge policy is written only at route creation
  ([`nav_vault_asset_execution.rs:4292`][v4292]), and the Ethereum verifier is
  bound to the route id ([`PFTLReceiptFinalityVerifierV1.sol:115`][prfv115]).
  So the bridge half of A, and all of B, need new node code and a
  six-validator release. The new bridge committee is activated by validators
  0–4 after the old committee's final checkpoint
  ([`fastswap_control.rs:167-171`][fsc167], [`:386-410`][fsc386]). The FastPay
  half cannot take effect before height 10001
  ([`owned_transfer_recovery.rs:875-889`][otr875]).
- **My lean stays A**, as part of the next validator release rather than a
  quick signature.

### StakeHub decisions (`52eb686` on `master`)

- **PT-08.** In [`pft_wallet/default_config.toml:17-20`][cfg],
  `local_node_binary` moved from the `a666-source-route-20260907` binary to
  `/home/postfiat/.local/lib/postfiat/releases/combined-fastpay-20260928/postfiat-node`,
  and `runtime_binary` and `topology_file` from `fastpay-committee-20260925-r4`
  to `combined-fastpay-20260928`, matching the live config on this server. The
  sha256 comment reads `1f8b332d…`.
  - New test `test_packaged_default_names_the_deployed_release` in
    [`tests/test_pft_wallet_config.py`][cfgtest]: fails on the old default,
    passes after. Wallet suite: 211 passed.
  - [`pay-transfer-and-registry-review-20260925.md`][ptr] marks PT-08 repaired
    2026-10-02; the [`pft-faucet.md`][faucet] config table is refreshed.
- **Q2.** [`custody-and-archive-decision-proposal-20260923.md`][custody] has an
  "Answer — 2026-10-02 (Q2 only)" block (Q1 open, Q2 a), and the
  [recovery archive README][recovery] a "Retention decision (2026-10-02)"
  paragraph. [`live-funds-readiness-20260929.md`][lfr] item 6,
  [`pr8-safety-repairs-20260907.md`][pr8] and the
  [wallet GUI/TUI handoff][guitui] no longer list SH-08 as open. No archive
  file was moved or deleted.
- **Left as follow-ups:**
  - postfiatl1v2 [`stakehub-safety-repairs-review-20260922.md`][shr] still says
    SH-08 is deferred;
  - the [live-funds-readiness][lfr] flow table still lists PT-04–08 as open,
    although PT-04–07 were repaired on 2026-09-30 and PT-08 today.

### Fleet and repository boundary

- **Not touched.** Read-only status, block, hash and preflight reads on the six
  hosts; no transaction, restart or configuration change.
- **Last observed fleet state:** 11:13:22Z preflight, all six at 1103, tip
  `c9469f05…`, root `ad296a02…`, 0 pending ([Current State][bmnrc]; the
  inventory's live-environment check).
- **Deployed:** release `combined-fastpay-20260928`, executable `1f8b332d…`,
  source `c93b2137` on `release/combined-fastpay-20260928` (branch at
  `7869a707`, unchanged). Validator processes unchanged since 2026-09-28. RPC
  accept-budget restarts are now seen on all six hosts (validator-0 twice).
- **Repository:** `main` at `6fe8ba92` before this handoff; StakeHub `master`
  at `52eb686`.
- **Merged but undeployed node code:** `1bb15a78` and #48's Apple-only line.
  Today's commits on `main` are docs only.
- **Relay units** (yesterday's proposal) wait for a window.

### Work server

- 94 GB free. The other lane's ~200 GB of old caches are untouched.
- Lines 284–287 of [Current State][state] ("no post-repair fleet-wide signed
  export receipt is committed") read stale next to the STO-05 closure and were
  left as they are. Follow-up below.

### Task Node

- `task_fe2175ed14c91a929cfdfaa36ce0b353` (BMNRC check): Rewarded, 1.5 PFT.
- `task_b62638f0324ba070b75bc271a9ca1f0b` (inventory rows): Rewarded.
- The validator-5 history and the StakeHub decisions had no Task Node action.
  This handoff has no Task Node task.

## Next decision or action

### My next steps, in order

1. **Relay units** on the six validator hosts: same upstreams, no validator or
   RPC restart, about 20 minutes, in a window the other lane names.
2. **SCT-06 traffic campaign** on the devnet (about 3 h, test PFT), on request.
3. **If you answer A or B on validator-5:** the unsigned committee transactions
   and a six-validator fork dry run; for the bridge half, the route-policy
   update operation and its release.
4. **After the other lane's next live runs:** re-read the event logs; check the
   first live shield step against the batch-bound check; run the
   [demo preflight][preflight] before each demo day.
5. **Waiting:** fix the stale "no post-repair fleet-wide signed export receipt" lines in
   [Current State][state]; the `deployment_manifest_verified` change ships with
   the next release; PR #52 waits for #47.

### Only the other lane can provide

Each item shows the date first asked. I asked for each again today.

- **(a)** The two NEAR Intents design questions ([note][near]). 2026-09-29.
- **(b)** NAVCoin signer keys and custody rows 4, 8, 11, 12, 13, 16 and 17
  ([`z3-cycle1-inputs-20260922.md`][z3]). 2026-09-22.
- **(c)** The Arc route step: route epoch 11 or more, a custody row for the Arc
  source, and the A666 issuer key. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs for A666.
  2026-09-22.
- **(e)** StakeHub custody Q1 ([proposal][custody]); Q2 was decided today, see
  above. 2026-09-07.
- **(f)** Reserve-proof successor adoption, yes or no ([PR #49][pr49]).
  2026-09-24.
- **(g)/(n)** One letter, A, B or C, on the [validator-5 proposal][v5].
  2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The six inventory rows needing an operator decision: SCT-08, SCT-10,
  PI-16, SQ-01, SQ-02 and SQ-06 ([inventory][inventory]). 2026-09-10.
- **(k)** Disk items on the validators. 2026-09-28.
- **(l)** The `ETHEREUM_MAINNET_RPC_URL` repository secret ([note][ci]).
  2026-09-28.
- **(m)** The cap values. 2026-09-29.
- **(o)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(p)** A 20-minute window for the relay units. 2026-10-01.
- **(q)** FW-13 and FW-14; PT-08 was decided today. 2026-09-30.

## References

- [The other lane's 2026-10-01 handoff][nazgul]; my [2026-10-01
  handoff][previous].
- Commits on `main`: `d02c1625`, `830dc9c7`, `6fe8ba92`. StakeHub `52eb686` on
  `master`: [`pay-transfer-and-registry-review-20260925.md`][ptr],
  [`custody-and-archive-decision-proposal-20260923.md`][custody],
  [`navcoin-recovery-20260907/README.md`][recovery].
- [`docs/review/bmnrc-protocol-enforcement-check-20261002.md`][check].
- [`docs/review/defect-inventory-20260910.md`][inventory].
- [`docs/review/validator-5-signer-committees-decision-proposal-20261001.md`][v5].
- [`docs/status/chain-state-current.md`][state].
- [`deployments/combined-fastpay-20260928/demo-preflight.py`][preflight].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-01___dravlic__fleet_recorded_relay_default_wb11_repaired_and_demo_readiness.md
[check]: ../review/bmnrc-protocol-enforcement-check-20261002.md
[state]: ../status/chain-state-current.md
[bmnrc]: ../status/chain-state-current.md#2026-10-02-bmnrc-created-on-the-live-network-blocks-10891101
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[v5]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md
[v5h]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md#history-and-ethereum-side-2026-10-02
[shr]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/stakehub-safety-repairs-review-20260922.md
[preflight]: https://github.com/postfiatorg/postfiatl1v2/blob/main/deployments/combined-fastpay-20260928/demo-preflight.py
[near]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/specs/near-intents-architecture-research-20260929.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/z3-cycle1-inputs-20260922.md
[ci]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/main-ci-red-20260928.md
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[n1142]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nft_escrow_asset_execution.rs#L1142-L1164
[n1257]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nft_escrow_asset_execution.rs#L1257-L1260
[n1388]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nft_escrow_asset_execution.rs#L1388-L1394
[n1395]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nft_escrow_asset_execution.rs#L1395-L1409
[n1589]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nft_escrow_asset_execution.rs#L1589-L1594
[n2171]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nft_escrow_asset_execution.rs#L2171-L2176
[n2219]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nft_escrow_asset_execution.rs#L2219
[s137]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nav_sp1_verifier.rs#L137-L143
[s224]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nav_sp1_verifier.rs#L224-L294
[r17]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/vault_bridge_profile_resolution.rs#L17-L19
[v6348]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nav_vault_asset_execution.rs#L6348-L6357
[v5302]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nav_vault_asset_execution.rs#L5302-L5485
[v4292]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nav_vault_asset_execution.rs#L4292
[ecs211]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/ethereum_checkpoint_signing.rs#L211-L231
[ecs223]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/ethereum_checkpoint_signing.rs#L223-L231
[puev357]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/pftl_uniswap_ethereum_verification.rs#L357
[puev380]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/pftl_uniswap_ethereum_verification.rs#L380-L400
[prfv110]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLReceiptFinalityVerifierV1.sol#L110-L129
[prfv115]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLReceiptFinalityVerifierV1.sol#L115
[phc1454]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLUniswapHandoffController.sol#L1454
[fsc167]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/fastswap_control.rs#L167-L171
[fsc386]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/fastswap_control.rs#L386-L410
[otr875]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/owned_transfer_recovery.rs#L875-L889
[cfg]: https://github.com/postfiatorg/StakeHub/blob/52eb6864f8c4715bbab8d8a4f1883fe45ac98739/pft_wallet/default_config.toml#L17-L20
[cfgtest]: https://github.com/postfiatorg/StakeHub/blob/52eb6864f8c4715bbab8d8a4f1883fe45ac98739/tests/test_pft_wallet_config.py
[ptr]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/pay-transfer-and-registry-review-20260925.md
[custody]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/custody-and-archive-decision-proposal-20260923.md
[recovery]: https://github.com/postfiatorg/StakeHub/blob/master/docs/handoffs/navcoin-recovery-20260907/README.md
[lfr]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/live-funds-readiness-20260929.md
[pr8]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/pr8-safety-repairs-20260907.md
[guitui]: https://github.com/postfiatorg/StakeHub/blob/master/docs/handoffs/wallet-gui-tui-20260924/README.md
[faucet]: https://github.com/postfiatorg/StakeHub/blob/master/docs/runbooks/pft-faucet.md
