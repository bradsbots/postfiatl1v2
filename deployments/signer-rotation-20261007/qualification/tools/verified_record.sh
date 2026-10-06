#!/usr/bin/env bash
# Rehearse the deployment_manifest_verified status field (1bb15a78) against the signed stage. Local only.
set -euo pipefail
R=signer-rotation-20261007
S=$HOME/.postfiat/deployments/$R/stage; C=$S/rootfs/etc/postfiat/releases/$R
B=$S/rootfs/opt/postfiat/releases/$R/postfiat-node
Q=$HOME/.cache/release-signer-rotation-20261007; O=$Q/verified-record; mkdir -p $O
DATA=$HOME/.cache/release-repair-20260928/canary-backup/signed-import   # disposable 2026-09-28 canary import, height 1050
status() { POSTFIAT_DEPLOYMENT_MANIFEST=$C/deployment-manifest.json "$@" "$B" status --data-dir $DATA; }
field() { python3 -c 'import json,sys; s=json.load(sys.stdin); print(json.dumps({k: s.get(k) for k in ("block_height","state_root","deployment_manifest_sha256","deployment_manifest_verified")}))'; }
echo "1. no record variable:"; status env | field
echo "2. record variable set, record absent:"; status env POSTFIAT_DEPLOYMENT_VERIFIED_RECORD=$O/rpc.deployment-verified.json | field
POSTFIAT_DEPLOYMENT_VERIFIED_RECORD=$O/rpc.deployment-verified.json "$B" deployment-manifest-verify \
  --manifest-file $C/deployment-manifest.json --trusted-publisher-key-file $C/deployment.public.json > $O/verify.json
echo "3. after deployment-manifest-verify wrote the record:"; status env POSTFIAT_DEPLOYMENT_VERIFIED_RECORD=$O/rpc.deployment-verified.json | field
cp $O/rpc.deployment-verified.json $O/tampered.json; sed -i 's/"manifest_sha256": "./"manifest_sha256": "0/' $O/tampered.json
echo "4. record with a changed manifest hash:"; status env POSTFIAT_DEPLOYMENT_VERIFIED_RECORD=$O/tampered.json | field
