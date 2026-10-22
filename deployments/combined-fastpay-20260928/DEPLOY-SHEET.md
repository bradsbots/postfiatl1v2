# Deploy sheet — combined-fastpay-20260928

Exact commands used on 2026-09-28 on the signing workstation, following the
[September 25 sheet](../combined-fastpay-20260925/DEPLOY-SHEET.md) and the
[runbook](../../docs/runbooks/safe-validator-rollout.md). Keys are used by path
only; no key material is printed, copied to a host or committed.

**Status: deployed** (`status=DEPLOYED`, 2026-09-28 08:09:24Z). The six applies
ran 07:40–08:05Z. Results are in the [README](README.md#rollout-2026-09-28).

```bash
D=~/.postfiat/deployments/combined-fastpay-20260928   # local, not in Git
S=$D/stage; E=$D/evidence; R=combined-fastpay-20260928
C=$S/rootfs/etc/postfiat/releases/$R; U=$S/rootfs/etc/systemd/system
B=$S/rootfs/opt/postfiat/releases/$R/postfiat-node
PACKET=deployments/combined-fastpay-20260928
```

## 1. Before state (read-only)

`apt-daily-upgrade.timer` had already run today on all six hosts
(06:00–06:55Z), with the next run on 2026-09-29 and no upgrade running. The six RPC
tunnels `127.0.0.1:27650..27655` were already up. No other rollout or session
was active on the fleet.

```bash
python3 $PACKET/observe-fleet.py --output $PACKET/observed/before.json
```

The chain was still at 1050 with root `13d9e652…`, so the stage, signed
manifest, rollout state and signed backup prepared by the qualification step
([commands](../release-repair-20260928/canary-backup/prepare_rollout.sh)) were
reused. The observer now checks the six validators concurrently; each check is
unchanged from September 25.

## 2. Stage and local preflight

The stage was generated at 06:00Z with
`deployment-validator-units-stage --release-id $R` from the executable
`~/.cache/release-repair-20260928/binaries/candidate-1` (`1f8b332d…`,
rechecked: both builds and the stage copy match). The live
`combined-fastpay-20260925` layout on validator-0 (release directory and both
units, read with `ssh cat` into `$D/live-layout-validator-0/`) is byte-identical
to the stage after the release-ID change.

```bash
python3 $PACKET/local-preflight.py --stage $S --require-signed > $E/local-preflight-signed.json
```

PASS: 33 generated files match `rootfs/`, four circuit artifacts, signed gate
for all six.

## 3. Sign and verify

The manifest was signed at 06:00:14Z with the command from the September 25
sheet §3, with `--deployment-id $R`, `--git-revision c93b2137…`,
`--valid-from-unix 1790575214 --valid-until-unix 1822111514` and publisher key
`~/.postfiat/deployments/fastpay-committee-20260925-r4/keys/deployment-publisher.key.json`.
SHA-256 `d2fdb687…`. The inputs are in
[manifest-input.unsigned.json](manifest-input.unsigned.json) and match the
signed manifest field by field. The local preflight above ran
`deployment-manifest-verify` for all six validators: PASS.

## 4–5. Preflight and signed canary backup

These ran at 06:00–06:02Z. The preflight passed: six-way agreement at 1050, six
signer rosters, 0 deletions, order 1, 0, 2, 3, 4, 5. The backup
(`$E/pre-rollout-backup/backup-signed`, manifest `a40d6a99…`) was taken from
validator-1. The commands are in
[prepare_rollout.sh](../release-repair-20260928/canary-backup/prepare_rollout.sh).
The backup was verified again today before the first apply:

```bash
K=~/.postfiat/deployments/cobalt-activation-8694b99d/snapshot-keys
X=~/.cache/deploy-combined-fastpay-20260928/backup-reverify
$B snapshot-import-signed-finalized-checkpoint --data-dir $X --snapshot-dir $E/pre-rollout-backup/backup-signed \
  --trusted-publisher-key-file $K/snapshot-publisher.public.json --node-id validator-1
$B verify-finalized-checkpoint --data-dir $X     # verified: true
$B status --data-dir $X                          # 1050, tip 03a24230…, root 13d9e652…
```

## 6. One validator at a time

For each validator in order, only after the previous check passed:

```bash
scripts/postfiat-safe-rollout apply-next --state-file $E/rollout-state.json > $E/apply-N.json
(cd ~/repos/StakeHub && .venv/bin/pft faucet testing --asset PFT --amount 1000000) > $E/grant-after-<validator>.out
python3 $PACKET/observe-fleet.py --stage $S --applied validator-1[,validator-0,...] \
  --output $PACKET/observed/after-<validator>.json
```

The canary also had a health read before its grant
([after-validator-1-apply.json](observed/after-validator-1-apply.json)). Each
grant's certificate (height, view, proposer, voters) was read from all six
nodes with the `blocks` RPC and had to be identical on all six.

## 7. Live fix check

The check needs a FastPay payment followed by a grant at a height where
validator-5 is the view-0 proposer. The proposer is
`validators[(height + view) mod 6]`
(`crates/ordering_fast/src/lib.rs`, `leader_for_view`); heights 1051–1056
confirmed this. After the sixth grant the chain was at 1056, so validator-5's
next turn is 1061. That needs four positioning grants (1057–1060), more than
the three allowed, so the check was recorded as not run
([live-fix-check.json](observed/live-fix-check.json)). No FastPay payment was
made.

## 8. After state

```bash
python3 $PACKET/observe-fleet.py --stage $S \
  --applied validator-1,validator-0,validator-2,validator-3,validator-4,validator-5 \
  --output $PACKET/observed/after.json
```

## Rollback (one validator, emergency only)

`safe-rollout` has no rollback subcommand and makes no per-host data anchor.
Each host keeps the `combined-fastpay-20260925` executable (`d66cecc3…`) and
release directory. Its units are in the local September 25 stage.
[rollback-one.sh](rollback-one.sh) stops the validator and checks the
September 25 executable against the data in place at the given identity. It
then reinstalls the September 25 units, verifies the signed September 25
manifest and restarts:

```bash
scp ~/.postfiat/deployments/combined-fastpay-20260925/stage/rootfs/etc/systemd/system/postfiat-validator-N{,-rpc}.service \
  root@HOST:/etc/postfiat/releases/combined-fastpay-20260925/
ssh root@HOST bash -s -- validator-N HEIGHT TIP ROOT < $PACKET/rollback-one.sh
```

If the September 25 executable cannot verify the data in place, the script
stops before installing anything. The remaining fallback is the signed
validator-1 backup at height 1050 (`$E/pre-rollout-backup/backup-signed`).
Rollback was not needed. validator-1 had 2.96 GB free after the rollout.
