#!/usr/bin/env bash
# EMERGENCY RECOVERY ONLY: return ONE validator from combined-fastpay-20260928 to
# combined-fastpay-20260925 (executable d66cecc3...). Adapted from
# ../combined-fastpay-20260925/rollback-one.sh. See DEPLOY-SHEET.md "Rollback".
#
# Before running, copy that validator's two combined-fastpay-20260925 units from
# the local 2026-09-25 stage into the host's 2026-09-25 release directory (hashes
# are checked below and against the signed 2026-09-25 manifest):
#   scp ~/.postfiat/deployments/combined-fastpay-20260925/stage/rootfs/etc/systemd/system/postfiat-validator-N{,-rpc}.service \
#       root@HOST:/etc/postfiat/releases/combined-fastpay-20260925/
# Then: ssh root@HOST bash -s -- validator-N HEIGHT TIP ROOT < rollback-one.sh
# HEIGHT/TIP/ROOT: the fleet's current converged identity (the pre-upgrade
# baseline if no block was committed since).
#
# Data: safe-rollout makes no per-host data anchor. The data directory is kept
# in place (nothing moved or deleted); the 2026-09-25 executable must verify it
# at the given identity or the script stops before that release is installed.
# If it stops there, the fallback is the signed validator-1 backup at height
# 1050 in the rollout evidence (a manual import that preserves the node's own
# signer state), not this script.
set -euo pipefail
validator="${1:?validator ID required}"
height="${2:?height required}"
tip="${3:?tip required}"
root="${4:?state root required}"
case "$validator" in validator-[0-5]) ;; *) exit 64 ;; esac
old=/opt/postfiat/releases/combined-fastpay-20260925/postfiat-node
config=/etc/postfiat/releases/combined-fastpay-20260925
live="/var/lib/postfiat/$validator"
transport="postfiat-$validator.service"
rpc="postfiat-$validator-rpc.service"
declare -A want_transport=(
  [validator-0]=ef3bc7c26c986fed6df10c828726589ee2a3c7a553e24246b1083458c1d29f36
  [validator-1]=60610dda5eec0d564f178ed031a1deb071ec75afa9fc66a0a3a57c9a1301d1fb
  [validator-2]=f58a9192bff13d94adc9473a450f596fc66b169999b6074128ae7a81c6b9a44a
  [validator-3]=984a369965c00ae9b1708c2f1cdc2dabab4fd68bf61944c20799a0f6b87e2a25
  [validator-4]=f7de3c15575cbd9c3ec742ef60e6d5fda56df59f07ae9e1c9319089cf56b5e28
  [validator-5]=0dbe048eee0f03c397d40cf3f46d329fd237273c37f59570b52de16f4253c7ca
)
declare -A want_rpc=(
  [validator-0]=2b6a8e4484fea98aab0d60b385a39b1d6e7a70858fb1f6f1f53e7e6b3ee667b3
  [validator-1]=bf85d9b920035e1749ce9320a8ec57a87db22982daf74660a3b0bfde98bd2d92
  [validator-2]=eb114f863af73f5eff0163d3a31ea654b1ccb93a931245187f1d42d3d3095c1d
  [validator-3]=60d1a7556eebb77b2422a2e916ca37f284d320d77e1ce4645819e2a7d70c7216
  [validator-4]=abdc7c3b968212137c3425b6312f33d7ec3084bdfdf77aec33fc00e476d07289
  [validator-5]=ee475a3c40814e6ce2ed67ef502c33775e46e1a2f3a2dbea93ffabf36995045b
)
test "$(sha256sum "$old" | cut -d' ' -f1)" = d66cecc36426ce05ced8730b2439a27285c6b404688acd13dc23594b884eabd6
test "$(sha256sum "$config/$transport" | cut -d' ' -f1)" = "${want_transport[$validator]}"
test "$(sha256sum "$config/$rpc" | cut -d' ' -f1)" = "${want_rpc[$validator]}"
test -d "$live"
test -s "$live/.integrity.key"
systemctl stop "$rpc" "$transport"
! systemctl is-active --quiet "$rpc"
! systemctl is-active --quiet "$transport"
runuser -u postfiat -- "$old" verify-finalized-checkpoint --data-dir "$live" >/dev/null
runuser -u postfiat -- "$old" status --data-dir "$live" |
  python3 -c 'import json,sys; s=json.load(sys.stdin); v,h,t,r=sys.argv[1:]; assert s["node_id"]==v and s["block_height"]==int(h) and s["block_tip_hash"]==t and s["state_root"]==r and s["mempool_pending"]==0, "rollback identity differs"' "$validator" "$height" "$tip" "$root"
runuser -u postfiat -- "$old" validate-local-keys --data-dir "$live" --validators 6 --local-only >/dev/null
install -m 0644 "$config/$transport" "/etc/systemd/system/$transport"
install -m 0644 "$config/$rpc" "/etc/systemd/system/$rpc"
"$old" deployment-manifest-verify \
  --manifest-file "$config/deployment-manifest.json" \
  --trusted-publisher-key-file "$config/deployment.public.json" \
  --validator-id "$validator" \
  --validator-bindings-file "$config/$validator.bindings.json" \
  --runtime-binary-file "$old" \
  --runtime-topology-file "$config/topology.json" \
  --runtime-swap-circuit-metadata-file "$config/swap.metadata.json" \
  --runtime-private-egress-circuit-metadata-file "$config/private-egress.metadata.json" >/dev/null
systemctl daemon-reload
systemctl start "$transport"
systemctl start "$rpc"
systemctl is-active "$transport" "$rpc"
# Then run observe-fleet.py from the workstation before any further action.
