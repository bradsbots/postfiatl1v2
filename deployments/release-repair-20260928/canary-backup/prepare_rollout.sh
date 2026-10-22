#!/usr/bin/env bash
# Prepare the combined-fastpay-20260928 rollout state and take the signed validator-1 canary backup,
# as deployments/combined-fastpay-20260925/DEPLOY-SHEET.md §2-5 did. No apply, no restart, no transaction.
# Keys are passed by path only.
set -euo pipefail

D=$HOME/.postfiat/deployments/combined-fastpay-20260928
S=$D/stage; E=$D/evidence; R=combined-fastpay-20260928
C=$S/rootfs/etc/postfiat/releases/$R; U=$S/rootfs/etc/systemd/system
B=$S/rootfs/opt/postfiat/releases/$R/postfiat-node
REPO=$HOME/.cache/qualify-20260928
OLDPACKET=$REPO/deployments/combined-fastpay-20260925
BIN=$HOME/.cache/release-repair-20260928/binaries/candidate-1
L=$HOME/.postfiat/deployments/combined-fastpay-20260925/r4-layout-validator-0
PUBK=$HOME/.postfiat/deployments/fastpay-committee-20260925-r4/keys
K=$HOME/.postfiat/deployments/cobalt-activation-8694b99d/snapshot-keys
VULTR=$HOME/.postfiat/deployments/cobalt-activation-8694b99d/vultr-api-key
SRC=c93b213755f5889565fd1f77b9e45c149a07193a
step() { echo "$(date -u +%FT%TZ) $*"; }
test ! -e "$D"
mkdir -p "$E"; chmod 700 "$E"
step "binary $(sha256sum "$BIN" | cut -d' ' -f1)"
step stage
"$BIN" deployment-validator-units-stage --release-id $R \
  --topology-file $L/topology.json --binary-file "$BIN" \
  --swap-circuit-metadata-file $L/swap.metadata.json \
  --private-egress-circuit-metadata-file $L/private-egress.metadata.json \
  --output-dir $S > $E/stage-command.stdout 2> $E/stage-command.stderr
install -m 0644 $PUBK/deployment.public.json $C/deployment.public.json
cmp "$BIN" "$B"
# Inventory: same file as the 2026-09-25 rollout (SHA-256 6c11341d...), kept beside the state so it outlives the worktree.
install -m 0644 $OLDPACKET/inventory.txt $D/inventory.txt
step "inventory $(sha256sum $D/inventory.txt | cut -d' ' -f1)"
FROM=$(date -u +%s); UNTIL=$((FROM + 31536300))
echo "from=$FROM until=$UNTIL" > $E/manifest-validity.txt
step sign
"$B" deployment-manifest-create --deployment-id $R \
  --valid-from-unix $FROM --valid-until-unix $UNTIL \
  --chain-id postfiat-wan-devnet-2 --genesis-hash ce22ca8c932da0998b484483a09647138a30e0bf44408dd49a8d6d452787ad25521aff3ed334da07e150a7233a3e90a9 \
  --git-revision $SRC --binary-file "$B" \
  --build-profile release --build-features privacy,rpc,transport \
  --protocol-version 1 --rpc-schema postfiat-local-rpc-v1 \
  --service-unit-file $U/postfiat-validator-0-rpc.service \
  --environment-file $C/validator-0.rpc.env \
  --validator-bindings-file $S/validator-bindings.signing.json \
  --topology-file $C/topology.json --swap-circuit-metadata-file $C/swap.metadata.json \
  --private-egress-circuit-metadata-file $C/private-egress.metadata.json \
  --publisher-key-file $PUBK/deployment-publisher.key.json \
  --manifest-file $C/deployment-manifest.json > $E/manifest-create.stdout 2> $E/manifest-create.stderr
step "manifest $(sha256sum $C/deployment-manifest.json | cut -d' ' -f1)"
step preflight
(cd $REPO && scripts/postfiat-safe-rollout preflight --stage-report $S/stage-report.json \
  --inventory-file $D/inventory.txt --vultr-api-key-file $VULTR \
  --state-file $E/rollout-state.json --canary-validator-id validator-1 \
  --rpc-tunnel-base-port 27650) > $E/preflight.json 2> $E/preflight.stderr
step "preflight ok state $(sha256sum $E/rollout-state.json | cut -d' ' -f1)"
step backup
(cd $REPO && scripts/postfiat-safe-rollout backup --state-file $E/rollout-state.json \
  --evidence-dir $E/pre-rollout-backup \
  --snapshot-publisher-key-file $K/snapshot-publisher.private.json \
  --snapshot-publisher-public-key-file $K/snapshot-publisher.public.json) > $E/backup.json 2> $E/backup.stderr
step "backup ok state $(sha256sum $E/rollout-state.json | cut -d' ' -f1)"
