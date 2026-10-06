#!/usr/bin/env bash
# EMERGENCY RECOVERY ONLY: return ONE validator from signer-rotation-20261007 to
# combined-fastpay-20260928 (executable 1f8b332d...). Adapted from
# ../combined-fastpay-20260928/rollback-one.sh. See DEPLOY-SHEET.md "Rollback".
#
# Before running, copy that validator's two combined-fastpay-20260928 units from
# the local 2026-09-28 stage into the host's 2026-09-28 release directory (hashes
# are checked below and against the signed 2026-09-28 manifest):
#   scp ~/.postfiat/deployments/combined-fastpay-20260928/stage/rootfs/etc/systemd/system/postfiat-validator-N{,-rpc}.service \
#       root@HOST:/etc/postfiat/releases/combined-fastpay-20260928/
# Then: ssh root@HOST bash -s -- validator-N HEIGHT TIP ROOT < rollback-one.sh
# HEIGHT/TIP/ROOT: the fleet's current converged identity (the pre-upgrade
# baseline if no block was committed since).
#
# Data: safe-rollout makes no per-host data anchor. The data directory is kept
# in place (nothing moved or deleted); the 2026-09-28 executable must verify it
# at the given identity or the script stops before that release is installed.
# If it stops there, the fallback is the signed validator-1 backup taken on
# 2026-10-07 in the rollout evidence (a manual import that preserves the node's own
# signer state), not this script.
set -euo pipefail
validator="${1:?validator ID required}"
height="${2:?height required}"
tip="${3:?tip required}"
root="${4:?state root required}"
case "$validator" in validator-[0-5]) ;; *) exit 64 ;; esac
old=/opt/postfiat/releases/combined-fastpay-20260928/postfiat-node
config=/etc/postfiat/releases/combined-fastpay-20260928
live="/var/lib/postfiat/$validator"
transport="postfiat-$validator.service"
rpc="postfiat-$validator-rpc.service"
declare -A want_transport=(
  [validator-0]=fe8ff4415d8f64d92fda6fa3b0927b816d3ce82ac8b6cf12a2a2da06002fbf56
  [validator-1]=6194186dfd8f297a4ace7ba7c1ce2a13d578df227a814512927c89a74503cf8d
  [validator-2]=4a483f85a9b8737a023837fc90b0260cfcc3d6a2a1edc7f542c0d38199c3a4e8
  [validator-3]=804bf5e91f6983d002020eddcaa5ac608140a7650c5daafe5d7a099da0d41fe2
  [validator-4]=ccb6754563c54468333c0674cc6414fcd1ad9d2b49bb7c2fe16413f07dac17a4
  [validator-5]=65cad745188cfab137afb2163fea62e5f20c07e8f20392db29bb79240f7de5e7
)
declare -A want_rpc=(
  [validator-0]=f96e4aa67f98b550a940c98a84de8bd0a82c038d13fcca69616fdb98bf49cce6
  [validator-1]=23036dd4e2162d112c5ecdf8a3d488cddf596635dd5ce5fc60841ca2f4828d95
  [validator-2]=394dbc54ff8516590937e38f743137af4dcea153a963b5348facc13836e65e42
  [validator-3]=a49f00c5585b4d8bcbaad42137fb2c8930c81170c78abcf9e20742cca3b552a1
  [validator-4]=d86878297b24cb3128601bf2ad322e9814a28ca21274dc6a8af142689340602f
  [validator-5]=432e761226fe14dc065dcb35a527e1f5636a481121694f43df64fd661c4c6e73
)
test "$(sha256sum "$old" | cut -d' ' -f1)" = 1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a
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
