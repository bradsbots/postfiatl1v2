#!/usr/bin/env bash
# CLI-level test of the deploy script: runs `forge script` (not `forge test`,
# which does not apply forge's script-only rules such as the address(this)
# check) on forge's in-process chain with a real Safe treasury. No RPC, no key,
# no broadcast. Hermetic: forge runs under `env -i` with FOUNDRY_OFFLINE=true
# and no RPC variable, and its output is echoed only through a URL redactor.
set -euo pipefail
cd "$(dirname "$0")/.."

RPC_VARS=(FOUNDRY_ETH_RPC_URL DAPP_ETH_RPC_URL ETH_RPC_URL FOUNDRY_FORK_URL)
for v in "${RPC_VARS[@]}"; do unset "$v" 2>/dev/null || true; done
for v in "${RPC_VARS[@]}"; do
  if [ -n "${!v+x}" ]; then echo "FAIL: $v could not be unset (readonly?); refusing to run forge" >&2; exit 1; fi
done

FORGE="$(command -v forge)" || { echo "FAIL: forge not on PATH" >&2; exit 1; }
SAFE_PATH="$(dirname "$FORGE"):/usr/bin:/bin"

redact() {
  sed -E -e 's#[A-Za-z][A-Za-z0-9+.-]*://[^[:space:]"'"'"'<>]+#<redacted-url>#g' \
    -e 's#\b(localhost|[0-9]{1,3}(\.[0-9]{1,3}){3})(:[0-9]+)?(/[^[:space:]]*)?#<redacted-url>#g'
}

# run [VAR=value...]: the script on the in-process chain with only these variables.
run() {
  env -i PATH="$SAFE_PATH" HOME="$HOME" FOUNDRY_OFFLINE=true \
    PFT_TOKEN_CHAIN_ID=84532 PFT_TOKEN_NAME="Post Fiat Token" PFT_TOKEN_SYMBOL=PFT \
    PFT_TOKEN_TOTAL_SUPPLY=1000000000000 PFT_TOKEN_TOTAL_SUPPLY_PFT=1000000 \
    PFT_TOKEN_TREASURY=0x0000000000000000000000000000000000005AFE \
    PFT_TOKEN_ALLOW_USED_DEPLOYER=1 "$@" \
    "$FORGE" script test/DeployPFTTokenCli.s.sol:DeployPFTTokenWithFakeSafe --chain-id 84532 2>&1 | redact
  return "${PIPESTATUS[0]}"
}
# The in-process chain starts the sender at nonce 1, hence PFT_TOKEN_ALLOW_USED_DEPLOYER.

out="$(run)" || { printf '%s\n' "$out"; echo "FAIL: the script refused a real Safe" >&2; exit 1; }
grep -q "PFTToken deployed at" <<<"$out"
grep -q "treasury Safe threshold 2" <<<"$out"
grep -q "treasury Safe singleton 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762" <<<"$out"
echo "ok: real Safe proxy of the official singleton accepted"

if out="$(run PFT_TOKEN_TEST_SINGLETON=0x0000000000000000000000000000000000000BAD)"; then
  printf '%s\n' "$out"; echo "FAIL: the script accepted a wrong singleton" >&2; exit 1
fi
grep -q "UnofficialSafeSingleton" <<<"$out" || { printf '%s\n' "$out"; exit 1; }
echo "ok: Safe proxy with a wrong singleton refused"

if out="$(run PFT_TOKEN_TEST_LOOKALIKE=true)"; then
  printf '%s\n' "$out"; echo "FAIL: the script accepted a lookalike" >&2; exit 1
fi
grep -q "ProxyCodeMismatch" <<<"$out" || { printf '%s\n' "$out"; exit 1; }
echo "ok: lookalike with an allowed singleton in slot 0 refused"
