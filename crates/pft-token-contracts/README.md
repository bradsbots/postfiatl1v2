# PFT token contracts

Stand-alone Foundry project for the PFT token. It is kept apart from
`crates/ethereum-contracts` so that project's library directory and compiler
remappings, and with them the pinned A666 public reader build
(`scripts/check-a666-public-reader-candidates`), stay unchanged. Same solc
0.8.24 and optimizer settings (`foundry.toml`); CI's `evm-contracts` job runs
`forge test` here after fetching the OpenZeppelin submodule.

## PFT token (Base)

`src/PFTToken.sol` is the fixed-supply ERC-20 representation of PFT, Phase 1 of
the ERC-20 representation options paper. It is meant for Base, with test
deployments on Base Sepolia.

- Fixed supply: the whole supply is minted once, in the constructor, to the
  treasury. No function mints, burns or changes it later.
- Six decimals: one token unit is one atom of native PFT (1 PFT = 1,000,000 units).
- No privileged role: no owner, admin, pause, blacklist, hook or upgrade path.
- Permit: EIP-2612 approvals by signed message.
- Built only from OpenZeppelin `ERC20` and `ERC20Permit`.

Constructor: `PFTToken(string name, string symbol, uint256 totalSupply, address treasury)`.
`totalSupply` is in six-decimal units; `treasury` is the Safe multisig that
receives the whole supply. A zero treasury (`ZeroTreasury()`) or a zero supply
(`ZeroSupply()`) reverts. The contract fixes no supply number. `name` is at
most 31 bytes: OpenZeppelin v5.7.0's EIP712 stores it as a `ShortString`
(`EIP712.sol:79`) and a longer name reverts with `StringTooLong`
(`ShortStrings.sol:54-56`); the deploy script refuses it first with
`NameTooLong(length)`.

Interface notes:

- `approve` or `permit` to the zero address reverts with `ERC20InvalidSpender`
  (OpenZeppelin v5).
- Besides ERC-20 and EIP-2612, the ABI exposes `eip712Domain()` (ERC-5267).
- The approve race is the standard ERC-20 one: set the allowance to zero first,
  or use `permit`.

Tests:

```bash
git submodule update --init --depth 1 crates/pft-token-contracts/lib/openzeppelin-contracts
cd crates/pft-token-contracts
forge test
```

`test/DeployPFTToken.t.sol` covers every refusal of the deploy script and its
accepted path.

## Deployment

`script/DeployPFTToken.s.sol` reads its values from the environment
(`script/pft-token.env.example` holds placeholders only; keep the filled copy
outside the repository, `*.env` is ignored) and refuses, before the broadcast:

| Check | Refusal |
|---|---|
| `PFT_TOKEN_CHAIN_ID` is 8453 or 84532 and equals the RPC's chain id | `UnsupportedChain`, `WrongChain(expected, actual)` |
| name and symbol are not empty, blank or `replace...` (any casing); name at most 31 bytes | `PlaceholderValue(name)`, `NameTooLong(length)` |
| `PFT_TOKEN_TOTAL_SUPPLY` (units) equals `PFT_TOKEN_TOTAL_SUPPLY_PFT` (whole PFT) × 1,000,000 | `SupplyMismatch(units, pft)` |
| the treasury is not the deployer and has code on the target chain | `TreasuryIsDeployer`, `TreasuryNotAContract` |
| the treasury answers the read-only Safe probe (`getThreshold`, `getOwners`) | `TreasuryIsNotASafe` on 8453; a warning on 84532 |
| the deployer's nonce on the target chain is 0 (a one-time key) | `DeployerAlreadyUsed(deployer, nonce)` |

It prints the chain id, deployer, treasury, Safe threshold and owner count, and
both supply values. `PFT_TOKEN_ALLOW_EOA_TREASURY=1` and
`PFT_TOKEN_ALLOW_USED_DEPLOYER=1` are test-only switches for a local dry run on
84532; on 8453 the script refuses them (`TestSwitchOnMainnet`).

Dry run against a local anvil, with no key and no broadcast:

```bash
anvil --chain-id 84532 &
PFT_TOKEN_CHAIN_ID=84532 PFT_TOKEN_NAME="Post Fiat Token" PFT_TOKEN_SYMBOL=PFT \
PFT_TOKEN_TOTAL_SUPPLY=1000000000000 PFT_TOKEN_TOTAL_SUPPLY_PFT=1000000 \
PFT_TOKEN_TREASURY=0x0000000000000000000000000000000000007EA5 \
PFT_TOKEN_ALLOW_EOA_TREASURY=1 \
  forge script script/DeployPFTToken.s.sol:DeployPFTToken --rpc-url http://127.0.0.1:8545
```

Without `--rpc-url`, forge's in-process EVM starts the sender at nonce 1, so an
in-process run also needs `PFT_TOKEN_ALLOW_USED_DEPLOYER=1`.

Pre-deployment checklist:

- [ ] The treasury Safe is deployed on the target chain and its address,
      owners and threshold are checked on the explorer.
- [ ] `PFT_TOKEN_CHAIN_ID` is the target chain (84532 first; 8453 only after
      the audit below).
- [ ] The supply pair `PFT_TOKEN_TOTAL_SUPPLY` / `PFT_TOKEN_TOTAL_SUPPLY_PFT`
      is the decided supply.
- [ ] The one-time deployer key is fresh (nonce 0) and on a hardware wallet,
      used with `--ledger` (or typed once with `--interactives 1`).
- [ ] Neither test-only switch is set.

A Base mainnet (8453) deployment happens only after an independent audit of
the exact commit being deployed.

Deployment (the RPC URL and the key are given on the command line only):

```bash
forge script script/DeployPFTToken.s.sol:DeployPFTToken \
  --rpc-url <base-rpc-url> --ledger --sender <deployer-address> --broadcast
```

The broadcast writes `deployments/pft-token-base-<chain id>/deployment.json`
(token address, chain id, constructor arguments, deployer, Safe threshold and
owner count, solc version and settings, OpenZeppelin commit); a dry run writes
none. Commit it once the transaction is confirmed. `broadcast/` stays ignored.

Verification on Basescan (`BASESCAN_API_KEY` exported in the shell, never in a
file; `foundry.toml` reads it for chain ids 8453 and 84532):

```bash
forge verify-contract <address> src/PFTToken.sol:PFTToken --chain <8453|84532> \
  --constructor-args $(cast abi-encode "constructor(string,string,uint256,address)" \
    "$PFT_TOKEN_NAME" "$PFT_TOKEN_SYMBOL" "$PFT_TOKEN_TOTAL_SUPPLY" "$PFT_TOKEN_TREASURY") \
  --compiler-version 0.8.24 --num-of-optimizations 200 --evm-version cancun
```

The encoded arguments equal `constructor_args` in the deployment record.

Post-deployment checks:

- [ ] On the explorer, `totalSupply()` equals `PFT_TOKEN_TOTAL_SUPPLY` and the
      treasury Safe holds all of it; the source is verified.
- [ ] The deployment record is committed.
- [ ] The deployer key is retired; it holds nothing and is never used again.

OpenZeppelin pin: `lib/openzeppelin-contracts` is a git submodule at tag
`v5.7.0`, commit `cab19933c33c2ad1d4c7a84864a3601dddfd16f3`. `foundry.toml`
pins solc 0.8.24, optimizer 200 runs and `evm_version = "cancun"`;
`src/PFTToken.sol` pins `pragma solidity 0.8.24`.
