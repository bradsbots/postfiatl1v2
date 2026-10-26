# PFT token deploy-script dry run, 2026-10-26

This records the local dry run of `DeployPFTToken` for milestone item P1.3. It
ran against commit `ad5ba32f` on a local anvil only. No key was used, no
transaction was broadcast, and nothing exists on any network.

## Command

The run used forge 1.8.1 in `crates/ethereum-contracts`.

```bash
anvil --port 18547 --chain-id 84532 --silent &
PFT_TOKEN_NAME="Post Fiat Token" PFT_TOKEN_SYMBOL=PFT \
PFT_TOKEN_TOTAL_SUPPLY=1000000000000 \
PFT_TOKEN_TREASURY=0x0000000000000000000000000000000000007EA5 \
  forge script script/DeployPFTToken.s.sol:DeployPFTToken \
  --rpc-url http://127.0.0.1:18547 --offline
```

Chain id 84532 is Base Sepolia's, so the simulation runs under the test
network's id. The supply and treasury are test values; the real supply is not
decided and the treasury Safe does not exist yet.

## Results

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

P1.3 still needs the test deployment on Base Sepolia. It needs a deployer key
funded with Base Sepolia ETH and a treasury there, either the Safe or a
placeholder address. The command is the one in `crates/ethereum-contracts/README.md`,
with `--rpc-url <base-sepolia-rpc-url> --interactives 1 --broadcast`. After
it, the source must be verified on the Base Sepolia block explorer; the item
is ticked with the deployed address and the verified-source page.
