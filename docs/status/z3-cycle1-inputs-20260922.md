# Z3 cycle-1 inputs and provenance — 2026-09-22

**Collection complete; live cycle remains BLOCKED.** Of the 17 execution fields left null by the [second dry run](z3-dry-run-20260921.md#second-run): **6 resolved / 4 re-read after deployment / 7 needs the other lane** on 2026-09-22; after the [2026-09-28 re-read](#re-read-after-the-2026-09-25-deployment), **9 resolved / 8 needs the other lane**. These counts concern input fields, not satisfied live gates. In particular, recovered signer account names and a tool's TTL default do not establish custody or authorize their use.

Task Node: `task_8dacbe0a2767fa10c90ff70e12080f78`, requested and accepted through the offchain lifecycle; evidence and verification belong to that same task. No skip was needed. Collection began with `git pull --rebase origin main` (already up to date). Main base: `f3075071d31accb8f738bef732dbe83f8f606bfb`. The temporary detached release checkout was `/tmp/z3-inputs-20260922`, commit `f19c7344068a844ea8ec60800f6d83e148a19742` (**R** below).

The existing 39/39 dry-run result is inherited, not rerun. Its immutable seed remains `~/.cache/z3-dry-run-fix-20260921/inputs-reviewed.json`, SHA-256 `5cd8d89ae9dc9ed159cbff61e4cacafc2f1a9747c89986f6c68ae35d457497b7`. No seed, signer, validator data, service, or chain state was changed. Only the requested documentation, temporary worktree, publication gates, Task Node lifecycle and Git publication are writes in this task. No transaction, chain signature, proof generation, deployment, remote shell command, or wallet-secret read occurred. SSH forwarded read-only RPC traffic; signer-file checks used names and file metadata only.

## Re-read after the 2026-09-25 deployment

Read 2026-09-28, read-only, no Task Node action. No transaction, key access or SSH write. **D** is the deployed source, [`f60e9639f83649769f29276a9de14f5f16271877`](https://github.com/postfiatorg/postfiatl1v2/tree/f60e9639f83649769f29276a9de14f5f16271877); both NAV scripts there are byte-identical to R.

- **F2, fleet:** `postfiat-local-rpc-v1` over the existing SSH tunnels `127.0.0.1:27650`–`27655`, 07:12:23–07:13:56Z. Methods: `status`, `server_info`, `mempool_status`, `nav_reserve_proof_status` (A666), `navcoin_bridge_supply_status` (primary route), `vault_bridge_route` (family and Arc series), `vault_bridge_status` (family) and `asset_info` (Arc series). Exploratory validator-0 reads ran at 07:08–07:10Z. All six report distinct IDs and identical values: running, height **1050**, tip `03a24230…`, root `13d9e652…`, build `f60e9639`, binary `d66cecc3…`, manifest `7a682ffe…`, empty mempool. `status` shows `deployment_manifest_verified=false` on all six; the rollout record verified the signed manifest per host, and this was not investigated.
- **E2, Arc:** the E getter list at block 64401669, 07:13:22–07:13:24Z. Every value equals E: all three code hashes; wallet 20,000,000 and vault 1,000,000 atoms; allowance **0**; not paused; binding `0xd9e0cd40…`; egress vkey `0x0036cbe7…`; route epoch 9; finalized height 948; checkpoint commitment `0x2e64ef8e…`; native balance 20×10¹⁸ wei.
- Local unversioned captures: `~/.cache/z3-reread-20260928/fleet-capture.json`, SHA-256 `d7ee7e3a7c640472bf608a07d84de5f63a71095fc5d5bfc2c2aea3c38b0db5a0`, and `arc-capture.json`, SHA-256 `5ef33c10bdc8a35eb3685fb8385156d4438e72c728af36dc75fd6e7d268a8c21`.

**What changed.** Only the release changed. The fleet moved from `a666-source-route-20260907` (build `707e006f`, height 1020) to `combined-fastpay-20260925` (build `f60e9639`, height 1050). Rows 2, 3 and 9 and the A666 NAV state are unchanged, and the row-14 ceiling recomputes to the same value. The pfUSDC and A666 issuers are also unchanged. At F2 the deployed binary and topology were `/opt/postfiat/releases/combined-fastpay-20260925/postfiat-node` and `/etc/postfiat/releases/combined-fastpay-20260925/topology.json`. The 2026-09-23 lineage (`1a0989ad`, `e7bb1afa…`) was never the running executable. The command sheet now names `combined-fastpay-20260928` (see the [lineage note](#ordered-live-command-sheet-blocked-not-executed)).

**First direct route reads.** These states predate the deployment:

- **The Arc route is not active.** The family's active governed vault-bridge route is `ethereum-mainnet-usdc-v1`, epoch 10, profile `b2ca6cda…`, activated at height 1008. For the Arc series, `vault_bridge_route` returns "no active governed profile". D:`crates/node/src/execution_actions.rs::governed_vault_bridge_route_rejection` requires the active route for `vault_bridge_deposit_propose`. Step 7, with policy `f7ce6d3c…` epoch 9, would therefore be rejected. D:`GovernanceState::active_vault_bridge_route_profile` selects the highest (epoch, height). A new Arc activation would therefore need epoch ≥ 11, which differs from the decided epoch-9 route and the verifier's `routeEpoch()` 9.
- **The Arc source has no custody row.** The primary route's only custody row is the Ethereum source `2bae082a…`: enabled for issue, principal 12,419, spread 54,721. These live values replace H's figures. `build-issue` stops with "selected source series has no custody row". The row can be added only by a route-epoch advance with `settlement_source_asset_ids`, signed by A666 route operator `pffcb93…` (D:`crates/execution/src/pftl_source_settlement.rs::pftl_source_govern`).
- **Tooling mismatch.** The node omits empty `reservation_escrows`. D:`scripts/a666-pfusdc-reserve-demo.py::selected_source_custody` rejects the live read-back with "source custody reservation_escrows must be an object". This was checked locally against F2. **Fixed on main 2026-09-28** (`25610696`): only an absent map reads as empty, every other field still fails closed, and the fixed check accepts validator-0's 09:52:13Z read-back on `combined-fastpay-20260928` (same row as F2).

**Release after F2 (2026-09-28).** From 07:40 to 08:05Z, after F2, the fleet moved to `combined-fastpay-20260928`: source `c93b213755f5889565fd1f77b9e45c149a07193a`, executable `1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a`, manifest `d2fdb687…`. Its [deployment directory](https://github.com/postfiatorg/postfiatl1v2/tree/release/combined-fastpay-20260928/deployments/combined-fastpay-20260928) is on `release/combined-fastpay-20260928` and was merged into main as `6b8f6ea8`. Relative to D, its `crates/`, `scripts/` and `python/` differ only in four FastPay node files, so the D-relative findings here still hold. A read-only `status` at 09:51:50–09:51:55Z showed all six validators at height 1062 with build `c93b2137`, binary `1f8b332d…` and manifest `d2fdb687…`. No other F2 value was re-read on this release.

**NAV compatibility blocker: unchanged.** The live A666 profile is `a94a3929…`: `verifier_kind=sp1-groth16`, `source_class=stakehub-six-leg-reserves-v3`, with no `public_values_schema` or `source_manifest_hash`. It is at epoch 8 with NAV 103,523,693, packet `f670ad00…`, not halted. D:`a666-build-live-nav-mark-ops.py::active_profile` still requires `sp1-nav-reserve-v1` and `postfiat.nav_reserve_public_values.v1`. D:`a666-pfusdc-reserve-demo.py::validate_nav_binding` still requires source-manifest and schema bindings. D validates `sp1-nav-reserve-v1` profiles, and its status would expose those bindings. The block is therefore the governed profile and fresh proofs, not node support.

**Cycle 1 remains blocked by:**

1. *Other lane:* PFTL signer keys and custody for holder/owner, pfUSDC proposer/finalizer/settler, A666 issuer and NAV reserve submitter.
2. *Other lane:* rows 4, 8, 11, 12, 13, 16 and 17. Row 14's live quote then follows from rows 4 and 12–13.
3. *Other lane:* a governed NAV profile compatible with the tooling, with fresh opening and post-subscription proofs. Rows 3 and 9 follow it if the profile changes.
4. *Other lane:* an Arc custody row enabled for issue on the primary route, through a route-epoch advance signed by `pffcb93…`.
5. *Our side, operator decision:* Arc ingress needs an active governed Arc route, which the decided epoch-9 identities cannot supply.
6. *Our side, fixed 2026-09-28:* the `reservation_escrows` tooling mismatch (`25610696`).
7. *Our side:* bind INPUTS to the running release `combined-fastpay-20260928`. The command sheet was rebound on 2026-09-28.
8. *Our side:* the separately authorized Arc allowance approval, because the allowance is 0.
9. The [predecessor and monitoring items](#predecessors-read-backs-and-monitoring-still-required) below.

## Provenance key

- **R:** [release checkout](https://github.com/postfiatorg/postfiatl1v2/tree/f19c7344068a844ea8ec60800f6d83e148a19742). Every R-relative path below is pinned to that full commit.
- **A:** R:`docs/evidence/arc-mvp-20260828/devnet-20260902/`, committed by [a40f257e](https://github.com/postfiatorg/postfiatl1v2/commit/a40f257eb13d656e79c4c08889d3d692014ad4cd). This is historical Arc evidence, not a new-cycle packet.
- **H:** `/home/postfiatchad/.cache/stakehub-safety-docs-20260922/handoffs/navcoin-recovery-20260907/`. This existing local copy is **unversioned: its source commit is unavailable**. File hashes are recorded below; its values are historical candidates, not qualified live inputs.
- **F:** six-validator status/health read-backs in the fleet table below, height 1020 on the supplied `a666-source-route-20260907` release.
- **E:** Arc read-backs below, all state calls pinned to block **63401279**, `0x3c76d3f`, at `https://rpc.testnet.arc.network`. All capture times are the collecting server's UTC clock on September 22.
- **F2 / E2:** the [2026-09-28 re-read](#re-read-after-the-2026-09-25-deployment): six validators at height 1050 on `combined-fastpay-20260925`, and Arc block **64401669**, `0x3d6b105`.

## The 17 formerly unknown fields

“Resolved” means an existing artifact/tool or permitted observation supplies a value. “Re-read after deployment” keeps a historical value or calculation provisional until the selected deployed state is captured. “Needs the other lane” identifies a missing binding, file, selection or proof that this collection cannot supply. All dynamic Arc observations must also be refreshed immediately before use.

| # | Input field | Value or explicit remaining input | Status | Provenance / deployment dependency |
| --- | --- | --- | --- | --- |
| 1 | `manifest.identities.anchor_code_hash` | `0x3782655d3b1faac7889003995a6bf461bde994bb3968ab832c213f64675625f0` | resolved | E: `eth_getCode(anchor,0x3c76d3f)`, 09:49:21.420971Z; Keccak-256 of 3,084 runtime bytes. Independent of the PFTL executable; refresh at preflight. |
| 2 | `manifest.policy_hashes.primary_route` | **Advanced 2026-10-04/05:** policy `32c970e9…`, route epoch 11, valid heights 1110–10000, not paused. Only custody row: still the Ethereum pfUSDC source `2bae082a…`. The sources record only the hash prefix; take the full hash from a fresh read-back before sealing INPUTS. Before block 1110: policy `fffecee58fdf91cde477f71214fde2b1d9d7a94fa27d671e6e0081017c03e7bd53d74ee8199b899efffa81beaad46e37`, policy and route epoch 10, valid heights 1012–10000 | resolved | Block 1110 `pftl_uniswap_route_epoch_advance` 10 → 11, signed by `pffcb93d…` ([Current State, 2026-10-05](chain-state-current.md#2026-10-05-weekend-state-before-the-other-lanes-conference-day)); validator-1 read-only read 2026-10-05 10:55Z ([handoff](../handoffs/2026-10-05___dravlic__release_after_the_conference_prepared_on_main.md)), one validator. Epoch 10 value: F2, 2026-09-28 07:12:23–07:13:56Z, `navcoin_bridge_supply_status` for `pftl-a666-ethereum-wA666-usdc-v1`, identical on all six. Formerly H only. Distinct from Arc route epoch 9 and from route-config digest `12ed00ca…`. |
| 3 | `manifest.proof_keys.nav` | **Unchanged:** a94a profile key `0x00580ee8c389192568a29dc23d54c22e73a3a45203b22e3d5a934801871e11a7` | resolved | F2, same window: `nav_reserve_proof_status` for A666, `active_profile.sp1_program_vkey`, identical on all six. Recomputing the profile ID from that profile reproduces `a94a3929…`. This legacy key does **not** solve the NAV-builder mismatch below; it changes if row 8's compatible profile is activated. |
| 4 | `manifest.accounts.owner` | **null**. Existing A666 subscriber/owner: `pfab9b9228942e5c529633a13aa271d5297bec6353`; September 2 deposit recipient: `pffcb93d9f87a843a8aa34e1adf241f5d58143e81b`; claim signer: `pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8` | needs the other lane | R:`deployments/a666-mainnet-20260727/04-opening-holder-trust.ops.json`; A:`devnet/relay-bundle.report.json#/relay_bundle/plan`. Supply one explicit cycle owner with recoverable custody and the required source/A666 balances and permissions. The wrapper uses that one owner for deposit recipient, claim signer, subscriber, redeem and burn; the old packets cannot be spliced into that binding. |
| 5 | `manifest.accounts.proposer` | `pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8` | resolved | A:`devnet/relay-bundle.report.json#/relay_bundle/plan/propose_operation/proposer`. Existing pfUSDC operation signer; distinct from the elected validator proposer. Re-read eligibility after deployment; custody remains open. |
| 6 | `manifest.accounts.finalizer` | `pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8` | resolved | A:`devnet/relay-bundle.report.json#/relay_bundle/plan/finalize_operation/finalizer`. Re-read governed finalization eligibility after deployment; custody remains open. |
| 7 | `manifest.accounts.bridge_settler` | `pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8` | resolved | H:`resumed-epoch10/pfusdc-egress/settle.ops.json` names both source and `issuer_or_redemption_account`; R:`deployments/pfusdc-tier4-v3-accel-short-20260719/input.json#/asset/issuer` supplies the same committed public issuer. Re-read current issuer/redemption authority after deployment. |
| 8 | `reserve_identities.nav_source_manifest_hash` | **null**. The observed legacy a94a profile has no provider-neutral source-manifest binding | needs the other lane | F plus R:`tools/nav-reserve-proof/qualifications/a666-shadow-20260730/reconciliation.json`. Supply a governed, compatible profile/source manifest and its provenance. Neither the retired shadow hash nor the public-successor hash can be inserted under a94a. |
| 9 | `reserve_identities.nav_program_vkey` | **Unchanged:** same `0x00580ee8c389192568a29dc23d54c22e73a3a45203b22e3d5a934801871e11a7` as row 3 | resolved | Same F2 read as row 3. The two input fields must remain identical; re-read the full selected profile before sealing INPUTS. |
| 10 | `paths.remote_runner` | `/home/postfiatchad/repos/postfiatl1v2/scripts/a666-remote-sync-round.py` | resolved | Main base and R contain identical bytes, SHA-256 `1e090f92b3cce27266231fc202c23299c60dfe69dc3a86fa276fd4a9c3edfaff`. R:`scripts/a666-ce22-remote-finality-op.py` copies this helper to `/usr/local/sbin/a666-remote-sync-round.py` only during a future authorized submission. It was only read here. |
| 11 | `paths.proposer_hosts_file` | **null** path; all six mapping values are established in the fleet table | needs the other lane | F and [September 17 preflight](z3-preflight-20260917.md#fleet). H:`profile-live.json` expects `/home/postfiat/.local/share/stakehub/navcoin-reproduction-20260906/hosts.json`, absent on this server. Supply an operator-owned JSON file mapping exactly validator-0 through validator-5 to those hosts; no host-map file was created here. |
| 12 | `paths.opening_nav_manifest` | **null**. Historical epoch-8 path: `/home/postfiat/.local/share/stakehub/navcoin-reproduction-20260906/nav-refresh-e8/ops/live-nav-mark-manifest.json`, absent locally | needs the other lane | H:`profile-live.json`. The committed July opening manifest has another schema/profile/epoch; it is not a substitute. Supply a fresh accepted manifest satisfying every field in `validate_nav_binding`, under the selected deployed profile. |
| 13 | `paths.fresh_packet_operation` | **null**; a same-cycle, post-subscription NAV reserve packet does not yet exist | needs the other lane | R:`scripts/a666-build-live-nav-mark-ops.py`, `active_profile` / `validate_packet`. Needs fresh source observations, qualified proof, post-subscription supply and the source-reserve overlay counted once. It depends on future verified predecessor artifacts, not only deployment. |
| 14 | `parameters.mint_amount_atoms` | **null live quote**. Cap ceiling **unchanged: 1,922,312 native atoms**, base 1,990,049, spread 9,951, spend 2,000,000 source atoms | needs the other lane | F2, same window, `navcoin_bridge_supply_status`: pricing NAV epoch 8 at 103,523,693 USD_1E8, issue multiplier 10,050 bps, orders 1,000,000–1,000,000,000,000, available issue 1,000,000,000,000; all unchanged. Recomputed with `derive_issue_amounts` at `f60e9639`. A live quote still needs the fresh NAV (rows 12–13), row 4's owner and source balance, and an Arc source custody row enabled for issue, which does not exist ([re-read](#re-read-after-the-2026-09-25-deployment)). This is not a chosen mint amount. |
| 15 | `parameters.reservation_ttl_blocks` | **128 blocks**, recovered tool default | resolved | R:`scripts/a666-pfusdc-reserve-demo.py`, `--reservation-ttl-blocks`. Future `ISSUE_HEIGHT + 128` must be strictly below policy expiry. Record operator adoption with the live envelope; this is not a seconds-based deadline. |
| 16 | `parameters.deposit_nonce` | **null**; no unused cycle-1 bytes32 nonce has been supplied | needs the other lane | A's deposit nonce is already historical. R:`crates/ethereum-contracts/src/ERC20BridgeVaultV2.sol::depositV2` keys `depositSeen` by the full deposit ID, not nonce alone. Supply the nonce and selected owner, derive the exact wallet/amount/recipient/route-bound ID, then read `depositSeen(bytes32)` on vault and anchor at preflight. No nonce was generated or reserved here. |
| 17 | `parameters.reservation_recipient` | **null**. Existing A666 tooling recipient: `0x1455bd7fbfbf92a171ef36025e13959e3b0ad8c0` | needs the other lane | H:`profile-live.json` and [G2](../review/z3-g2-route-compatibility-20260917.md). Supply/confirm the reservation recipient. It is an existing Ethereum export binding; it is not implicitly the Arc wallet. This cycle releases the export entitlement. |

The archived family definition in `~/.cache/release-repair-20260918/rollback/validator-0/ledger.json` names pfUSDC issuer `pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8`; its a94a profile contains the row-3 key and no source-manifest/schema field. This legacy JSON file has trailing data and was inspected as a historical first JSON document only, **not** treated as the active transactional database. Whole-file SHA-256: `5ecb7b738406b371cf4058d33878b7754eae9ab1fa0a3f803a5c20ef0de898d6`; source commit of this local capture is unavailable.

H file SHA-256 provenance:

| H-relative file | SHA-256 |
| --- | --- |
| `profile-live.json` | `03093e8bd90017338f39f0e896718a7226f6899f93d59897a130cffe5e618ed9` |
| `resumed-epoch10/pftl-supply-status-after.json` | `3d35da5973724cb1c524051e5beaa09ecbe4d26817bc3d3d0024c85bfbda158c` |
| `resumed-epoch10/primary-redeem/primary-redeem.ops.json` | `672acce3bea6daf1492b4bed689c08d4beb80f58590dad51e0d1ced265b4a2e3` |
| `resumed-epoch10/pfusdc-egress/settle.ops.json` | `addd113a8168bc2294ae9b187daa77bac6c2fc0526e7f90c66b25696d093755f` |

## Fixed identities and remaining envelope inputs

These are copied from the reviewed seed and the user's decided facts; no route/asset identity was re-derived. Mirrored fields in `manifest.identities` and `reserve_identities` must agree. The reserve identity object's schema remains `postfiat.reserve_demo_identities.v1`.

| Input group | Recorded value | Treatment |
| --- | --- | --- |
| Cycle | First live cycle **1**, amount/cap **2,000,000 atoms** | Seed cycle 0 and its timestamps remain dry-run evidence. Supply actual start/end UTC; end stays null only until sealing. |
| Chain/domain | PFTL `postfiat-wan-devnet-2`, protocol **1**; Arc **5042002** | Decided; F/E observations are point-in-time. |
| Arc pair | Anchor `0x92390d3a2102cb74e4746c05b4d91f61093475d0`; vault `0x160307f3efead79b6a3629c4b8d90e8301fc250f`; verifier `0x1d436908516d15e3c55a936899b47a885e047f27` | Decided current-v2; source route epoch **9**. E2: code, binding, vkey and route epoch unchanged. |
| Token/wallet | USDC `0x3600000000000000000000000000000000000000`; wallet `0xC75Bf05Ce82d6f4b6139dd9446D6De5F5994a4CB` | Six-decimal atoms; native balance is the same USDC at 18 decimals, not additional funds. |
| Arc route | `pfusdc-arc-testnet-tier4-epoch9`; EVM binding `0xd9e0cd409c5d1e118d65c78ee059adcbba937616353e9675e350d52ee8d498b2` | Re-read 2026-09-28 (F2, `vault_bridge_route`): **not the active governed route**; the family's active route is Ethereum epoch 10. Blocks ingress; see [re-read](#re-read-after-the-2026-09-25-deployment). |
| Arc profile/source policy | `f7ce6d3cce3bd058a218db6bd829b01be13c576a2270aed362052d12654fc7a911a8423ee2d961ca45dbf72c08df6ae2` | Re-read 2026-09-28 (F2, `vault_bridge_status`): still the Arc bucket's pinned policy; not the active route profile. |
| Arc bucket | `fcc209605f8cfda895acbf78047f83f97b0bc1cee3927582fb262efb46e7d136b098183d5f83e19a82d34c218bab67a7` | Same exact source; do not substitute the family. F2: `active`, counted 1,000,000, outstanding 0. |
| Arc source series | `3923511d5be0557a61051e099b606d3decc11a5ba274c7d551168735accad8ed18d89c9200efc4bfbbbab6e85d4c173f` | Re-read 2026-09-28 (F2): outstanding supply 0; **no custody row** on the A666 primary route. |
| A666 primary route | `pftl-a666-ethereum-wA666-usdc-v1` | Existing export domain remains Ethereum **1**, outbound `TRUSTLESS_FINALITY`, return `BFT_CHECKPOINT`. |
| Native A666 asset | `521c6c630bb48d4a37ab4a7bd4900dd2caa2d9e99499e452da3c7ce75b3d74b62d20e18555642bec32174498cbee5e2c` | Decided. |
| pfUSDC settlement family | `02c46a36eb0da3516b4d8affea8f4028ad3f36825a3e8f0e009ea9dbbbcfb3c233f6830bd5221fe2717fb6a1a7005d7b` | Remains subscription settlement family; reserve/redeem select the exact Arc series. |
| Existing NAV profile | `a94a392926967722b2cceb88b19c4108726381f5b184007185a27e91f3e27c63dcc713a28f6cc4cf765826564e2b5f52` | F: epoch **8**, NAV **103523693**, packet `f670ad00bfdcf838a5d551988a2f750bd118deae03ea8042a2ff3879bc2fd7d3664c22a87ff40e8aab2260b17685ac96`. F2 2026-09-28: unchanged, not halted. |
| NAV valuation | `076c071e44127158ef82350e7feeb64e0be0a06bf8ba4be5f0374ac36b992ac7`; unit `USD_1E8` | Seed requires schema `postfiat.nav_reserve_public_values.v1`; F's legacy profile does not establish that schema. |
| Source verifier policy | `1c61349713b41cc15b3ec0863605b1ed5ef65ee43faa862ff17211c194023b26` | Decided seed binding; refresh on deployed source profile. |
| Issuer / reserve operator | `pffcb93d9f87a843a8aa34e1adf241f5d58143e81b` / `pfd0c86d9084915e1fefd22eab891806397d5a5937` | Explicit existing NAV-builder authorities; signer custody still required. |
| Qualified-node reference | `~/.cache/release-repair-20260928/binaries/candidate-1`; SHA-256 `1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a` | 2026-09-28: the running executable, source `c93b2137`, qualified PASS in `deployments/release-repair-20260928/`; local copy rehashed. Supersedes the 2026-09-18 reference `~/.cache/qualify-fix-20260918/binaries/candidate-1`, `051ad12c…` (R:`deployments/release-repair-20260918/node-builds.json`, source `03e422a7`). |
| Deployment / checkout | `combined-fastpay-20260928`; remote binary `/opt/postfiat/releases/combined-fastpay-20260928/postfiat-node`; topology `/etc/postfiat/releases/combined-fastpay-20260928/topology.json` | 2026-09-28: the running release ([after F2](#re-read-after-the-2026-09-25-deployment)). It supersedes the prepared `combined-devnet-20260921` and the 2026-09-25 `combined-fastpay-20260925`. Seed checkout commit `b1201bc9f2d30822359ce5610b2a465f120d4b96` and inspected R are distinct from `c93b2137`; INPUTS must bind the running checkout, source and runtime. Do not relabel R as a `1f8b332d` build. |
| Paths / evidence | Future local WORK `~/.cache/z3-cycle1-20260922/work`, PACKET `~/.cache/z3-cycle1-20260922/packet` | Proposed output destinations only; not created. INPUTS, VALUES, CHECKPOINT and authoritative per-validator data sources still need preparation. Seed `work/validator-data` is a nominal path, not a current state capture. |
| Window / timers | Seed window `2026-09-18T00:00:00Z`–`2026-09-25T00:00:00Z`; per-command timeout **7200 s** | Do not carry forward September 21 cycle timestamps. Confirm the remaining window, live start, all aggregate timers and live authorization. |

**NAV compatibility blocker:** F reports `verifier_kind=sp1-groth16`, `source_class=stakehub-six-leg-reserves-v3`. R:`scripts/a666-build-live-nav-mark-ops.py::active_profile` requires `sp1-nav-reserve-v1` and the provider-neutral public-values schema. Its packet path does not bypass that check. R:`scripts/a666-pfusdc-reserve-demo.py::validate_nav_binding` also requires source-manifest/schema bindings. The public successor at R:`tools/nav-reserve-proof/manifests/a666/profile-registration-public-successor.json` pins key `0x00f3857f96ef97e00bd15b4030acd8d6b0a72740b28c6160d154bc2c9bb141bf`, source manifest `8abe3e59198b72945d4778a7fa91e5af157a6c65032d8940cca486850ffe59fcb567268ca5942669ff6977ef32dd3a41`, and a different valuation policy. It is not evidence of activation or permission to change the decided a94a identity. The other lane must resolve the compatible governed profile/tooling and deliver fresh proofs. No repair or profile selection was attempted. Re-checked 2026-09-28 on the deployed source: [unchanged](#re-read-after-the-2026-09-25-deployment).

H's historical primary-route capture enables only Ethereum source `2bae082a6703375b9405af44715e1e64623265392627767b040fa2c30abb100a09da403724a6f105317292d9c0073df7`, principal 9,950,248 and spread 49,752; it does not establish an enabled Arc row. F also reports the family currently bound to an Ethereum vault profile at NAV epoch 53. These observations cannot be promoted into Arc claim/source-custody readiness. Exact source governance, fresh NAV, route state and balances are **re-read after deployment** requirements; deployment by itself does not perform their maintenance.

## Signer bindings and file presence

No signer file was opened, hashed, restored or tested. “Present” below means only file metadata/name presence on this server at **2026-09-22T09:52:09.849112Z**. Paths are recorded because the user explicitly requested them; this document is not a public cycle evidence packet.

| Role / wrapper argument | Existing public account binding | Expected path(s), never contents | This server / provenance |
| --- | --- | --- | --- |
| Arc signer, `--keystore` | `0xC75Bf05Ce82d6f4b6139dd9446D6De5F5994a4CB` | `~/.foundry/keystores/arc-testnet-server`; password path `~/.postfiat/arc-testnet-server.password` | **Both present**. Decided identity and runbook; contents/custody recovery untested. |
| Owner / subscriber / redeemer / burner, `--holder` | Historical A666 `pfab9b9228942e5c529633a13aa271d5297bec6353`; cycle owner still row 4 | `/home/postfiat/tmp/pfusdc-closed-roundtrip-20260720/keys/holder.json`; older R deployment expects `/home/postfiat/tmp/navswap-ce22-venue-rebuild-20260719/private/holder-key.json` | **Expected paths missing**. H profile/redeem operation; R opening-holder operation. |
| Arc ingress proposer, `--proposer` | `pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8` | Historical validator-2 path `/var/lib/postfiat/validator-2/a666-joe-e2e-20260728/pfusdc-issuer-key.json` | **Missing on this server**; remote presence was not inspected. A public operation plus local `~/.postfiat/deployments/arc-current-v2-a699d560/WORKLOG.md` records that path. |
| Arc ingress finalizer, `--finalizer` | Same pfUSDC account | Same historical `pfusdc-issuer-key.json` | **Expected path missing here**; A public finalize operation. |
| Bridge settler, `--settler` | Same pfUSDC account | `/home/postfiat/tmp/pfusdc-closed-roundtrip-20260720/keys/pfusdc-issuer.json` | **Expected path missing**; H settlement operation. |
| A666 issuer / route operator / NAV finalizer, `--issuer` | `pffcb93d9f87a843a8aa34e1adf241f5d58143e81b` | `/home/postfiat/tmp/navswap-ce22-venue-rebuild-20260719/private/faucet-key.json` | **Expected path missing**; R:`deployments/a666-mainnet-20260727/07-opening-epoch-finalize.ops.json` and route activation operation. |
| NAV reserve submitter, `--reserve` | `pfd0c86d9084915e1fefd22eab891806397d5a5937` | `/home/postfiat/tmp/navswap-ce22-venue-rebuild-20260719/private/reserve-key.json` | **Expected path missing**; R:`deployments/a666-mainnet-20260727/06-opening-reserve-submit.ops.json`. |
| Consensus proposer (separate from ingress proposer) | Elected `validator-N` | `/var/lib/postfiat/validator-N/validator_keys.json` on that validator | R remote-finality helper; remote signer presence/custody not inspected. |

Names-only search of existing local deployment archives found **holder-key.json, holder.json, pfusdc-issuer-key.json, pfusdc-issuer.json, reserve-key.json, reserve.json**. For example, `~/.postfiat/deployments/storage-rollout-d0ae79f3/g6-sources/validator-1/closed-roundtrip/keys/` contains historical copies; filenames alone do not bind them to the accounts above. They were not substituted into the command sheet. No `faucet-key.json` was found in that deployment-archive search. The six September 21 `unprovided-signers/` arguments remain placeholders. The local Arc WORKLOG path provenance is unversioned, SHA-256 `6933b1eca11a09fa31abba656f845a38885162a71ffee2645b9d555ac29980e7`; it is a historical path record, not a fresh remote key check.

## Prover provenance

| Component | Required identity / observed comparison | Verdict |
| --- | --- | --- |
| Historical qualification record | **There is no** R:`deployments/release-repair-20260918/proof-identities.json`. September 18 README follows the September 16 procedure. The retained record is R:`deployments/release-repair-20260916/proof-identities.json`, SHA-256 `fe93ad2594ab6219b971f53ecccbfc59ea13b646b42bc6a5562a58f33c59e065`, introduced in `67aa3ce611d7682d521366dbadb18e3e581d12bd`. | Pins guest reproduction and keys, **not a host-prover executable hash**. |
| Required Arc guest build | R:`programs/pfusdc-egress/releases.json`: `arc-v2-20260902`, source `b945bbb321eb4fdc5a57998fadcf0b353f1acb86`, retained commit `65df4263746566c90d0e46db8c90a46c23576265`; SP1 **6.3.1** Docker build; egress lock SHA-256 `084ce9bd8eb22e4bedf41fb514a2f605a5c4d6b5314e04bf42f23d20b7c159f4`. | Exact historical guest family; do not rebuild from arbitrary current sources. |
| Build environment | Image `ghcr.io/succinctlabs/sp1@sha256:0942a27dbe8e38f4b14f3732e779df4027b17bde93e9fbc9e8c773c15eb63400`; guest source root `/root/program`, Cargo home `/root/.cargo`; CI installs Rust **1.95.0** and SP1 **6.3.1**. | R:`.github/workflows/arc-proof-identities.yml`; historical workflow source `5b1093faad8c78fa7a394b51863e454970815a36`, run [35044347138](https://github.com/postfiatorg/postfiatl1v2/actions/runs/35044347138) recorded in proof identities; not rerun. |
| Ingress | ELF SHA-256 `7660fcc58677cfec433a5f2337b9fe46fa96374a1e3c4bd6fba625b982d881bc`; vkey `0x0050a8b0daed2fa75f44d4102b42204c34668a03d311cb727cc6ca3f8df5cf16`. | R ingress ELF hash matches; the borrowed host binary contains this exact ELF once, byte offset **42696743**. |
| Arc egress | ELF SHA-256 `8b0f266a035a432ef3c0e4233672d8a15b913cefd4c85ff07f91f008601bb744`; vkey `0x0036cbe7d36bbfe1118a3c544eeba74f3791d2a19bf5ec59b972f72d36416852`. Retained file `~/.cache/release-repair-20260916/arc-identity-20260902/pfusdc-egress-program`. | **Retained file matches**. Its vkey matches E's selected verifier. Must pass `--egress-release arc-v2 --elf <retained file>`. |
| Borrowed host prover | `/home/postfiatchad/repos/postfiatl1v2-arcusdc-current/tools/pfusdc-tier4-prover/target/release/pfusdc-tier4-prover`; SHA-256 `1372ad0c0cd5c4364247c7891e17949a6855c08c33757ffddad3219db10334e1`. | **Matches September 21 reference hash; qualified host-build match cannot be established.** The packet supplies no host hash/build receipt. Enclosing checkout HEAD is not binary provenance. |
| Default embedded egress | SHA-256 `0ea4dbabc8a36b44824c861cf2e1ae90454df2a6e4bb8a357f9d3a8672696d83`, pfETH vkey `0x00140f09ca6f1b917e3999a806df5ef4ac4468bd65b85e8580cbc16f832dfe47`. | R default ELF and borrowed binary's embedded ELF match **pfETH**, not Arc (one occurrence, offset **43858759**; Arc ELF absent). This does not invalidate the explicit retained-ELF route; it prevents using the default. |
| NAV prover | Existing legacy key in rows 3/9 versus provider-neutral successor bindings above | Needs the other lane's compatible governed profile, exact prover/guest build and fresh opening/post-subscription proof provenance. Arc guest qualification does not qualify NAV proofs. |

Hash/embedded-byte comparisons completed at **2026-09-22T09:50:48.724549Z**, using file reads, SHA-256 and exact byte comparison only. No prover process or guest execution was started. A matching embedded guest does not attest host build flags, source, proving backend or the future proof. Qualified host provenance and proving capacity remain required.

## Fresh fleet observations

Only `status`, `server_info`, and `mempool_status` were sent as newline-delimited `postfiat-local-rpc-v1` requests through SSH `-W` to each loopback port. Each reported its own distinct validator ID. All six returned **running, height 1020, mempool 0**, chain `postfiat-wan-devnet-2`, protocol 1, and these identical finalized values:

| Common field | Value |
| --- | --- |
| Genesis | `ce22ca8c932da0998b484483a09647138a30e0bf44408dd49a8d6d452787ad25521aff3ed334da07e150a7233a3e90a9` |
| Tip | `9d02b8eecb78408e8f1de12ae1e2607ad4987c2c8d883f1718593df7c2d9ca529f0707bd581e3e414361f202b1768feb` |
| State root | `587c6526a2549c97458b371f42e849c49274a1f522e7dcb841b74cd74bdb3d6747c2e6ca646c08ac51733796d39bead6` |
| RPC runtime binary identity | `57b0f4d1d42d66878d7dbb8c33919c7fa0f87c6cc1a4b9cc1a85d75b634eec83`; build revision `707e006f` |
| Release label | Supplied `a666-source-route-20260907`; consistent with the returned binary identity. No fresh process/executable-file inspection was performed. |

| Validator / SSH host | Loopback RPC | status UTC | server_info UTC | mempool_status UTC |
| --- | --- | --- | --- | --- |
| validator-0 / 64.176.220.75 | 127.0.0.1:27650 | 09:50:51.057441Z | 09:50:58.622460Z | 09:51:00.185014Z |
| validator-1 / 95.179.184.122 | 127.0.0.1:27651 | 09:50:50.441607Z | 09:50:57.415821Z | 09:50:58.063879Z |
| validator-2 / 66.42.48.39 | 127.0.0.1:27652 | 09:50:53.439813Z | 09:51:05.675866Z | 09:51:09.714982Z |
| validator-3 / 149.28.63.106 | 127.0.0.1:27653 | 09:50:51.166838Z | 09:50:59.318057Z | 09:51:00.873976Z |
| validator-4 / 95.179.179.206 | 127.0.0.1:27654 | 09:50:50.190813Z | 09:50:56.534880Z | 09:50:57.144062Z |
| validator-5 / 45.32.110.170 | 127.0.0.1:27655 | 09:50:52.438658Z | 09:51:03.433836Z | 09:51:05.974670Z |

The first validator-0 attempt incorrectly used HTTP framing on the TCP RPC and received parse errors at 09:46:57Z. The documented newline protocol then succeeded; a second bounded capture produced the compact table above. Parse errors were not interpreted as chain/health failures. Health agreement does not supply route/asset/custody snapshots or verified finality certificates. All F state is **re-read after deployment**.

## Arc observations and predecessor binding

Block 63401279 was obtained using only the allowed `eth_call`: `{"data":"0x4360005260206000f3"}` at `latest` returns the EVM NUMBER opcode value. This simulation creates no contract and publishes no transaction. All subsequent calls below used the explicit block tag. The initial urllib request received HTTP 403; curl with its request user agent succeeded. Chain ID 5042002 was the supplied identity, not re-derived.

The selected vault/anchor/verifier addresses are the fixed table above. Getter ABIs were read from R:`crates/ethereum-contracts/src/{ERC20BridgeVaultV2,PfUsdcIngressAnchorV1,PFTLFinalityVerifierV1}.sol`.

| Method / target and getter | Result at block 63401279 | Capture UTC |
| --- | --- | --- |
| `eth_getCode`, anchor | 3,084 bytes; hash in row 1 | 09:49:21.420971Z |
| `eth_getCode`, vault | 5,284 bytes; Keccak `0x8d15bb9dc20c416db72c724eeeb725b8b395cb850a889cde130645dcc752764e` | 09:49:21.552040Z |
| `eth_getCode`, verifier | 11,319 bytes; Keccak `0xf660662865cc6bb1302a5605134bde6bad7922a68482b37e0f2fff84d32a4ba1` | 09:49:21.681597Z |
| `eth_call`, USDC `balanceOf(wallet)` | **20,000,000 atoms** | 09:49:21.834022Z |
| `eth_call`, USDC `balanceOf(vault)` | **1,000,000 atoms** | 09:49:22.022650Z |
| `eth_call`, USDC `allowance(wallet,vault)` | **0 atoms — deposit blocked** | 09:49:22.143510Z |
| `eth_call`, vault `paused()` | false | 09:49:22.259194Z |
| `eth_call`, vault `token()` | `0x3600000000000000000000000000000000000000` | 09:49:22.383891Z |
| `eth_call`, vault `ingressAnchor()` | `0x92390d3a2102cb74e4746c05b4d91f61093475d0` | 09:49:22.502075Z |
| `eth_call`, vault `finalityVerifier()` | `0x1d436908516d15e3c55a936899b47a885e047f27` | 09:49:22.610770Z |
| `eth_call`, vault `owner()` | `0x0995876e5a97c036c0fda8846f8f47b57b6d2bfc` | 09:49:22.738170Z |
| `eth_call`, vault `directIngress()` | true | 09:49:22.845366Z |
| `eth_call`, anchor `governedRouteBinding()` | `0xd9e0cd409c5d1e118d65c78ee059adcbba937616353e9675e350d52ee8d498b2` | 09:49:23.035858Z |
| `eth_call`, verifier `programVKey()` | Arc egress `0x0036cbe7d36bbfe1118a3c544eeba74f3791d2a19bf5ec59b972f72d36416852` | 09:49:23.143770Z |
| `eth_call`, verifier `routeEpoch()` | 9 | 09:49:23.263616Z |
| `eth_getBalance(wallet)` | **20,000,000,000,000,000,000 wei** | 09:49:23.359407Z |
| `eth_call`, verifier `latestFinalizedHeight()` | **948** | 09:51:28.275771Z |
| `eth_call`, verifier `latestCheckpointCommitment()` | `0x2e64ef8e780c00ffb7b94272143f7d03f3655111f806b33e0a9b7e47b7dfa3da` | 09:51:28.388847Z |
| `eth_call`, verifier `latestCommitteeRootCommitment()` | `0xfdc302352eb65ad7e321c677e27dcb0ca56e718c478fe7d2447a7aa59eaeab4b` | 09:51:28.529533Z |
| `eth_call`, verifier `sp1Verifier()` | `0x532d3a8035b87646a92245ecaa01e6602a13654e` | 09:51:28.643363Z |
| `eth_call`, verifier `routeProfileHashCommitment()` | `0x43b718931b64e6087a04346821c4fb9ffa5779fa38436fb335053448825ae1f7` | 09:51:28.750576Z |
| `eth_call`, verifier `vaultRuntimeCodeHash()` | Same vault code hash above | 09:51:28.858067Z |
| `eth_call`, verifier `tokenRuntimeCodeHash()` | `0xc9987bd3af6b26a030951faa7eacc017b68343aeedf3ce5fe68f821c4b93939d` | 09:51:28.988040Z |

`PRIOR_CHECKPOINT` needs a **96-hex PFTL block ID**, not the 32-byte EVM commitment. A:`egress/egress-witness.json#/block/header` supplies height 948 block ID:

`7c0559cf330a78db15dc4f391ea5e8381a6265ac248d043f87f093df54628c8100d06a88bf0422f5ea272d3358400c89`.

`cast keccak 0x7c0559cf330a78db15dc4f391ea5e8381a6265ac248d043f87f093df54628c8100d06a88bf0422f5ea272d3358400c89` returned the exact current checkpoint commitment above. The historical witness's own prior ID `8e3639ee748255636d09adb8b3fe70f20f8ae0aa9388b024eaffb98b7a94f3c7c4b0e5710f0d8c2479b08d9bc8665c4b` is older and is not substituted. The height-948 ID is a **re-read after deployment / before egress** candidate: recheck accepted checkpoint/committee bindings and availability of the finalized ancestry through the new burn. A's whole witness SHA-256 is `e4d5202be88f8411671c9a97228f7f307aa3b2078f96a0806bab673c6fd5975a`.

No `eth_getStorageAt` was needed where the ABI exposed getters. No nonce check was fabricated without a selected nonce/owner. Gas sufficiency for actual submissions, current proof-service/registry witness availability, the SP1 gateway route's qualified policy, and withdrawal/receipt finality remain unestablished. The historical registry/proof packet is not a fresh ingress witness.

## Predecessors, read-backs and monitoring still required

These are additional live prerequisites outside the counted 17 fields. Keep missing artifacts explicit; no checkpoint flags were set true here.

| Required input | Provenance that must supply it | Status |
| --- | --- | --- |
| Qualified deployment, exact checkout and host-prover build | Other lane's signed deployment/qualification receipts, source and executable/guest hashes; fresh all-six runtime identity | needs the other lane; then re-read after deployment |
| Immutable cycle-1 INPUTS / reserve-identities / public VALUES | The reviewed seed plus this inventory, resolved missing bindings, actual start/window and cycle 1; stable paths and SHA-256 | needs the other lane |
| Authoritative validator data and six bound views | Fresh status, primary-route supply, native/source asset, owner balances, vault/source-custody/NAV views at one height/block/root | re-read after deployment |
| Checkpoint projection | Original read-backs, six unique validators, empty queues/pending withdrawal/reservations/entitlement, exact capacities, quote/balances/allowance, recoverable signing and proof validity; captured/expires UTC within 300 s; INPUTS SHA-256 | needs the other lane; refreshed before every row |
| `DEPOSIT_TX` / deposit receipt / finality | Future status-1 deposit, exact deltas and authenticated source finality; then fresh registry witness, proof and public values | future same-cycle predecessor |
| `INGRESS_EXPIRES_HEIGHT`, `ISSUE_HEIGHT`, `ROUTE_HEIGHT`, `REDEEM_HEIGHT` | Fresh finalized eligibility/quote state before those operations, TTL/policy bounds and accepted prior receipts | re-read after deployment and at each stage |
| `REDEEM_OUTPUT_ATOMS`, `WITHDRAWAL_ID` | Actual verified redeem manifest/output, then accepted burn receipt, packet and matching certificate | future same-cycle predecessor |
| `PRIOR_CHECKPOINT` | Height-948 candidate above, accepted checkpoint/committee read-back and exact ancestry available to the qualified node | re-read after deployment / before egress |
| `EGRESS_PUBLIC_VALUES_HEX`, `EGRESS_PROOF_HEX` | Exact new proof files and their qualified verifier report, not September 2 proof bytes | future same-cycle predecessor |
| `SETTLEMENT_OPERATION` | Existing `vault_bridge_redeem_settle` operation from the actual withdrawal observations, released amount and settlement receipt hash; issuer/redemption authority | future same-cycle predecessor; needs the other lane's qualified observations |
| Public packet layout and all original artifacts | Actual stage receipts/certificates, proof reports, quote/balance/custody/route/NAV read-backs, retained attempt records and final reconciliation | future same-cycle predecessor |
| G5 monitoring and live authorization | Confirm aggregate timers below, named monitor and one-cycle G4 authorization; independently authorize any allowance approval | needs the other lane / operator |

The [G5 bounds](../review/z3-g5-failure-rehearsal-20260917.md#latency-bounds-and-pause-thresholds) are still proposals: preflight **300 s**, deposit **180 s**, ingress proof/claim **7200 s**, subscription **300 s**, entitlement release **180 s**, NAV/route **7200 s**, redemption **300 s**, burn/egress **7200 s**, final convergence **300 s**. Measure each aggregate stage from its first command through its final verified artifact; pause on exceeding the bound or any mismatch. The wrapper's **7200 s per-command timeout does not implement these aggregate monitors**.

After deployment and authorization, the runbook's exact state-read command forms are below. Supply each validator's authoritative data source; the paths were not opened or created in this collection. Every output must be tied to its validator's finalized height/block/root. Use the fixed route/native/source/family IDs from the identity table.

~~~bash
"$NODE" status --data-dir "$VALIDATOR_DATA_DIR"
"$NODE" navcoin-bridge-supply-status --data-dir "$VALIDATOR_DATA_DIR" --route-id pftl-a666-ethereum-wA666-usdc-v1
"$NODE" asset-info --data-dir "$VALIDATOR_DATA_DIR" --asset-id 521c6c630bb48d4a37ab4a7bd4900dd2caa2d9e99499e452da3c7ce75b3d74b62d20e18555642bec32174498cbee5e2c
"$NODE" asset-info --data-dir "$VALIDATOR_DATA_DIR" --asset-id 3923511d5be0557a61051e099b606d3decc11a5ba274c7d551168735accad8ed18d89c9200efc4bfbbbab6e85d4c173f
"$NODE" account-assets --data-dir "$VALIDATOR_DATA_DIR" --account @MANIFEST_ACCOUNTS_OWNER@
"$NODE" vault-bridge-status --data-dir "$VALIDATOR_DATA_DIR" --asset-id 02c46a36eb0da3516b4d8affea8f4028ad3f36825a3e8f0e009ea9dbbbcfb3c233f6830bd5221fe2717fb6a1a7005d7b
~~~

Use E's same getter/method list with a **new pinned Arc block**, including code/proof/checkpoint bindings, wallet/vault balances and allowance. For the chosen nonce, query the exact computed deposit ID on both deposit guards. Existing allowance is zero: the runbook requires a separately authorized pre-cycle approval, its status-1 receipt, new allowance read-back and a new gas baseline. No approval command was executed here.

## Ordered live command sheet — blocked, not executed

**Lineage note, 2026-09-28.** The lineage decided on 2026-09-23 (source `1a0989ad`, executable `e7bb1afa…`, prepared as `combined-devnet-20260923`) was never deployed. Until today this sheet kept the paths of the earlier prepared release `combined-devnet-20260921` and the `051ad12c…` node. Both were superseded by the deployments of 2026-09-25 (`combined-fastpay-20260925`, `f60e9639`) and 2026-09-28 (`combined-fastpay-20260928`, source `c93b2137`, executable `1f8b332d…`). The sheet now names the 2026-09-28 release: `NODE` and every `--remote-binary` / `--remote-topology`. The decided Arc pair, cap and route are unchanged.

This is a review copy of the already-retained 39 commands, with recovered values filled, fresh output-directory names and the unresolved placeholders listed below. It does not rerun the dry-run harness, qualify a build, create INPUTS or authorize execution.

Use the [runbook's](../runbooks/z3-cycle-dry-run.md#readbacks-and-the-stop-before-every-step) `next_step` and **one** `confirm_step NAME` at a time after a fresh checkpoint and explicit review. The code blocks below describe the underlying argv for each named confirmation; **do not execute them as a batch or bypass the wrapper**. In particular, its remote-finality helper signs and writes remote state, which was outside this collection's scope.

Command aliases (fixed reference paths remain subject to the qualification blocker):

~~~bash
TOOLING=/home/postfiatchad/repos/postfiatl1v2
NODE=/home/postfiatchad/.cache/release-repair-20260928/binaries/candidate-1
PROVER=/home/postfiatchad/repos/postfiatl1v2-arcusdc-current/tools/pfusdc-tier4-prover/target/release/pfusdc-tier4-prover
EGRESS_ELF=/home/postfiatchad/.cache/release-repair-20260916/arc-identity-20260902/pfusdc-egress-program
WORK=/home/postfiatchad/.cache/z3-cycle1-20260922/work
PACKET=/home/postfiatchad/.cache/z3-cycle1-20260922/packet
INPUTS=/home/postfiatchad/.cache/z3-cycle1-20260922/inputs-reviewed.json
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$TOOLING/python"
~~~

INPUTS is a **future path**, not the September 21 seed. Its `manifest.source_commit` must match the running lineage checkout (`c93b2137`); its release/binary must match the actual deployment (`combined-fastpay-20260928`, `1f8b332d…`). The six PFTL signer arguments remain `@SIGNER_HOLDER@`, `@SIGNER_PROPOSER@`, `@SIGNER_FINALIZER@`, `@SIGNER_ISSUER@`, `@SIGNER_RESERVE@`, `@SIGNER_SETTLER@` until custody is bound. `@VALIDATOR_DATA_DIR@` requires the authoritative data source. `@CHECKPOINT@` and all future VALUES names are defined in the predecessor table. Other `@MANIFEST_*@`, `@PATHS_*@` and `@PARAMETERS_*@` names map exactly to unresolved rows in the 17-field table.

The historical height-948 `PRIOR_CHECKPOINT` candidate is filled below to make the required **96-hex** format reviewable; replace it if the fresh accepted checkpoint/ancestry evidence requires a different value. Native quote remains a placeholder because the historical ceiling is not a live quote.

**1. `confirm_step preflight` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py check-preflight \
  --inputs "$INPUTS" \
  --checkpoint @CHECKPOINT@
~~~

**2. `confirm_step arc-deposit` — SUBMIT**

~~~bash
cast send 0x160307f3efead79b6a3629c4b8d90e8301fc250f 'depositV2(uint256,string,bytes32,bytes32)' 2000000 @MANIFEST_ACCOUNTS_OWNER@ @PARAMETERS_DEPOSIT_NONCE@ 0xd9e0cd409c5d1e118d65c78ee059adcbba937616353e9675e350d52ee8d498b2 \
  --rpc-url https://rpc.testnet.arc.network \
  --chain 5042002 \
  --from 0xC75Bf05Ce82d6f4b6139dd9446D6De5F5994a4CB \
  --keystore /home/postfiatchad/.foundry/keystores/arc-testnet-server \
  --password-file /home/postfiatchad/.postfiat/arc-testnet-server.password \
  --json
~~~

**3. `confirm_step ingress-capture` — prepare / verify**

~~~bash
"$PROVER" arc-ingress-capture \
  --rpc https://rpc.testnet.arc.network \
  --deposit-tx @DEPOSIT_TX@ \
  --route-id 0xd9e0cd409c5d1e118d65c78ee059adcbba937616353e9675e350d52ee8d498b2 \
  --vault 0x160307f3efead79b6a3629c4b8d90e8301fc250f \
  --token 0x3600000000000000000000000000000000000000 \
  --output "$WORK"/ingress-witness.json
~~~

**4. `confirm_step ingress-proof` — prepare / verify**

~~~bash
"$PROVER" arc-ingress \
  --witness "$WORK"/ingress-witness.json \
  --output-dir "$WORK"/ingress-proof \
  --prove
~~~

**5. `confirm_step ingress-bundle` — prepare / verify**

~~~bash
"$NODE" vault-bridge-deposit-relay-bundle \
  --receipt-file "$WORK"/arc-deposit.stdout.json \
  --vault-address 0x160307f3efead79b6a3629c4b8d90e8301fc250f \
  --token-address 0x3600000000000000000000000000000000000000 \
  --asset-id 02c46a36eb0da3516b4d8affea8f4028ad3f36825a3e8f0e009ea9dbbbcfb3c233f6830bd5221fe2717fb6a1a7005d7b \
  --policy-hash f7ce6d3cce3bd058a218db6bd829b01be13c576a2270aed362052d12654fc7a911a8423ee2d961ca45dbf72c08df6ae2 \
  --route-epoch 9 \
  --proposer pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8 \
  --finalizer pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8 \
  --claimer @MANIFEST_ACCOUNTS_OWNER@ \
  --expires-at-height @INGRESS_EXPIRES_HEIGHT@ \
  --source-proof-kind sp1-arc-finality-v1 \
  --source-proof-file "$WORK"/ingress-proof/proof-calldata.bin \
  --source-public-values-file "$WORK"/ingress-proof/public-values.bin \
  --bundle "$WORK"/relay
~~~

**6. `confirm_step prepare-propose` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py wrap-operation \
  --operation "$WORK"/relay/propose.operation.json \
  --source pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8 \
  --signer-path @SIGNER_PROPOSER@ \
  --output "$WORK"/propose.ops.json
~~~

**7. `confirm_step ingress-propose` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/propose.ops.json \
  --artifact-dir "$WORK"/finality/ingress-propose \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**8. `confirm_step prepare-finalize` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py wrap-operation \
  --operation "$WORK"/relay/finalize.operation.json \
  --source pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8 \
  --signer-path @SIGNER_FINALIZER@ \
  --output "$WORK"/finalize.ops.json
~~~

**9. `confirm_step ingress-finalize` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/finalize.ops.json \
  --artifact-dir "$WORK"/finality/ingress-finalize \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**10. `confirm_step prepare-claim` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py wrap-operation \
  --operation "$WORK"/relay/claim.operation.json \
  --source @MANIFEST_ACCOUNTS_OWNER@ \
  --signer-path @SIGNER_HOLDER@ \
  --output "$WORK"/claim.ops.json
~~~

**11. `confirm_step ingress-claim` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/claim.ops.json \
  --artifact-dir "$WORK"/finality/ingress-claim \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**12. `confirm_step prepare-subscription` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-pfusdc-reserve-demo.py build-issue \
  --identities "$WORK"/reserve-identities.json \
  --route-status "$WORK"/before-issue.route.json \
  --nav-manifest @PATHS_OPENING_NAV_MANIFEST@ \
  --subscriber @MANIFEST_ACCOUNTS_OWNER@ \
  --ethereum-recipient @PARAMETERS_RESERVATION_RECIPIENT@ \
  --holder-key-file @SIGNER_HOLDER@ \
  --mint-amount-atoms @PARAMETERS_MINT_AMOUNT_ATOMS@ \
  --current-height @ISSUE_HEIGHT@ \
  --reservation-ttl-blocks 128 \
  --output-dir "$WORK"/issue
~~~

**13. `confirm_step reserve` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/issue/01-reserve.ops.json \
  --artifact-dir "$WORK"/finality/reserve \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**14. `confirm_step subscribe` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/issue/02-subscribe.ops.json \
  --artifact-dir "$WORK"/finality/subscribe \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**15. `confirm_step entitlement-release` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/issue/03-release-entitlement.ops.json \
  --artifact-dir "$WORK"/finality/entitlement-release \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**16. `confirm_step verify-subscription` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-pfusdc-reserve-demo.py verify-issue \
  --issue-manifest "$WORK"/issue/issue-manifest.json \
  --output "$WORK"/issue-verify.json \
  --before-route "$WORK"/before-issue.route.json \
  --before-pfusdc "$WORK"/before-issue.pfusdc.json \
  --before-a666 "$WORK"/before-issue.a666.json \
  --after-subscribe-route "$WORK"/after-subscribe.route.json \
  --after-subscribe-pfusdc "$WORK"/after-subscribe.pfusdc.json \
  --after-subscribe-a666 "$WORK"/after-subscribe.a666.json \
  --after-release-route "$WORK"/after-release.route.json \
  --after-release-pfusdc "$WORK"/after-release.pfusdc.json \
  --after-release-a666 "$WORK"/after-release.a666.json
~~~

**17. `confirm_step prepare-nav` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-build-live-nav-mark-ops.py \
  --packet-operation @PATHS_FRESH_PACKET_OPERATION@ \
  --pftl-status "$WORK"/after-release.pftl-status.json \
  --issuer-key-file @SIGNER_ISSUER@ \
  --reserve-key-file @SIGNER_RESERVE@ \
  --output-dir "$WORK"/nav
~~~

**18. `confirm_step nav-submit` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/nav/01-reserve-submit.ops.json \
  --artifact-dir "$WORK"/finality/nav-submit \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**19. `confirm_step nav-finalize` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/nav/02-epoch-finalize.ops.json \
  --artifact-dir "$WORK"/finality/nav-finalize \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**20. `confirm_step prepare-route-pause` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py route-switch \
  --route pftl-a666-ethereum-wA666-usdc-v1 \
  --operator pffcb93d9f87a843a8aa34e1adf241f5d58143e81b \
  --paused true \
  --signer-path @SIGNER_ISSUER@ \
  --output "$WORK"/route-pause.ops.json
~~~

**21. `confirm_step route-pause` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/route-pause.ops.json \
  --artifact-dir "$WORK"/finality/route-pause \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**22. `confirm_step prepare-route-epoch` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-build-route-epoch-advance.py \
  --route-status "$WORK"/paused.route.json \
  --nav-manifest "$WORK"/nav/live-nav-mark-manifest.json \
  --identities "$WORK"/reserve-identities.json \
  --operator pffcb93d9f87a843a8aa34e1adf241f5d58143e81b \
  --issuer-key-file @SIGNER_ISSUER@ \
  --valid-from-height @ROUTE_HEIGHT@ \
  --output-dir "$WORK"/route-epoch
~~~

**23. `confirm_step route-advance` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/route-epoch/route-epoch-advance.ops.json \
  --artifact-dir "$WORK"/finality/route-advance \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**24. `confirm_step prepare-route-resume` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py route-switch \
  --route pftl-a666-ethereum-wA666-usdc-v1 \
  --operator pffcb93d9f87a843a8aa34e1adf241f5d58143e81b \
  --paused false \
  --signer-path @SIGNER_ISSUER@ \
  --output "$WORK"/route-resume.ops.json
~~~

**25. `confirm_step route-resume` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/route-resume.ops.json \
  --artifact-dir "$WORK"/finality/route-resume \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**26. `confirm_step prepare-redemption` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-pfusdc-reserve-demo.py build-redeem \
  --identities "$WORK"/reserve-identities.json \
  --route-status "$WORK"/before-redeem.route.json \
  --nav-manifest "$WORK"/nav/live-nav-mark-manifest.json \
  --issue-manifest "$WORK"/issue/issue-manifest.json \
  --holder-key-file @SIGNER_HOLDER@ \
  --owner @MANIFEST_ACCOUNTS_OWNER@ \
  --current-height @REDEEM_HEIGHT@ \
  --output-dir "$WORK"/redeem
~~~

**27. `confirm_step redeem` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/redeem/primary-redeem.ops.json \
  --artifact-dir "$WORK"/finality/redeem \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**28. `confirm_step verify-redemption` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-pfusdc-reserve-demo.py verify-redeem \
  --redeem-manifest "$WORK"/redeem/redeem-manifest.json \
  --output "$WORK"/redeem-verify.json \
  --before-route "$WORK"/before-redeem.route.json \
  --before-pfusdc "$WORK"/before-redeem.pfusdc.json \
  --before-a666 "$WORK"/before-redeem.a666.json \
  --after-route "$WORK"/after-redeem.route.json \
  --after-pfusdc "$WORK"/after-redeem.pfusdc.json \
  --after-a666 "$WORK"/after-redeem.a666.json
~~~

**29. `confirm_step burn-bundle` — prepare / verify**

~~~bash
"$NODE" vault-bridge-burn-to-redeem-bundle \
  --data-dir @VALIDATOR_DATA_DIR@ \
  --owner @MANIFEST_ACCOUNTS_OWNER@ \
  --asset-id 02c46a36eb0da3516b4d8affea8f4028ad3f36825a3e8f0e009ea9dbbbcfb3c233f6830bd5221fe2717fb6a1a7005d7b \
  --bucket-id fcc209605f8cfda895acbf78047f83f97b0bc1cee3927582fb262efb46e7d136b098183d5f83e19a82d34c218bab67a7 \
  --amount-atoms @REDEEM_OUTPUT_ATOMS@ \
  --destination-ref evm-erc20:5042002:0xc75bf05ce82d6f4b6139dd9446d6de5f5994a4cb \
  --bundle "$WORK"/burn
~~~

**30. `confirm_step prepare-burn` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py wrap-operation \
  --operation "$WORK"/burn/burn-to-redeem.operation.json \
  --source @MANIFEST_ACCOUNTS_OWNER@ \
  --signer-path @SIGNER_HOLDER@ \
  --output "$WORK"/burn.ops.json
~~~

**31. `confirm_step burn` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/burn.ops.json \
  --artifact-dir "$WORK"/finality/burn \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**32. `confirm_step egress-witness` — prepare / verify**

~~~bash
"$NODE" pfusdc-egress-witness \
  --data-dir @VALIDATOR_DATA_DIR@ \
  --withdrawal-id @WITHDRAWAL_ID@ \
  --prior-checkpoint 7c0559cf330a78db15dc4f391ea5e8381a6265ac248d043f87f093df54628c8100d06a88bf0422f5ea272d3358400c89
~~~

**33. `confirm_step egress-proof` — prepare / verify**

~~~bash
"$PROVER" egress \
  --egress-release arc-v2 \
  --elf "$EGRESS_ELF" \
  --witness "$WORK"/egress-witness.stdout.json \
  --output-dir "$WORK"/egress-proof \
  --prove
~~~

**34. `confirm_step arc-release` — SUBMIT**

~~~bash
cast send 0x160307f3efead79b6a3629c4b8d90e8301fc250f 'withdrawWithProof(bytes,bytes)' @EGRESS_PUBLIC_VALUES_HEX@ @EGRESS_PROOF_HEX@ \
  --rpc-url https://rpc.testnet.arc.network \
  --chain 5042002 \
  --from 0xC75Bf05Ce82d6f4b6139dd9446D6De5F5994a4CB \
  --keystore /home/postfiatchad/.foundry/keystores/arc-testnet-server \
  --password-file /home/postfiatchad/.postfiat/arc-testnet-server.password \
  --json
~~~

**35. `confirm_step release-replay-check` — read-only replay check**

~~~bash
cast call 0x160307f3efead79b6a3629c4b8d90e8301fc250f 'withdrawWithProof(bytes,bytes)' @EGRESS_PUBLIC_VALUES_HEX@ @EGRESS_PROOF_HEX@ \
  --rpc-url https://rpc.testnet.arc.network \
  --from 0xC75Bf05Ce82d6f4b6139dd9446D6De5F5994a4CB
~~~

**36. `confirm_step prepare-egress-settlement` — prepare / verify**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/z3-cycle-dry-run.py wrap-operation \
  --operation @SETTLEMENT_OPERATION@ \
  --source pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8 \
  --signer-path @SIGNER_SETTLER@ \
  --output "$WORK"/settle.ops.json
~~~

**37. `confirm_step egress-settle` — SUBMIT**

~~~bash
/usr/bin/python3 "$TOOLING"/scripts/a666-ce22-remote-finality-op.py \
  --ops-file "$WORK"/settle.ops.json \
  --artifact-dir "$WORK"/finality/egress-settle \
  --node-bin "$NODE" \
  --remote-runner "$TOOLING"/scripts/a666-remote-sync-round.py \
  --proposer-hosts-file @PATHS_PROPOSER_HOSTS_FILE@ \
  --remote-binary /opt/postfiat/releases/combined-fastpay-20260928/postfiat-node \
  --remote-topology /etc/postfiat/releases/combined-fastpay-20260928/topology.json \
  --timeout-seconds 7200
~~~

**38. `confirm_step seal-packet` — prepare / verify**

~~~bash
/usr/bin/python3 -m postfiat_rpc.z3_cycle build \
  --layout "$PACKET"/layout.json \
  --output "$PACKET"/cycle.json
~~~

**39. `confirm_step final-convergence` — prepare / verify**

~~~bash
/usr/bin/python3 -m postfiat_rpc.z3_cycle verify "$PACKET"/cycle.json
~~~

## Publication and stop record

Only this status document and its one-line G4 link are intended for the commit. No gate checkbox is ticked and no milestone is closed. The temporary release worktree is removed after publication.

| Documentation publication gate | Result |
| --- | --- |
| `.venv-docs/bin/mkdocs build --strict` | PASS, exit 0; documentation built in 4.07 s |
| `PATH="$PWD/.venv-docs/bin:$PATH" scripts/public-doc-links` | PASS, exit 0; `public_documentation_links=ok files=416` |
| `scripts/public-secret-scan` | PASS, exit 0; `public secret scan passed mode=tracked-tree` |

No Rust, workspace, Orchard/Halo2, proof-generation or live-cycle test is appropriate to this documentation-only collection. The source/proof mismatch, absent signer bindings, zero allowance, deployment blocker and future artifacts remain explicit. Task Node receives the pushed commit and actual gate output as evidence; its final outcome is read back separately. Collection stops here.
