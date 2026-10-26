# Ethereum contracts

Foundry project for the Solidity contracts, tests and deploy scripts. CI's
`evm-contracts` job runs `forge test --no-match-path 'test/*Fork.t.sol'` here
with Foundry v1.7.1 and solc 0.8.24 (`foundry.toml`). Bridge deployment is
described in [script/README.md](script/README.md).

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
(`ZeroSupply()`) reverts. The contract fixes no supply number.

Tests:

```bash
cd crates/ethereum-contracts
git submodule update --init lib/openzeppelin-contracts
forge test --match-contract PFTToken
```

Dry run of the deploy script against a local anvil, with no key and no broadcast:

```bash
anvil --chain-id 84532 &
PFT_TOKEN_NAME="Post Fiat Token" PFT_TOKEN_SYMBOL=PFT \
PFT_TOKEN_TOTAL_SUPPLY=1000000000000 \
PFT_TOKEN_TREASURY=0x0000000000000000000000000000000000007EA5 \
  forge script script/DeployPFTToken.s.sol:DeployPFTToken --rpc-url http://127.0.0.1:8545
```

The script prints the deployed address. It refuses unset, empty or
`replace...` values; `script/pft-token.env.example` holds placeholders only. For
a real deployment, fill a copy kept outside the repository, load it into the
shell, and give the RPC URL and the one-time deployer key on the command line
(`--rpc-url <base-sepolia-rpc-url> --interactives 1 --broadcast`); neither is
stored in a file.

OpenZeppelin pin: `lib/openzeppelin-contracts` is a git submodule at tag
`v5.7.0`, commit `cab19933c33c2ad1d4c7a84864a3601dddfd16f3`.
