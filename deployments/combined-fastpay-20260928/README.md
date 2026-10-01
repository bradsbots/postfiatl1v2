# FastPay effect-anchoring release deployment — 2026-09-28

Release `combined-fastpay-20260928` is the deployed September 25 code
(`f60e9639`) plus the FastPay effect-anchoring fix: a registered validator
that cannot sign now holds certificate-verified FastPay effects, so its own
proposal anchors them ([design](../../docs/status/fastpay-effect-anchoring-fix-20260928.md)).
Qualified at `c93b2137` ([qualification](../release-repair-20260928/README.md), PASS,
including the full workspace suite). Executable
`1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a` (two identical
clean builds, rechecked before staging). Rollback release:
`combined-fastpay-20260925` (`d66cecc3…`). Identities: [RELEASE-ID.txt](RELEASE-ID.txt).

## Status

**Deployed** (`status=DEPLOYED`, 2026-09-28 08:09:24Z). All six validators run
`combined-fastpay-20260928` (executable `1f8b332d…`, build `c93b2137`, signed
manifest `d2fdb687…`) and agree at height 1056, tip `30ebdccd…`, root
`22576546…` ([after.json](observed/after.json)). The live fix check passed
on 2026-09-28 (see below).

| Step | Result | Evidence |
|---|---|---|
| 1. Before state, read-only | PASS: six on `combined-fastpay-20260925` (`d66cecc3…`, build `f60e9639`, manifest `7a682ffe…`), height 1050, tip `03a24230…`, root `13d9e652…`, mempools empty; `apt-daily-upgrade` had run today on all six (06:00–06:55Z) | [before.json](observed/before.json) |
| 2. Stage, local preflight | PASS: prepared stage reused (chain unchanged); the live validator-0 layout equals the stage after the release-ID change; 33 generated files, four circuit artifacts | DEPLOY-SHEET §2 |
| 3. Sign, verify ×6 | PASS: manifest `d2fdb687…`, publisher `pfc531e0…`, `deployment-manifest-verify` passes for all six | DEPLOY-SHEET §3 |
| 4. `postfiat-safe-rollout preflight` | PASS (06:00Z, reused): six-way agreement at 1050, six signer rosters valid, 0 deletions, order 1, 0, 2, 3, 4, 5 | local `rollout-state.json` (`4d3a7586…` before, `dde65f5b…` after) |
| 5. Signed canary backup, validator-1 | PASS: height 1050, root `13d9e652…`, signed manifest `a40d6a99…`, snapshot publisher `pf4ebb80…`; re-imported and checkpoint-verified again at 07:38Z | local `pre-rollout-backup/`, DEPLOY-SHEET §4–5 |
| 6. Applies, one at a time | PASS: six `apply-next` runs, exit 0, each followed by one faucet grant and a full observer check | table below, [rollout-record.json](observed/rollout-record.json) |
| 7. Live fix check | PASS (08:36Z, second attempt): after a FastPay payment signed by validators 0–4, height 1061 certified at view 0 with validator-5 as proposer and the effect anchored; six-way agreement | [live-fix-check.json](observed/live-fix-check.json) |
| 8. After state | PASS: six on the new release, all 12 validator and RPC processes on `1f8b332d…`, manifest verified on every host, height 1056 | [after.json](observed/after.json) |

## Rollout, 2026-09-28

Each `apply-next` did four things. It verified the signed manifest on the host,
restarted the validator and RPC units on the new executable, verified the
finalized checkpoint and checked six-way convergence. Then one 1 PFT faucet
grant (fee 32 atoms) went from the faucet account `pfcd4cc8…` to the `testing`
wallet (`pf6395ef…`) through StakeHub's `pft faucet` and made the next block.
Each grant was verified on all six, certified at view 0 and returned the same
block on all six. After each grant, [observe-fleet.py](observe-fleet.py)
checked units, running executables, the manifest signature on every host and
six-node agreement. There were never two applies at once.

| Validator | Applied (UTC) | Grant height, proposer | Certificate voters (quorum 5) | Check after grant |
|---|---|---|---|---|
| validator-1 (canary) | 07:40:50 | 1051, validator-1 | 0, 1, 3, 4, 5 | PASS, root `03427781…` ([after-validator-1](observed/after-validator-1.json)) |
| validator-0 | 07:45:59 | 1052, validator-2 | 1, 2, 3, 4, 5 | PASS, root `c971dce4…` ([after-validator-0](observed/after-validator-0.json)) |
| validator-2 | 07:54:31 | 1053, validator-3 | 0, 1, 3, 4, 5 | PASS, root `e6bf5a9a…` ([after-validator-2](observed/after-validator-2.json)) |
| validator-3 | 07:58:08 | 1054, validator-4 | 0, 1, 3, 4, 5 | PASS, root `8ee8314d…` ([after-validator-3](observed/after-validator-3.json)) |
| validator-4 | 08:01:15 | 1055, validator-5 | 1, 2, 3, 4, 5 | PASS, root `d86d3931…` ([after-validator-4](observed/after-validator-4.json)) |
| validator-5 | 08:05:26 | 1056, validator-0 | 0, 1, 2, 3, 4 | PASS, root `22576546…` ([after-validator-5](observed/after-validator-5.json)) |

The six grants were block triggers, 1 PFT each at heights 1051–1056
(6 PFT plus 192 atoms of fees; faucet 85.995400 → 79.995208 PFT). Nothing
else moved.

## Live fix check, 2026-09-28

The first attempt (08:08Z) was not run: it would have needed four
positioning grants, more than the three allowed. The second attempt ran
08:28–08:38Z with a throwaway sender wallet `dravlic-fixcheck-20260928`
(`pf8cb695…`), as on 2026-09-25. The proposer is
`validators[(height + view) mod 6]` (`crates/ordering_fast/src/lib.rs`,
`leader_for_view`). Each height below was read from the `blocks` data of all
six validators and was identical on all six.

| Height | Step | Proposer, view | Certificate voters |
|---:|---|---|---|
| 1057 | Grant 1 PFT to the throwaway wallet | validator-1, 0 | 0, 1, 3, 4, 5 |
| 1058 | Grant 1 PFT to `testing` | validator-2, 0 | 1, 2, 3, 4, 5 |
| 1059 | Grant 1 PFT to `testing` | validator-3, 0 | 0, 1, 3, 4, 5 |
| 1060 | FastPay wrap, 1,001 atoms into one coin | validator-4, 0 | 0, 1, 3, 4, 5 |
| — | FastPay payment, 0.001 PFT to `testing` (no block) | — | signed by 0–4 |
| **1061** | **Check: grant 1 PFT to `testing`** | **validator-5, 0** | 0, 1, 2, 4, 5 |
| 1062 | Return 0.998956 PFT to the faucet | validator-0, 0 | 0, 1, 3, 4, 5 |

All six signed the precommit certificate at every height.

- **Payment** (08:33Z): validators 0–4 signed the certificate and returned
  `postfiat-fastpay-apply-ack-v1` acknowledgements. The proxy lists validator-5
  as pending, because it counts only signed acknowledgements; the held receipt
  itself does not reach the wallet. All six validators' FastPay journals then
  held the same effect: identical files with lock `0708497d…`, certificate
  digest `53a09e9a…`, decided at 1060. Before the payment, validator-5's journal
  still held a July effect instead. The new 0.001 PFT coin `e48ac3ec…` was
  visible on all six, and the spent input was gone on all six.
- **1061**: certified at view 0 by validator-5, with no view change and no
  timeout votes. Its `fastpay_pre_state_effects` contains that effect (lock
  `0708497d…`, input `8a7442df…`) on all six. Tip `ab20666b…` and root
  `20d21e0e…` are the same on all six. Compare 1043 on 2026-09-25, before the
  fix: after a payment, the same situation certified only at view 1, through
  validator-0.
- **Funds**: the faucet held 79.995208 PFT before and 76.994036 PFT after
  (four grants of 1 PFT plus 32-atom fees, less the 0.998956 PFT returned).
  The throwaway wallet ends with the 10-atom account reserve and no FastPay
  coins. Its key material and passphrase file were deleted at 08:38Z. It was
  never registered in StakeHub.

Record: [live-fix-check.json](observed/live-fix-check.json).

## Notes

- During the rollout, StakeHub's `~/.pft/config.toml` named the
  `combined-fastpay-20260925` executable as `runtime_binary`, so the grants
  at 1051–1056 ran that CLI on the proposer host. Before the live fix check,
  `runtime_binary`, `topology_file` and `local_node_binary` were pointed at
  `combined-fastpay-20260928`. The local copy was `1f8b332d…` before and after
  copying, and the old config is kept as `config.toml.bak-20260928b`.
- The wallet proxy counts only signed acknowledgements. It still reports
  validator-5 as not applied for FastPay payments and retries it; each retry
  returns the same held receipt ([design](../../docs/status/fastpay-effect-anchoring-fix-20260928.md)).

## Demo preflight

`python3 demo-preflight.py` answers in about 10 seconds whether the fleet is
ready for a demo. It is read-only and uses only the Python standard library. Run
it on the work server that holds the RPC tunnels `127.0.0.1:27650`–`27655` and
root SSH to the six hosts. It reuses the checks in `observe-fleet.py`: status
identity, running executable hashes, `deployment-manifest-verify` and
`apt-daily-upgrade`. It adds the following checks:

- six-way agreement on height, tip and root;
- validator and RPC unit state, uptime and `NRestarts`;
- an archive `eth_getCode` through relay 28703, and how 28701 and 28702 were started;
- whether the checkpoint key file exists on validators 0–4 (it never reads the
  file), and the time of the newest signing record;
- the RPC readiness flags;
- free disk space (ATTENTION under 10 GB);
- the two logrotate rules.

It prints PASS, ATTENTION or FAIL for each check and a one-line verdict. The
exit code is 0 for READY, 1 for ATTENTION and 2 for FAIL. `--json` prints the
full result. `--wallet-url URL` adds an HTTP GET that reports only the status
code. Readiness note: [demo-readiness-20261001](../../docs/status/demo-readiness-20261001.md).

## Caveats

1. **No per-host data copies.** The rollout tool does not copy validator data.
   Rollback is the September 25 executable and unit files with the data in
   place, verified by that executable first ([rollback-one.sh](rollback-one.sh)).
   The signed 1050 backup is the fallback. Rollback was not needed.
   validator-1 had 2.96 GB free after the rollout.
2. **Leftovers on validator-1.** The backup step left an unsigned snapshot
   (under `/var/lib/postfiat/pre-rollout-snapshots/`) and a copy of the new
   executable beside it. Nothing was deleted.

## Contents

- [DEPLOY-SHEET.md](DEPLOY-SHEET.md): the exact commands, in order, and the rollback.
- `rootfs/etc/`: the 33 generated files (12 units, 12 environment files, six
  runtime bindings, topology, both circuit metadata files). They are identical
  to the September 25 files after the release-ID change.
- `stage-report.template.json`, `validator-bindings.signing.template.json`: the
  generated stage files with the local prefix replaced by `@STAGE@`.
- [manifest-input.unsigned.json](manifest-input.unsigned.json): the reviewed
  inputs of the signed manifest (validator-0's RPC unit and environment at the
  top level, as before).
- [local-preflight.py](local-preflight.py), [observe-fleet.py](observe-fleet.py),
  [rollback-one.sh](rollback-one.sh): adapted from `../combined-fastpay-20260925/`.
- `observed/`: before, per-validator and after observations, the
  [rollout record](observed/rollout-record.json) and the
  [live fix check record](observed/live-fix-check.json).
- [publication-gates.json](publication-gates.json).
- [inventory.txt](inventory.txt): the rollout inventory (SHA-256 `6c11341d…`).

Not in Git: private keys, the signed stage, rollout state and backup under
`~/.postfiat/deployments/combined-fastpay-20260928/` on the signing workstation.
No key material is in this directory.
