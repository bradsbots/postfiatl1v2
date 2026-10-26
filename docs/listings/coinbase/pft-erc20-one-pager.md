# PFT as an ERC-20 on Base

A note for Coinbase, 2026-10-26.

## What PFT is

PFT is the native coin of Post Fiat L1. Its supply is fixed at genesis, every
native fee is burned, and no validator reward creates new PFT
([whitepaper](https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/whitepaper.md#L34);
[postfiat.org](https://postfiat.org)). Native PFT counts in six decimals, so
1 PFT is 1,000,000 atoms. Post Fiat L1 is not yet on mainnet.

## The ERC-20 PFT on Base

PFT will first exist as a standard ERC-20 token on Base. The contract mints
its whole supply once, at deployment, to a treasury that is designed to be a
multi-signature wallet, never a single key. No function mints more afterwards.

The token uses six decimals, the unit of native PFT, so one token unit equals
one atom and amounts match one for one. No account can mint, pause transfers,
block addresses or upgrade the contract, and the contract has no owner or
admin role. It is built only from the OpenZeppelin `ERC20` and `ERC20Permit`
contracts, release v5.7.0, and supports approvals by signed message
(EIP-2612).

The deployment is designed to follow an independent audit, and the source is
designed to be verified and published on the Base block explorer.

## The path to the native chain

At Post Fiat L1's mainnet genesis, the same amount of native PFT is designed
to be reserved for ERC-20 holders, in the external category of the ledger's
supply partition
([whitepaper](https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/whitepaper.md#L66-L70)).
A one-for-one bridge, designed to stay open with no closing date, then lets
holders move ERC-20 PFT to native PFT. Exchanges holding ERC-20 PFT
for customers can convert balances one for one in the same way, as Coinbase
did when INJ moved from its ERC-20 to the native Injective chain in July 2026
([Coinbase help centre](https://help.coinbase.com/en/coinbase/trading-and-funding/sending-or-receiving-cryptocurrency/token-migrations)).

## Source

The contract is public on GitHub at
[crates/ethereum-contracts/src/PFTToken.sol](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/ethereum-contracts/src/PFTToken.sol),
with its tests in
[test/PFTToken.t.sol](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/ethereum-contracts/test/PFTToken.t.sol).

Supply and allocation figures will be published in the token document before
the ERC-20 is deployed.
