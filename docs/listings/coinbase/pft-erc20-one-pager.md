# PFT as an ERC-20 on Base

A note for Coinbase, 2026-10-26.

## What PFT is

PFT is the native coin of Post Fiat L1. Its supply is fixed at genesis, every
native fee is burned, and no validator reward creates new PFT
([whitepaper](https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/whitepaper.md#L34);
[postfiat.org](https://postfiat.org)). Wallets show native PFT with six
decimals (1 whole PFT = 1,000,000 base units), and the ERC-20 uses the same
unit: one whole ERC-20 PFT is 1,000,000 base units
([comparisons](https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/listings/coinbase/comparisons.md#L96-L101))
(the contract fixes decimals at 6). Post Fiat L1 is not yet on mainnet. Its
validator set is run by the Foundation today, and that set is the trust base
of the later bridge.

A PFT token also circulates today on Post Fiat's test ledger, the PFT Ledger,
where it pays contributor rewards; its treatment at the ERC-20 deployment and
at mainnet genesis is to be set in the token document. The legal entity
responsible for the ERC-20, the treasury, the token document and the audit
engagement is not yet named; the token document will name it.

## The ERC-20 PFT on Base

On Base, PFT is to exist as a standard ERC-20 token. The contract mints the
whole ERC-20 supply once, at deployment, to the treasury; that supply is
designed to be a slice of the native genesis supply, not additional supply,
and the token document will fix the figures before any Base mainnet
deployment. The treasury is planned to be a Safe multisig, which the
deployment procedure checks on the target chain, and the token contract itself
gives the treasury no privilege beyond holding the supply. No function mints
more afterwards.

The token uses six decimals, the unit of native PFT, so one ERC-20 base unit
equals one native base unit and amounts match one for one. No account can
mint, pause transfers, block addresses or upgrade the contract, and the
contract has no owner or admin role. It is built only from the OpenZeppelin
`ERC20` and `ERC20Permit` contracts, release v5.7.0; the contract adds no code
of its own beyond the constructor, its two zero-value guards and `decimals()`,
and supports approvals by signed message (EIP-2612).

An independent audit is planned before the Base mainnet deployment, and its
report is planned to be shared with Coinbase; the source is to be verified on
the Base block explorer at deployment. Test deployments on Base Sepolia come
first.

## The path to the native chain

At Post Fiat L1's mainnet genesis, the design reserves native PFT in the
external category of the supply partition
([whitepaper](https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/whitepaper.md#L66-L70)),
one native base unit for each ERC-20 base unit. A bridge is designed to let
holders exchange ERC-20 PFT for native PFT one for one in quantity; it depends
on the Post Fiat validator committee's signed checkpoints and on governed
release limits, no closing date is planned, and the reverse direction is a
separate, optional phase. Coinbase converted its customers' ERC-20 INJ
balances one for one to native INJ in July 2026
([Coinbase help centre](https://help.coinbase.com/en/coinbase/trading-and-funding/sending-or-receiving-cryptocurrency/token-migrations));
that is a precedent for the customer-side conversion, not a statement about
Coinbase's plans for PFT.

## Source

The contract is public on GitHub at
[crates/pft-token-contracts/src/PFTToken.sol](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/pft-token-contracts/src/PFTToken.sol),
with its tests in
[test/PFTToken.t.sol](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/pft-token-contracts/test/PFTToken.t.sol).

The total supply is 100 billion PFT, fixed, decided 2026-10-28; the ERC-20
launch quantity and allocation are not yet decided.

## Facts at a glance

- Network: Base (chain id 8453); test network Base Sepolia (chain id 84532).
- Standard: ERC-20 with EIP-2612 permit.
- Decimals: 6.
- Supply and allocation: total supply 100 billion PFT, fixed, decided 2026-10-28; the Base slice, the launch allocation and the issuer per the token document (open).
- Treasury: planned to be a Safe multisig; address to be published.
- Admin keys: none; not upgradeable; no pause or blacklist.
- Audit: planned before the Base mainnet deployment; report planned to be shared with Coinbase.
- Source: to be verified on the Base block explorer at deployment.
- Contract address: to be published.
- Issuer: to be named in the token document.
- Current status: local simulation only; no Base Sepolia deployment yet.
- Dates: none promised; the audit, the Base mainnet deployment, the mainnet
  genesis and the bridge each have their own gate.
