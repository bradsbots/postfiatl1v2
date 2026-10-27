#!/usr/bin/env bash
# CLI-level test of the deploy script: runs `forge script` (not `forge test`,
# which does not apply forge's script-only rules such as the address(this)
# check) on forge's in-process chain with a code-bearing treasury. No RPC, no
# key, no broadcast.
set -euo pipefail
cd "$(dirname "$0")/.."

export PFT_TOKEN_CHAIN_ID=84532 PFT_TOKEN_NAME="Post Fiat Token" PFT_TOKEN_SYMBOL=PFT \
  PFT_TOKEN_TOTAL_SUPPLY=1000000000000 PFT_TOKEN_TOTAL_SUPPLY_PFT=1000000 \
  PFT_TOKEN_TREASURY=0x0000000000000000000000000000000000005AFE \
  PFT_TOKEN_ALLOW_USED_DEPLOYER=1 # the in-process chain starts the sender at nonce 1
unset PFT_TOKEN_ALLOW_EOA_TREASURY PFT_TOKEN_REAL_DEPLOYMENT PFT_TOKEN_TEST_SINGLETON

run() {
  forge script test/DeployPFTTokenCli.s.sol:DeployPFTTokenWithFakeSafe --chain-id 84532 2>&1
}

out="$(run)" || { printf '%s\n' "$out"; echo "FAIL: the script refused a Safe with the official singleton" >&2; exit 1; }
grep -q "PFTToken deployed at" <<<"$out"
grep -q "treasury Safe threshold 2" <<<"$out"
grep -q "treasury Safe singleton 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762" <<<"$out"
echo "ok: code-bearing treasury with the official singleton accepted"

if out="$(PFT_TOKEN_TEST_SINGLETON=0x0000000000000000000000000000000000000BAD run)"; then
  printf '%s\n' "$out"; echo "FAIL: the script accepted a wrong singleton" >&2; exit 1
fi
grep -q "UnofficialSafeSingleton" <<<"$out" || { printf '%s\n' "$out"; exit 1; }
echo "ok: lookalike with a wrong singleton refused"
