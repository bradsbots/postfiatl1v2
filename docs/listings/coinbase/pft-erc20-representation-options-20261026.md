# An ERC-20 form of PFT before mainnet: options and a recommended path

**Status:** Draft, 2026-10-26. Operator dravlic, for the product owner's Coinbase document. Text Improvement Harness full gate, scored without the score line (5 runs per judge): 83.27 → 83.93 after one editing pass (GPT-6 Astra Pro 79.40 → 81.80, Claude Fable 5.1 82.20 → 82.00, GLM 5.3 88.20 → 88.00; document SHA-256 `199aeb9e…` → `d8505f02…`); not iterated further.

## 1. BLUF

1. I recommend "ERC-20 first, bridge at mainnet": a plain fixed-supply ERC-20 PFT now, and a 1:1 bridge into native PFT that opens at this L1's mainnet genesis and never closes.
2. Coinbase integrates ERC-20 tokens with little engineering work. A native chain without mainnet or post-quantum custody cannot be integrated soon. Injective took this route onto Coinbase.
3. The token costs about 3 days plus an audit, the genesis bridge about 10–15 days, and an optional reverse bridge about 15–25 days; all are my estimates without audit time.
4. Only you decide the supply number, Ethereum or Base, the treasury keys, the allocation, the treatment of PFT already paid on the PFT Ledger, and when to tell Coinbase.
5. On your word I build the contract with tests and a test-network deploy script, then a one-page note for Coinbase, then the Phase 2 design note.

This paper extends the "Interim path: PFT as an ERC-20" section of the [integration plan](integration-plan.md) (`integration-plan.md:71-74`, `:719-737`). That section said the route would be scoped only if Coinbase showed interest (`:736-737`). That interest came with the product owner's message of 2026-10-23. Coinbase wants to start getting ramped up, he is assembling a document for them, and in his view Coinbase cannot get this on mainnet imminently. He also asked whether PFT itself could be the first NAVCoin with an ERC-20 form. Section 6 answers that.

## 2. Terms

- **PFTL**: this L1, Post Fiat L1, the chain in this repository (`docs/start/glossary.md:12-14`).
- **PFT Ledger**: the separate, older rippled-fork network run by `postfiatd`, where Task Node pays today (`docs/start/glossary.md:15-22`). My earlier research wording mixed the two; this paper keeps them apart.
- **Native PFT**: the base asset of PFTL, created only at genesis (`docs/status/OPEN-SOURCE-NATIVE-SUPPLY-INVENTORY-20260716.md:12-13`).
- **Issued asset**: an asset an issuer creates on PFTL, such as pfUSDC; it is not native PFT (`OPEN-SOURCE-NATIVE-SUPPLY-INVENTORY-20260716.md:48-49`).
- **NAVCoin**: an issued asset whose supply, mint and redeem are tied to proven reserve packets and a floating net asset value (`docs/navcoins/index.md:9-12`).
- **wA666**: the ERC-20 on Ethereum mainnet that represents the A666 NAVCoin (`docs/navcoins/assets-and-venues.md:29-33`).
- **ERC-20**: the standard fungible-token interface on Ethereum and other EVM chains.
- **Base**: Coinbase's Ethereum layer-2 network, one of the chains its listings page names (coinbase.com/listings, 2026-10-26).

## 3. Where PFT exists today

**On the PFT Ledger.** Task Node rewards are payments from a "Task Node distribution wallet", most with encrypted `pf.ptr/v4` reward pointers (`docs/governance/tasknode-unl-shadow-run-20260904.md:36-43`). Our completed plans record those rewards in PFT, for example 4.5 PFT for one task (`docs/plans/completed/cobalt-activate-or-retire-milestone.md:100`). The PFT Ledger's PFT supply and issuer are not recorded in this repository. postfiat.org says Task Node pays in PFT, PFT has a fixed supply and every fee is burned (postfiat.org, 2026-10-26).

**On PFTL's devnet.** The genesis constant is `GENESIS_NATIVE_SUPPLY_ATOMS = 1_000_000_000` (`crates/types/src/core_chain.rs:10`). Wallets show 1 PFT as 1,000,000 atoms, so the devnet holds 1,000 PFT; that decimal convention is not a Rust constant (`docs/listings/coinbase/comparisons.md:96-101`). Genesis is the only creation event (`OPEN-SOURCE-NATIVE-SUPPLY-INVENTORY-20260716.md:12-13`). NAV and bridge records cannot create native PFT (`:69`). Native PFT has no asset id (`docs/rpc/account-history.md:73`). PFTL is a controlled devnet, not a production mainnet (`integration-plan.md:22-29`).

**On Ethereum or Base.** Nowhere. No wrapped-PFT contract, proof profile or threat model exists (`integration-plan.md:729`). postfiat.org mentions no ERC-20, bridge or migration for PFT (postfiat.org, 2026-10-26).

**The supply number.** 100 billion PFT is a published target, "not a protocol artifact"; no production genesis, allocation table or vesting schedule exists (`integration-plan.md:99-105`). The 2026-10-23 handoff leaves the 100 billion target against the devnet's 1,000 PFT open (`docs/handoffs/2026-10-23___codex__chain_pr_merge_handoff.md:198-200`). Token migration from the PFT Ledger is out of scope of the launch spec and left to "a separate document" (`docs/architecture/l1v2-testnet-genesis-and-launch-spec.md:27`, `:402`). That document does not exist.

## 4. What Coinbase can take

Coinbase's listings page says it can integrate ERC-20 tokens on Base, Ethereum, Optimism, Arbitrum and Polygon, and Solana SPL and ARC-20 tokens, with relatively little engineering work (coinbase.com/listings, 2026-10-26; the page text is about two years old). Native blockchains and other asset types need extra resources and are prioritised lower (same source). Its 2020 technical criteria for ERC-20s are verified source code, industry-standard libraries, restrictions on privileged participants, and a simple modular design (same source). There is a separate track for tokens that have not launched yet (same source).

Our listing package assumes the native chain. Coinbase would run its own nodes, treat one commit certificate as final, and sign with ML-DSA-65 (`integration-plan.md:42-47`). Today there is no mainnet and no external audit (`:52`), the validator set is Foundation-run (`:58`), and Coinbase custody cannot sign ML-DSA-65 (`:59`). Coinbase's post-quantum signing pipeline is about mid-2027 (`:343`). The package already names the ERC-20 as the interim path on Ethereum or Base (`:71-74`). Its first ask to Coinbase is which route to plan on (`:741-743`).

Three precedents bracket the choice. INJ ran as an ERC-20 on Ethereum for years and was listed on Coinbase in that form. Coinbase supported the migration to native INJ on the Injective EVM on 2026-07-20..22. It converted customer balances 1:1 at no cost, then ended ERC-20 INJ deposits and withdrawals; self-custodied holders used the Injective Bridge (Coinbase Markets on X and Coinbase help centre "Token delistings and migrations", June–July 2026; cryptobriefing.com, 2026-06-18). dYdX moved its ERC-20 to the native chain token through a one-way bridge that closed on 2025-06-13. More than 41.6 million ethDYDX were left behind, unmigratable and unlisted, and holders now ask governance to reopen it (forklog.com, 2025). Fetch.ai keeps a two-way bridge between ERC-20 FET and native FET (fetch.ai docs, 2026-10-26).

## 5. The five technically possible forms

Sizes are my estimates in working days, without audit time.

| Form | What it is | Exists / missing | Main risk | Days |
| --- | --- | --- | --- | ---: |
| A. Treasury ERC-20, one-way swap at mainnet | Fixed-supply ERC-20 held by a treasury; holders later swap into native PFT reserved at genesis | Exists: migration precedent, token template, Ethereum-to-PFTL ingress. Missing: the token, the genesis reserve, the release path, the token document | Backed only by the genesis promise until mainnet | 3 + 10–15 |
| B. Bridged wPFT after mainnet | Native PFT locked on PFTL; an equal ERC-20 minted on Ethereum or Base against a finality proof | Exists: A666 export route, verifier, relay. Missing: a native-PFT export lane, a custody lane, route generalisation, threat model | Only as strong as the PFTL validator set | 15–25 |
| C. PFT-backed NAVCoin with an ERC-20 | An issued NAVCoin holding native PFT in reserve, exported like wA666 | Exists: the A666 stack. Missing: a PFT reserve adapter, a PFT valuation source, route generalisation | Coinbase reviews an issued product, not PFT | 10–20 |
| D. ERC-20 now, "external" lane at genesis | Fixed ERC-20 now; genesis places the same native amount in the external supply lane, released on bridge-in | Exists: the four-way supply partition, the A666 opening precedent. Missing: genesis support for the lane, the inbound release path | Supply number chosen now binds genesis | 15–20 |
| E. ERC-20 backed by PFT on the PFT Ledger | Lock PFT Ledger PFT and mint an ERC-20 against it | Exists: only read-only PFT Ledger readers for Task Node scoring. Missing: everything, outside this repository | A custodial bridge on a testnet, then a second migration | 15–25 |

**A. Treasury ERC-20, one-way swap.** The precedent is `A651ToA666MigrationV1`, an ownerless, fixed-ratio retirement path funded from a frozen holder snapshot (`crates/ethereum-contracts/src/A651ToA666MigrationV1.sol:14-18`). A token template with a lockable controller exists (`crates/ethereum-contracts/src/PFTLUniswapHandoffController.sol:903`). Ethereum-to-PFTL ingress runs on a disclosed BFT checkpoint plus receipt inclusion (`docs/status/A666-PFUSDC-PRIVATE-SWAP-CURRENT-STATE-20260730.md:391`). Missing are the token, a genesis reserve and the token document (`l1v2-testnet-genesis-and-launch-spec.md:402`).

**B. Bridged wPFT after mainnet.** This is the route the integration plan sketched (`integration-plan.md:729-731`). The A666 export route and relay run today (`deployments/a666-export-relay-mainnet-20260731/README.md:3`, `:7-12`). The route requires a registered NAV asset, so native PFT cannot use it yet (`crates/execution/src/nav_vault_asset_execution.rs:6470-6477`). The primary-market contract hard-codes A666 constants (`docs/navcoins/navcoin-create-and-swap-spec.md:778`). The token is only as strong as the validator committee (`integration-plan.md:733-734`).

**C. PFT-backed NAVCoin.** Section 6 covers it.

**D. External lane at genesis.** The whitepaper already partitions supply into native, shielded, external and in-flight claims (`docs/whitepaper.md:66-70`). A666 opened with its whole supply locked in a migration contract (`docs/whitepaper.md:42`). Today's native invariant counts only live custody and fee burns (`OPEN-SOURCE-NATIVE-SUPPLY-INVENTORY-20260716.md:23`), so a genesis external lane is new consensus work.

**E. PFT Ledger-backed ERC-20.** This repository only reads frozen PFT Ledger views for Task Node validator scoring (`docs/plans/completed/tasknode-unl-mvp-plan.md:196`, `:216`). The PFT Ledger is a testnet (`l1v2-testnet-genesis-and-launch-spec.md:33`). Holders would need a second migration to PFTL later.

## 6. The product owner's idea: PFT as the first NAVCoin

It is a good instinct. The NAVCoin stack is our most finished cross-chain product, and wA666 already lives on Ethereum mainnet (`docs/navcoins/assets-and-venues.md:39`). But native PFT cannot itself be a NAVCoin. NAVCoins are issued by issuers under registered profiles (`docs/whitepaper.md:34`), and a NAV mint names its issuer (`crates/types/src/transactions_mempool_receipts.rs:1039-1068`). Native PFT is created only at genesis, and NAV records have no authority to create it (`OPEN-SOURCE-NATIVE-SUPPLY-INVENTORY-20260716.md:12-13`, `:69`).

What could be built is a NAVCoin that holds native PFT in reserve, on the A666 stack. Coinbase would then review an issued, reserve-backed product with issuer and reserve questions. Its value would float with its reserve (`docs/navcoins/index.md:9-12`). The listing would not be PFT itself; our package keeps NAVCoins outside the native PFT integration (`integration-plan.md:66-68`). So the NAVCoin stack stays the product beside PFT, and the ERC-20 question is answered by a plain token.

## 7. Recommendation: ERC-20 first, bridge at mainnet

This is the Injective pattern (Coinbase help centre "Token delistings and migrations", June–July 2026). It combines forms A and D now and leaves B for later.

**Phase 1, now (about 3 days plus the audit).**

- One fixed-supply ERC-20 PFT contract on Ethereum mainnet. Base is the equal alternative Coinbase supports (coinbase.com/listings, 2026-10-26). My lean is Ethereum, because our verifier, relay and pool contracts already live there (`A666-PFUSDC-PRIVATE-SWAP-CURRENT-STATE-20260730.md:224-233`). The choice is yours.
- Built from the OpenZeppelin `ERC20` and `ERC20Permit` libraries. OpenZeppelin is not vendored today; `foundry.toml` expects a `lib` directory (`crates/ethereum-contracts/foundry.toml:6`) and `.gitmodules` pins only `arc-node` and `sp1-contracts` (`.gitmodules:1-6`). I add it as a pinned submodule.
- No mint after construction, no pause, no blacklist, no upgrade path and no admin role. That meets Coinbase's four criteria: verified source, standard libraries, no privileged participants, one simple contract (coinbase.com/listings, 2026-10-26).
- The whole supply minted at construction to a treasury address the product owner controls.
- Source verified on the block explorer.
- Deployed first on a test network with a deploy script and tests in `crates/ethereum-contracts`, as the existing scripts and tests are (`crates/ethereum-contracts/script/DeployERC20Bridge.s.sol:38-67`, `crates/ethereum-contracts/test/ERC20BridgeVaultL1.t.sol`).
- An audit before mainnet deployment.

**Phase 2, at PFTL's mainnet genesis (about 10–15 days).**

- Genesis reserves the same amount of native PFT in the "external" lane of the four-way partition (`docs/whitepaper.md:66-70`).
- A holder locks ERC-20 PFT in a contract on Ethereum and receives native PFT on PFTL. The proof is the existing BFT-checkpoint ingress used for pfUSDC deposits (`A666-PFUSDC-PRIVATE-SWAP-CURRENT-STATE-20260730.md:391`; `crates/ethereum-contracts/src/ERC20BridgeVaultL1.sol:6-16`).
- The new part is releasing native PFT from the reserved lane. Today the vault bridge credits issued assets, not native PFT (`docs/pfusdc-issuance-paths-inventory.md:55`).
- The frozen-snapshot part is modelled on `A651ToA666MigrationV1` (`A651ToA666MigrationV1.sol:14-18`).
- The bridge stays open with no closing date. That is the dYdX lesson (forklog.com, 2025).

**Phase 3, later and optional (about 15–25 days).**

- The reverse direction: native PFT exported as the same ERC-20 through a generalised export route. Today the route requires a NAV asset (`nav_vault_asset_execution.rs:6470-6477`).
- That makes the token two-way, as Fetch.ai's is (fetch.ai docs, 2026-10-26).

**What this path does not solve.** These questions belong in the token document. They are yours to decide, with counsel on the legal ones, including the securities framing; I do not decide them.

- The total supply number (`integration-plan.md:99-105`).
- The allocation: how much supply is in the ERC-20 at launch, and how much stays in genesis for the Foundation, validators and the Task Node pool (`integration-plan.md:710-711`).
- What happens to PFT already paid on the PFT Ledger: a snapshot and a swap into the ERC-20, or into native PFT at genesis.
- PFT's legal classification, which the package already lists as a question for counsel (`integration-plan.md:749-751`).

## 8. Risks

- **Before mainnet, the ERC-20 is backed by the genesis promise only.** No chain holds native PFT behind it until Phase 2.
- **The listing still depends on Coinbase's review of the project, not only the contract.** Coinbase's process includes legal, compliance and technical-security review (`integration-plan.md:142`).
- **A one-way bridge that closes strands holders.** dYdX left more than 41.6 million tokens behind (forklog.com, 2025).
- **A supply number chosen now binds genesis later.** The devnet and the target already disagree (`2026-10-23___codex__chain_pr_merge_handoff.md:198-200`).
- **The Foundation-run validator set is the trust base of any later bridge** (`integration-plan.md:58`, `:733-734`).

## 9. Decisions for the product owner

1. The total supply number.
2. Ethereum or Base for the token.
3. Custody of the treasury and deployer keys; they are your keys.
4. The allocation and the treatment of PFT Ledger holders.
5. Whether to tell Coinbase now that the ERC-20 is the path, answering the package's first ask (`integration-plan.md:741-743`).

## 10. What I build on your word

1. The ERC-20 contract with tests and a deploy script, deployed to Sepolia (or Base Sepolia).
2. A one-page note for Coinbase built from Appendix A.
3. The Phase 2 design note: the genesis external lane and the lock-and-release path.

## Appendix A: text for the Coinbase document

Paste-ready once the decisions in section 9 are made.

PFT will first exist as a standard ERC-20 token. The contract is built from widely used industry-standard libraries. Its whole supply is created once, at deployment. No account can mint more, pause transfers, block addresses or upgrade the contract. The source code will be verified and published. An independent audit will be completed before the token is deployed. The native Post Fiat L1 is not yet on mainnet. When it launches, the genesis supply will reserve native PFT for every ERC-20 PFT in existence. Holders will then be able to move ERC-20 PFT to native PFT one for one. That bridge will stay open, with no closing date. Exchanges holding ERC-20 PFT for customers can convert balances one for one in the same way. Supply and allocation figures will be published in a token document before the ERC-20 is deployed.

## Appendix B: sources

Repository:

- `docs/listings/coinbase/integration-plan.md`, `docs/listings/coinbase/comparisons.md`
- `docs/start/glossary.md`, `docs/whitepaper.md`, `docs/rpc/account-history.md`
- `docs/status/OPEN-SOURCE-NATIVE-SUPPLY-INVENTORY-20260716.md`, `docs/status/A666-PFUSDC-PRIVATE-SWAP-CURRENT-STATE-20260730.md`
- `docs/governance/tasknode-unl-shadow-run-20260904.md`, `docs/plans/completed/cobalt-activate-or-retire-milestone.md`
- `docs/handoffs/2026-10-23___codex__chain_pr_merge_handoff.md`, `docs/architecture/l1v2-testnet-genesis-and-launch-spec.md`
- `docs/navcoins/index.md`, `docs/navcoins/assets-and-venues.md`, `docs/navcoins/navcoin-create-and-swap-spec.md`, `docs/pfusdc-issuance-paths-inventory.md`
- `deployments/a666-export-relay-mainnet-20260731/README.md`
- `crates/types/src/core_chain.rs`, `crates/types/src/transactions_mempool_receipts.rs`, `crates/execution/src/nav_vault_asset_execution.rs`
- `crates/ethereum-contracts/src/A651ToA666MigrationV1.sol`, `crates/ethereum-contracts/src/PFTLUniswapHandoffController.sol`, `crates/ethereum-contracts/src/ERC20BridgeVaultL1.sol`
- `crates/ethereum-contracts/script/DeployERC20Bridge.s.sol`, `crates/ethereum-contracts/foundry.toml`, `.gitmodules`
- `docs/plans/completed/tasknode-unl-mvp-plan.md`

Outside sources, as I verified on 2026-10-26:

- Coinbase listings page, coinbase.com/listings (text about two years old).
- Coinbase Markets on X and Coinbase help centre, "Token delistings and migrations", June–July 2026; cryptobriefing.com, 2026-06-18 (Injective).
- forklog.com, 2025 (dYdX bridge closure).
- fetch.ai documentation (FET token bridge).
- postfiat.org.
