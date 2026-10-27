# PFT token deploy-script dry run, 2026-10-26

This records the local dry runs of `DeployPFTToken` for milestone item P1.3:
the first on 2026-10-26 against commit `ad5ba32f`, and two on 2026-10-27 after
the deploy-script guards (commit `5d6e6709`). All ran on a local anvil only;
nothing exists on any network.

## Command

The current script also needs `PFT_TOKEN_CHAIN_ID` and the supply in whole
PFT, and refuses a treasury without code unless the test-only switch is set
(84532 only; see `crates/pft-token-contracts/README.md`). The dry run, with
no key and no broadcast, is:

```bash
anvil --chain-id 84532 &
PFT_TOKEN_CHAIN_ID=84532 PFT_TOKEN_NAME="Post Fiat Token" PFT_TOKEN_SYMBOL=PFT \
PFT_TOKEN_TOTAL_SUPPLY=1000000000000 PFT_TOKEN_TOTAL_SUPPLY_PFT=1000000 \
PFT_TOKEN_TREASURY=0x0000000000000000000000000000000000007EA5 \
PFT_TOKEN_ALLOW_EOA_TREASURY=1 \
  forge script script/DeployPFTToken.s.sol:DeployPFTToken --rpc-url http://127.0.0.1:8545
```

`PFT_TOKEN_ALLOW_USED_DEPLOYER=1`, the other test-only switch, is needed only
for an account that has already sent a transaction. On chain id 8453 the script
refuses both switches.

The 2026-10-26 run predates these variables. It used forge 1.8.1 in
`crates/ethereum-contracts`, where the token then lived, with only
`PFT_TOKEN_NAME`, `PFT_TOKEN_SYMBOL`, `PFT_TOKEN_TOTAL_SUPPLY` and
`PFT_TOKEN_TREASURY`, against `anvil --port 18547 --chain-id 84532` with
`--offline`.

Chain id 84532 is Base Sepolia's, so the simulation runs under the test
network's id. The supply and treasury are test values; the real supply is not
decided and the treasury Safe does not exist yet.

## Anvil runs, 2026-10-27

These runs checked the one-time-deployer guard against a real node rather than
forge's in-process EVM. Setup: `anvil --chain-id 84532` with no network. The
deployer was anvil development account 0
(`0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`), whose public test key was given
with `--private-key`. The treasury was account 1
(`0x70997970C51812dc3A010C7d01b50e0d17dc79C8`), allowed by
`PFT_TOKEN_ALLOW_EOA_TREASURY=1`. `PFT_TOKEN_ALLOW_USED_DEPLOYER` was not set.
Both runs used `--broadcast` against the anvil.

| Run | Deployer nonce read | Outcome |
| --- | --- | --- |
| 1 | 0 | `PFTToken deployed at 0x5FbDB2315678afecb367f032d93F642f64180aa3`, `ONCHAIN EXECUTION COMPLETE & SUCCESSFUL.`, 1,232,032 gas estimated |
| 2, same key | 1 | `Error: script failed: DeployerAlreadyUsed(0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266, 1)` |

After run 1, `totalSupply()` was 1000000000000, the treasury held all of it,
the deployer held 0 and `decimals()` was 6. On a forked node the script reads
the account's real nonce, so a fresh key passes. Only forge's in-process EVM,
without `--rpc-url`, starts a sender at nonce 1.

The first attempt wrote its deployment record to
`deployments/pft-token-base-84532/`, the path reserved for the real Base
Sepolia record. The script now writes the record of a broadcast made with a
test-only switch to the ignored `cache/deploy-test/` instead. The runs above
used that version.

## Results, 2026-10-26

The run printed `Script ran successfully`, then `PFTToken deployed at
0x5b73C5498c1E3b4dbA84de0F1833c4a029d90519` and the same address as the
return value. It estimated 1,231,751 gas on chain 84532 and ended with
`SIMULATION COMPLETE`. The address is a local simulation result and holds
nothing anywhere.

With the values of `script/pft-token.env.example` loaded instead, the script
stopped before deploying with `Error: script failed:
PlaceholderValue("PFT_TOKEN_NAME")`.

## Tests and versions

| Check | forge 1.8.1 (local) | forge 1.7.1 (CI's version) |
| --- | --- | --- |
| `forge test --match-contract PFTToken` | 8/8 passed | 8/8 passed |
| `forge test --no-match-path 'test/*Fork.t.sol'` | 186/186 passed, 23 suites | 186/186 passed, 23 suites |

Against an empty stub with only the constructor, the eight PFTToken tests
failed 0/8 before the contract was written. The 1.7.1 run used the official
release binary on a fresh clone, after CI's own submodule step.

OpenZeppelin is pinned as the submodule `lib/openzeppelin-contracts` at tag
`v5.7.0`, commit `cab19933c33c2ad1d4c7a84864a3601dddfd16f3`.

## What remains for P1.3

P1.3 still needs the test deployment on Base Sepolia. It needs the treasury
Safe deployed there and a fresh deployer key funded with Base Sepolia ETH,
with no test-only switch set. The commands and checklists are in
`crates/pft-token-contracts/README.md` (`--rpc-url <base-sepolia-rpc-url>
--ledger --sender <deployer-address> --broadcast`). After it, the source must
be verified on the Base Sepolia block explorer and the deployment record
committed; the item is ticked with the deployed address and the
verified-source page.
