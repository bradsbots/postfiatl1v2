# Exchange-readiness merge review — 2026-10-23

Correctness review of the integrated source on `main` before the next release cut. Revision `5b2efe9d` (merge of #146). Its `crates/` tree is identical to `124a187b` (#145); #146 changed docs only. Diff reviewed: `git diff 86706699..5b2efe9d -- crates/` (56 files, +6576/−305), against the deployed `store-handle-20261021` source `86706699`. Scope: the #143/#144 composition, admission, activation, replay and the reserve identity consumers ([handoff](../handoffs/2026-10-23___codex__chain_pr_merge_handoff.md), step 1). Repository and work server only. No validator host, live RPC or transaction was touched.

## Verdict: CUT

The source is safe to cut, qualify and install today with all three activation heights left unset. The governance record comes later.

- Before activation, receipts, ledger bytes and state commitments are unchanged on every execution path (R2).
- No consensus or state result changes without an activation gate (R7).
- The admission change that ships with the binary refuses none of the addresses the devnet uses (R3).
- Older binaries reject the new amendment kinds and the new transaction variants. Do the full six-node rollout first, then the governance records (R1).

The findings below are Low or informational. None blocks the cut. XR-01 and XR-02 were fixed on main before the cut (2026-10-23). These release gates remain: the exact height-924 and current-head archive replays of the release binary, `official-mainnet-fork` on the release revision, then `account-tx-index-build` on every node after install.

## Findings

Every finding below has the same four parts: condition, observed, expected, suggested change.

### XR-01. Low — Orchard deposit sink is not a canonical address (latent) — [x] done

- **Condition:** An Orchard deposit's funding transfer must target `FEE_COLLECTOR_ADDRESS` (`crates/node/src/orchard_state_application.rs:418`). The builder signs that transfer (`crates/node/src/orchard_policy_actions.rs:812-819`).
- **Observed:** `FEE_COLLECTOR_ADDRESS` is `pffee0…0`, 41 characters (`crates/execution/src/entrypoints.rs:151`), so `validate_canonical_address` refuses it. It still works for two reasons. The funding transfer runs through plain `execute_transfer` inside the shielded batch, live and in replay (`orchard_state_application.rs:747`). The RPC/mempool check covers only the `mempool_submit_signed_*` methods (`crates/node/src/atomic_swap_rpc_server.rs:14-50`). No Orchard deposit flow uses those methods, and the node's `build_signed_transfer` has no address check (`crates/node/src/storage_commit.rs:812`).
- **Expected:** Orchard deposits work the same before and after `recipient_format_activation_height`.
- **Suggested change:** No change before the release. Add a comment at `orchard_state_application.rs:747` and a regression test saying that the funding transfer must stay outside the governed recipient wrappers. Routing it through `execute_transfer_with_compatibility` would make every Orchard deposit fail after activation. A canonical sink would need its own gated migration.
- **Done 2026-10-23:** comments at `orchard_state_application.rs:418,751`; pin test `orchard_deposit_funding_transfer_stays_on_plain_execute_transfer` (`crates/node/src/tests/recipient_format_activation.rs`).

### XR-02. Low — `verify_mempool` totals omit `issued_payment_v2` — [x] done

- **Condition:** `asset_transaction_amount` (`crates/node/src/mempool_proposals.rs:2473-2480`) feeds the mempool verification `total_amount` (`:1833`).
- **Observed:** The function matches `IssuedPayment`, `AssetBurn` and `AssetClawback`. `IssuedPaymentV2` falls to `_ => 0`.
- **Expected:** A pending `issued_payment_v2` counts like `issued_payment`.
- **Suggested change:** Add `AssetTransactionOperation::IssuedPaymentV2(operation) => operation.amount`. This is a read-only report, so it is not a consensus change and it can ride the next release. Every other `IssuedPayment` match handles V2: execution, recipient fields, history, `certified_asset_ops` and the source check.
- **Done 2026-10-23:** the arm is added; the test `verify_mempool_amount_counts_issued_payment_v2_like_issued_payment` (`mempool_proposals.rs`) failed before it and passes after.

### XR-03. Info — the three gates follow different postponement rules

- **Condition:** `rejected_tx_fee_activation_height()` and `require_memo_activation_height()` take the latest amendment (`crates/types/src/shielded_bridge_governance.rs:1550-1564`). `recipient_format_activation_height()` takes the earliest unpaused amendment (`:1601-1610`).
- **Observed:** Once activated, fee claims and require-memo can be switched off again by a later amendment with a higher value; the rule is then inactive until that height. The recipient rule cannot be postponed. Every new value must be above the block that applies it (`crates/node/src/execution_actions.rs:1954-1988`), and a paused amendment is refused (`:1999`). Replay applies governance in block order (`crates/node/src/block_replay_wallet.rs:2990-3020`), so both rules stay deterministic.
- **Expected:** Operators know which activation is irreversible.
- **Suggested change:** No code change. The runbook should say that the recipient-format height cannot be undone and the other two can be re-scheduled. The activation steps below follow that.

### XR-04. Info — older binaries reject the new kinds and variants (rollout order confirmed)

- **Condition:** The three new amendment kinds, plus the `account_set` and `issued_payment_v2` asset operations.
- **Observed:** At `86706699`, `validate_amendment_kind` ends in `unsupported governance amendment kind` (`crates/consensus_cobalt/src/internal_validation.rs:1781` at that revision). The asset-operation decoder ends in `unknown asset operation` (`crates/types/src/transactions_mempool_receipts.rs:3804` at that revision). An old node therefore refuses the RPC submission and cannot apply a block that contains either. On the new binary these are allowed (`internal_validation.rs:1773-1777`, `transactions_mempool_receipts.rs:3785-3789`). Before `require_memo_activation_height`, the new execution returns `account_set_not_active` / `issued_payment_v2_not_active` (`crates/execution/src/nft_escrow_asset_execution.rs:1086,1109`). Those codes are excluded from fee claims (`crates/execution/src/rejected_fee_claim.rs:30-37`). The mempool dry run refuses both variants (`mempool_proposals.rs:636-651`), so an honest proposer never includes them in a mixed fleet.
- **Expected:** The handoff says older binaries reject them. Confirmed.
- **Suggested change:** None. Do the full six-node rollout before any of the three governance records. After that, wait for require-memo activation before submitting `account_set` or `issued_payment_v2`; before it, the mempool refuses them anyway.

### XR-05. Info — `account_tx` falls back to archive scan until the v2 index is built

- **Condition:** Index schema v2 (`crates/node/src/block_finality.rs:221-228`).
- **Observed:** A v1 index fails `account_tx_index_matches_domain` (`:2382-2387`). Reads fall back to `account_tx_scan` (`:213-216`), and commit-time extension skips the v1 index (`:311-326`). Neither stops a commit or changes consensus.
- **Expected:** Results are correct right after install. Speed returns after the rebuild.
- **Suggested change:** None. Run `account-tx-index-build` then `account-tx-index-status` on every node after install (handoff step 4).

## Review answers

### R1. #143/#144 composition

- **Recipient rule:** `recipient_format.rs:13-94` lists the destination fields: transfer and payment `to`; issued payment, `issued_payment_v2` (`:31-33`, added in `1ebc0faf`), NAV mint, vault-bridge mint, claim and NAV allocation; PFTL-Uniswap settlement and return recipients; escrow recipient; NFT owner and `to`. Ethereum recipients and debited `owner` fields are deliberately not checked. Atomic-swap legs already require `pf` plus 40 lowercase hex in envelope validation (`crates/types/src/transactions_validation_helpers.rs:433-437`). `destination_address_rejection` (`:96-114`) returns the first failing field with a fixed receipt code.
- **Execution entrypoints:** the transfer, `payment_v2` and asset paths check the address only when `recipient_format_active(height)` (`crates/execution/src/entrypoints.rs:193-199,500-506,941-947`); escrow and NFT do the same (`recipient_format.rs:144-151,162-169`). The memo rule is a no-op until `require_memo_active` (`rejected_fee_claim.rs:48-67`).
- **Node batch:** the live batch (`execution_actions.rs:66-203`) and the archive batch (`:552-705`) send every transfer, `payment_v2`, asset, atomic-swap, escrow, NFT and offer receipt through `claim_rejected_*_fee` with the same compatibility (`:466-472`). FastLane primary, shielded and bridge batches are not fee-claimed, in either path.
- **Fee claim:** only for a rejected receipt at or above the fee height, with a claimable code (`rejected_fee_claim.rs:97-104`). It then re-checks the envelope, chain domain, ML-DSA signature, key-to-address match, bound key, exact next sequence, minimum fee and reserve (`:107-147`). It burns only the declared fee, consumes the sequence and adds the `tec_` prefix to the code (`:149-190`). A malformed recipient after both gates gives `tec_invalid_recipient_address`, `tec_invalid_recipient_checksum` or `tec_noncanonical_recipient_address`, with no amount moved. Test: `recipient_failures_claim_fees_with_both_gates_and_replay_identically`.
- **Require-memo and `issued_payment_v2`:** account `flags` bit `0x1` (`crates/types/src/account_owned_asset_types.rs:17,412`). `account_set` changes only the signer's own flags. `issued_payment_v2` is `issued_payment` plus signed memos, with recipient validation and the memo rule (`nft_escrow_asset_execution.rs:1077-1121`).
- **Activation heights:** governance amendments with kinds `rejected_tx_fee_activation_height`, `require_memo_activation_height` and `recipient_format_activation_height` (`shielded_bridge_governance.rs:40-56`). None of them is stored as a governance field; each lives only in the ordered amendment log. With no amendment the getter returns `None`, so the rule is inactive. The node reads them into `AssetExecutionCompatibility` (`execution_actions.rs:480-501,466-472`). A record sets them through the `ratify-*-activation-height` CLI (`crates/node/src/main_parts/cli_dispatch_parts/group_03.rs:1878-1908`). Older binaries reject them (XR-04).

### R2. Behaviour before activation is byte-identical

- **Code:** each gate is `Option::is_some_and(height >= h)` (`nft_escrow_asset_execution.rs:851-879`), so it is false while unset. Apart from the gated branches, `execute_transfer` and `execute_payment_v2` are unchanged (`entrypoints.rs` diff). The batch wrappers return the receipt unchanged when the fee gate is off. Zero `flags` are omitted from ledger JSON (`skip_serializing_if`) and from the state commitment (`crates/node/src/state_commitment.rs:1964-1969`). The new kinds add no governance field. `TxFinalityReport.transaction_rows` is skipped when empty, and transport always sends it empty (`crates/node/src/transport_protocol.rs:1683`).
- **Tests:**
  - `transparent_batch_claims_rejected_fees_only_from_the_governed_height` checks the bytes of the live and replayed receipts. With no amendment, and one block below activation, they equal the pre-change `execute_transfer`/`execute_payment_v2` output and the ledger is unchanged.
  - `recipient_format_rule_gates_live_execution_and_archive_replay_identically` and `zero_account_flags_preserve_legacy_bytes_and_set_flags_are_committed` cover the other two gates.
  - The governance tests check that legacy governance JSON leaves out the new kinds.
- **Limit:** these tests compare the new binary with itself. The exact height-924 and current-head archive replays are the cross-binary proof, and they remain the release gate.

### R3. The admission change and the devnet's addresses

"Malformed" here means the RPC and mempool refuse any destination field that is not exactly `pf` plus 40 lowercase hex characters:

- not 42 characters;
- a `PF`/`Pf`/`pF` prefix, or no prefix;
- non-ASCII or non-hex characters;
- any uppercase hex. A valid mixed-case checksum is refused as `noncanonical_recipient_address`; a wrong one as `invalid_recipient_checksum`.

Sources: `crates/crypto_provider/src/address.rs:122-146,179-205`; `mempool_proposals.rs:178-188` (all five `admit_*`); `atomic_swap_rpc_server.rs:4-62`, which runs before the mempool lock. The check applies from install, with no activation needed.

Each address below was checked with that rule and with the Python `postfiat_rpc.address.is_canonical_address`. The two agreed.

| Address role | Address | Result |
| --- | --- | --- |
| Faucet account (StakeHub `pft faucet` signer) | `pfcd4cc8c354bd340fe18386e6f875ff68f215a95c` | pass |
| `testing` wallet | `pf6395ef7f43ffaa74ce178d320b9bbbfd45532b38` | pass |
| validator-0 (from its registry key) | `pfc504592b3284f61e7e7d943a57ccef018a7c53b1` | pass |
| validator-1 | `pf1686766d7cef7da65faebb1af9702e4dbaff5a4a` | pass |
| validator-2 | `pf497f856cdff0df77c373312025b54675c374ba34` | pass |
| validator-3 | `pf8e10128be2e2e178d2188b5b1d2c8fc912ef7454` | pass |
| validator-4 | `pf9ab2e494f3bad7278f37963517a8452cd8e1d2c2` | pass |
| validator-5 | `pf12aecac06302863cd467568cd3551a491d72978d` | pass |
| A666 issuer; genesis faucet account | `pffcb93d9f87a843a8aa34e1adf241f5d58143e81b` | pass |
| BMNRC issuer | `pf9bd7958a0779f4de39e871878bbd6552dc461c3f` | pass |
| pfUSDC account | `pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8` | pass |
| A666 reserve submitter | `pfd0c86d9084915e1fefd22eab891806397d5a5937` | pass |
| BMNRC reserve operator | `pf7143fef04a76dc4cc2c65d74892dcd4d44876d11` | pass |
| A666 route wallet and subscriber | `pfab9b9228942e5c529633a13aa271d5297bec6353` | pass |
| A666 route account | `pf2ddefa436ad1ccc40b61e26409b334ace71b9fb2` | pass |
| BMNRC route source wallet | `pf4b26feb8adcbd048eaa260fca6043aff7336985c` | pass |
| BMNRC return-import recipient | `pff5e2908c40b648301c96862dc0d620990504d137` | pass |
| Release manifest publisher | `pfc531e00ffefecb8fabe40c6f47c69148df31e49c` | pass |
| StakeHub venue wallet (`venue-nav-20260721`) | Not on this server. It is derived from a key, so it has the canonical form. Any ledger account is in the row below. | pass |
| All 58 ledger accounts, and all 646 destination values (58 distinct) in the archived transactions through height 1123 | signed canary import of `store-handle-20261021` | 58/58 and 646/646 pass |
| Sink `FEE_COLLECTOR_ADDRESS` (never a mempool destination; XR-01) | `pffee0…0` (41 characters) | refused, no effect |

Blocks 1124–1137 add only faucet grants to `testing` and the FastLane `AnchorCheckpoint`/`ActivateCommittee`, which have no destination fields. Every `pf` literal in `scripts/`, `python/postfiat_rpc/`, `ops/` and StakeHub `pft_wallet/` is canonical; StakeHub passes it lowercase. **No address the devnet uses today is refused.**

### R4. Archive and replay paths

The archive replay keeps a mutable `GovernanceState` and applies each governance batch in block order before later blocks run (`block_replay_wallet.rs:2962-3020`). Every gate is therefore read as it stood at that block. This is the sequential governance replay the handoff examined; it found no bug, and neither does this review. Transparent replay builds its compatibility the same way as live execution and uses the same claim wrappers (`execution_actions.rs:572-576`). Asset replay builds its compatibility with `asset_execution_compatibility_with_chain_activation`, which carries both the recipient and memo heights (`:742-860`). The fee height is read in one place only, `rejected_fee_claim.rs:101`, so live and replay cannot differ on it. The `live_and_replayed` test helper compares receipts byte for byte and checks ledger equality and native supply conservation (`crates/node/src/tests/rejected_fee_require_memo.rs:147-193`).

### R5. Reserve identity consumers

- The consumers now pin profile `bfb599f2…`, vkey `0x00d28f47…` and source manifest `122a4327…`: `scripts/a666-build-nav-profile-rotation-ops.py`, `scripts/a666-build-route-epoch-advance.py` and `crates/node/tests/atomic_swap_local_six.rs:1445,1451,2960`.
- Those values equal `tools/nav-reserve-proof/qualifications/freshness-and-debt-20260924/candidate-identity.json`. That file records `candidate_not_registered`, source `16d41b5d` (an ancestor of main), ELF `b64b7666…`, built twice with byte-identical output.
- `git log 86706699..main` shows no commit touching `program-identity.json` (legacy ELF `0f847643…`), `a666-successor-program-identity.json` (vkey `0x00f3857f…`) or `elf/`. The old successor values remain only in historical qualification evidence and docs.
- Confirmed.

### R6. `consensus_cobalt` and `crypto_provider`

- **`consensus_cobalt`:** `core_types.rs` imports the three kinds. `internal_validation.rs:1773-1777` allows them in `validate_amendment_kind`, and a value of 0 is still refused. `tests.rs` adds `ratifies_recipient_fee_and_memo_activation_heights`. This is needed so validators can ratify the new kinds; there is no other change.
- **`crypto_provider`:** adds `address.rs`, with parse, checksum and canonical validation and published vectors from `docs/fixtures/addresses/pftl-address-vectors-v1.json`. `lib.rs` re-exports it, and `address_from_public_key` now uses the same constants (`postfiat.address.v1`, `pf`), so derived addresses are unchanged. `Cargo.toml` adds `serde_json` as a dev-dependency only.

### R7. Changes without an activation gate

None alters a consensus or state result. The changes that apply from install:

- RPC and mempool refusal of malformed destinations, which is local policy;
- typed RPC error codes for those refusals (`crates/node/src/rpc_dispatch.rs:5-14`);
- the `account` RPC field `address_checksummed` and the `WalletKeyReport` field of the same name;
- memo contents and shielded-withdrawal rows in `account_tx`, plus index schema v2 (XR-05);
- `tx` `transaction_rows`, which is not hashed;
- test fixtures changed to canonical recipients.

## Activation steps (later today, after all six run the new binary)

- **Record kinds:** `recipient_format_activation_height`, `rejected_tx_fee_activation_height` and `require_memo_activation_height`. Use three amendments, one per governance batch (`governance-batch` takes one `--amendment-file`). The value is the first block height where the rule applies.
- **Signers:** the six validators, each with its validator key file. `governance-authorization-sign` checks each signature against the current registry key, and the batch must satisfy the amendment's `quorum` and `support` (`crates/node/src/consensus_artifacts.rs:2980-2994`). `--support` defaults to all `--validators`. The issuer does not sign, and neither does any account key.
- **Commands** (as in the FastPay record and the address-format doc's [activation section](../wallets/address-format.md#activation)), per kind:
  1. `postfiat-node ratify-<kind-with-dashes> --data-dir PATH --validators validator-0,…,validator-5 --height H --amendment-file K.unsigned.json`
  2. On each validator: `governance-authorization-sign --amendment-file K.unsigned.json --validator validator-N --validator-key-file PATH --proposal-slot S --expires-at-height E --authorization-file N.json`
  3. `governance-amendment-assemble --amendment-file K.unsigned.json --authorization-files 0.json,…,5.json --proposal-slot S --output K.signed.json`
  4. `governance-batch --amendment-file K.signed.json --batch-file K.batch.json`
  5. `transport-peer-certified-batch-round --batch-kind governance --batch-file K.batch.json --topology PATH --key-file PATH --artifact-dir PATH`
- **Height:** the chain advances only with transactions. After install the tip is about 1143, assuming the usual six faucet grants, and the three records take three more blocks. Read the tip T just before signing. Then:
  - set S to the next slot;
  - set E to a few blocks later;
  - set H to about T+10, a short margin above the last governance block. That block must stay below H, or the lifecycle check rejects the record and it has to be signed again.
  - Do not pick a distant height: it would need hundreds of filler blocks to reach.
  - Use one H for all three, or submit recipient-format last, because it is irreversible (XR-03).
  - Reach H with faucet grants. Then probe once per rule: an `account_set` to the test account, a memo-less payment that should be refused at RPC, and a `tec_` fee claim.

## Tests run

Focused suites on `5b2efe9d` (Rust 1.95.0, `--locked`):

- `cargo test -p postfiat-crypto-provider -p postfiat-types -p postfiat-execution -p postfiat-rpc-sdk`: 11, 153, 230 and 254 (195 lib + 59 bin/integration) passed, 0 failed.
- `cargo test -p postfiat-consensus-cobalt --lib`: 76 passed.
- `cargo test -p postfiat-node --lib -- recipient_format rejected_fee require_memo issued_payment_v2 account_tx_exchange rpc_serve_request legacy`: 34 passed. That includes all six `rejected_fee_require_memo`, all three `recipient_format_activation` and all three `account_tx_exchange_history` tests.
- `--test exchange_rpc_history`: 1 passed.
- `--bin postfiat-node -- signed_submit_rpc_rejects_malformed_recipients account_rpc_result_adds_checksummed`: 2 passed.
- `--test atomic_swap_local_six`: 1 passed and 8 ignored. The six-validator successor rehearsals are `#[ignore]`; they were compiled but not run.
- `scripts/test-a666-build-nav-profile-rotation-ops.py` and `scripts/test-a666-build-route-epoch-advance.py`: 8 and 14 passed.

Total: 762 Rust tests and 22 Python tests, 0 failed. The full workspace suite was not rerun; it passed in CI on `7e7169b6`/`124a187b`: [rust-ci 39864672912](https://github.com/postfiatorg/postfiatl1v2/actions/runs/39864672912) including `test`, [product-security-ci 39864672901](https://github.com/postfiatorg/postfiatl1v2/actions/runs/39864672901) and [docs 39864672913](https://github.com/postfiatorg/postfiatl1v2/actions/runs/39864672913). No Orchard boundary changed, so the Orchard suite was not run (XR-01 confirms that the Orchard deposit path is unchanged).

## Limits

- This is an agent source review. It is not an external audit, and it does not replace the cross-binary archive replays.
- The live fleet was not probed; the address inventory comes from the signed 1123 canary import plus the documented blocks 1124–1137.
- The StakeHub venue wallet file is not on this server.
