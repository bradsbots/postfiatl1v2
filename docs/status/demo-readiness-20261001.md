# Demo readiness, 2026-10-01

Network `postfiat-wan-devnet-2`, release `combined-fastpay-20260928` (source
`c93b2137`). Observed read-only at 12:05:53Z with
`deployments/combined-fastpay-20260928/demo-preflight.py`. Verdict: **READY WITH
ATTENTION**, with 55 PASS, 5 ATTENTION and 0 FAIL. All five ATTENTION results
come from relays that were started by hand.

## Solid

- **One release on six validators.** All six run `combined-fastpay-20260928`,
  executable `1f8b332d…`. It was qualified on 2026-09-28 (full workspace suite,
  1,487 passed) and deployed the same day. At 12:05:53Z all six agreed at height
  1085, tip `b2c7f04e…`, root `b60665e9…`. The manifest was verified on every
  host, and all mempools were empty.
- **The FastPay effect-anchoring fix is live.** The live check on 2026-09-28
  certified height 1061 at view 0 with validator-5 as proposer, right after a
  FastPay payment.
- **A666 went to Ethereum and back on 2026-10-01.** The export mint is
  `0x3070a3a3…2fab` and the return burn is `0x2368e691…e5bb` (Ethereum block
  26094365). The native import is at height 1077 and the redemption at 1078.
  The supply invariant holds at 31,518,438,511. Validators 0–4 signed both
  certificates. Heights 1079–1085 are later operator tests.
- Sources: the [current state](chain-state-current.md#2026-10-01-fleet-after-the-other-lanes-navcoin-operator-tests)
  and the other lane's [handoff](../handoffs/2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md#update-0335-utc).

## Fragile

- **Relays 28701 and 28702 do not survive a reboot.** On validators 0 and 2–5
  they were started by hand from `/tmp/a666-https-jsonrpc-loopback-proxy.py`,
  and that file no longer exists. On validator-1, 28701 is a systemd unit and
  28702 does not exist.
- **PublicNode refuses archive reads.** 28701 forwards to PublicNode. Since
  2026-10-01 it returns HTTP 403 for archive `eth_getCode`. Only 28703, the
  unit-managed relay to `eth.drpc.org`, answers archive reads. It passed on all
  six hosts. All archive reads now depend on that one provider. The A666
  scripts on main default to 28703.
- **The bridge committee has no spare.** Ethereum checkpoint signing needs all
  five of validators 0–4. Validator-5 is outside both signer groups: its
  checkpoint key is not in the bridge committee, and it is not an eligible
  FastPay signer. If any of validators 0–4 is down, Ethereum transfers stop.
  [Decision proposal](../review/validator-5-signer-committees-decision-proposal-20261001.md).
- **RPC accept-budget restarts leave 5-second gaps.** Each RPC process exits
  after it has accepted 10,000 connections (`--max-requests 10000`), and systemd
  restarts it 5 seconds later. Restarts today:
    - validator-0 at 07:40:35–40Z;
    - validator-5 at 08:28:25–31Z;
    - validator-2, restarted at 11:40:39Z (found by the preflight).

  The end-of-run report of the validator-0 process that exited at 07:40:35Z is
  in `rpc-stdout.log`. It shows `"max_requests": 10000` and
  `"request_count": 129838`. `rpc-stderr.log` was last written at 01:01:03Z. The
  request count includes several requests on each kept-alive connection. The
  budget counts connections, and the report has no connection counter. In
  `c93b2137` the report is printed only after the accept loop stops at 10,000
  connections, so the budget was reached. During each gap, a demo request to
  that RPC port fails. Each run also adds most of a 46 MB report to
  `rpc-stdout.log`, and no logrotate rule covers that file.
- **The work server's disk** was full this morning. At 12:06Z it had 94 GB
  free. The validator hosts have 17.1–28.9 GB free.

## Before the event

| Step | Duration | Validator restart |
|---|---|---|
| Replace the hand-started 28701 and 28702 relays on validators 0 and 2–5 with systemd units. Add 28702 on validator-1. Use the same ports and upstreams, and the script already installed for the 28703 unit (`/opt/postfiat/route-tools/navcoin-20260907/https-jsonrpc-loopback-proxy.py`). Each port is down for a few seconds. | 20 min, six hosts | None |
| Make no change to the RPC accept budget before the event. Changing it changes a signed unit file, which needs a release. Demo clients should retry once after 6 seconds. | 0 | None |
| Freeze validators 0–4 during the event: no deployments and no maintenance. `needrestart` does not restart PostFiat units after the daily upgrade (06:00–07:00Z). | 0 | None |
| Run the preflight before each demo. | about 10 s | None |

**Go needed from the other lane:** one 20-minute window for the relay units
on the six hosts.

**Before each demo, the other lane runs** this command on the work server,
which holds the RPC tunnels and root SSH:
`python3 deployments/combined-fastpay-20260928/demo-preflight.py`. Optionally,
add `--wallet-url <public wallet URL>`. Go ahead on READY, or on ATTENTION
caused only by the relay start method. Stop on FAIL.

## Preflight, 12:05:53Z

```text
Check                Scope        Result     Detail
ledger agreement     fleet        PASS       6/6 at height 1085, tip b2c7f04e, root b60665e9
release              validator-0  PASS       combined-fastpay-20260928 c93b2137 1f8b332d, manifest verified
mempool              validator-0  PASS       0 pending
units                validator-0  PASS       validator up 3d4h restarts 0; rpc up 4h25m restarts 1; aux 2/2 active
relay 28703 archive  validator-0  PASS       eth_getCode @26094220: HTTP 200, 2186 B
relays 28701/28702   validator-0  ATTENTION  28701 ethereum-rpc.publicnode.com hand-started (session-18776.scope), script deleted; 28702 eth.drpc.org hand-started (session-20814.scope), script deleted
checkpoint signing   validator-0  PASS       /var/lib/postfiat/validator-0/validator_keys.json present; 55 records, newest 2026-10-01 02:25Z
rpc readiness        validator-0  PASS       ready=True degraded=False event_log_writable=True finality_key=True telemetry_failures=0
disk /               validator-0  PASS       17.1 GB free (threshold 10 GB)
logrotate            validator-0  PASS       postfiat-validator-events, postfiat-rpc-events
apt-daily-upgrade    validator-0  PASS       service inactive
release              validator-1  PASS       combined-fastpay-20260928 c93b2137 1f8b332d, manifest verified
mempool              validator-1  PASS       0 pending
units                validator-1  PASS       validator up 3d4h restarts 0; rpc up 3d4h restarts 0; aux 2/2 active
relay 28703 archive  validator-1  PASS       eth_getCode @26094220: HTTP 200, 2186 B
relays 28701/28702   validator-1  PASS       28701 ethereum-rpc.publicnode.com navcoin-ethereum-rpc-proxy-20260907.service; 28702 not listening
checkpoint signing   validator-1  PASS       /var/lib/postfiat/validator-1/validator_keys.json present; 55 records, newest 2026-10-01 02:49Z
rpc readiness        validator-1  PASS       ready=True degraded=False event_log_writable=True finality_key=True telemetry_failures=0
disk /               validator-1  PASS       19.5 GB free (threshold 10 GB)
logrotate            validator-1  PASS       postfiat-validator-events, postfiat-rpc-events
apt-daily-upgrade    validator-1  PASS       service inactive
release              validator-2  PASS       combined-fastpay-20260928 c93b2137 1f8b332d, manifest verified
mempool              validator-2  PASS       0 pending
units                validator-2  PASS       validator up 3d4h restarts 0; rpc up 0h25m restarts 1; aux 2/2 active
relay 28703 archive  validator-2  PASS       eth_getCode @26094220: HTTP 200, 2186 B
relays 28701/28702   validator-2  ATTENTION  28701 ethereum-rpc.publicnode.com hand-started (session-19228.scope), script deleted; 28702 eth.drpc.org hand-started (session-29943.scope), script deleted
checkpoint signing   validator-2  PASS       /var/lib/postfiat/validator-2/validator_keys.json present; 55 records, newest 2026-10-01 02:50Z
rpc readiness        validator-2  PASS       ready=True degraded=False event_log_writable=True finality_key=True telemetry_failures=0
disk /               validator-2  PASS       24.2 GB free (threshold 10 GB)
logrotate            validator-2  PASS       postfiat-validator-events, postfiat-rpc-events
apt-daily-upgrade    validator-2  PASS       service inactive
release              validator-3  PASS       combined-fastpay-20260928 c93b2137 1f8b332d, manifest verified
mempool              validator-3  PASS       0 pending
units                validator-3  PASS       validator up 3d4h restarts 0; rpc up 3d4h restarts 0; aux 2/2 active
relay 28703 archive  validator-3  PASS       eth_getCode @26094220: HTTP 200, 2186 B
relays 28701/28702   validator-3  ATTENTION  28701 ethereum-rpc.publicnode.com hand-started (session-14185.scope), script deleted; 28702 eth.drpc.org hand-started (session-15962.scope), script deleted
checkpoint signing   validator-3  PASS       /var/lib/postfiat/validator-3/validator_keys.json present; 54 records, newest 2026-10-01 02:50Z
rpc readiness        validator-3  PASS       ready=True degraded=False event_log_writable=True finality_key=True telemetry_failures=0
disk /               validator-3  PASS       28.9 GB free (threshold 10 GB)
logrotate            validator-3  PASS       postfiat-validator-events, postfiat-rpc-events
apt-daily-upgrade    validator-3  PASS       service inactive
release              validator-4  PASS       combined-fastpay-20260928 c93b2137 1f8b332d, manifest verified
mempool              validator-4  PASS       0 pending
units                validator-4  PASS       validator up 3d4h restarts 0; rpc up 3d4h restarts 0; aux 2/2 active
relay 28703 archive  validator-4  PASS       eth_getCode @26094220: HTTP 200, 2186 B
relays 28701/28702   validator-4  ATTENTION  28701 ethereum-rpc.publicnode.com hand-started (session-14081.scope), script deleted; 28702 eth.drpc.org hand-started (session-15864.scope), script deleted
checkpoint signing   validator-4  PASS       /var/lib/postfiat/validator-4/validator_keys.json present; 55 records, newest 2026-10-01 02:51Z
rpc readiness        validator-4  PASS       ready=True degraded=False event_log_writable=True finality_key=True telemetry_failures=0
disk /               validator-4  PASS       24.2 GB free (threshold 10 GB)
logrotate            validator-4  PASS       postfiat-validator-events, postfiat-rpc-events
apt-daily-upgrade    validator-4  PASS       service inactive
release              validator-5  PASS       combined-fastpay-20260928 c93b2137 1f8b332d, manifest verified
mempool              validator-5  PASS       0 pending
units                validator-5  PASS       validator up 3d4h restarts 0; rpc up 3h37m restarts 1; aux 2/2 active
relay 28703 archive  validator-5  PASS       eth_getCode @26094220: HTTP 200, 2186 B
relays 28701/28702   validator-5  ATTENTION  28701 ethereum-rpc.publicnode.com hand-started (session-14182.scope), script deleted; 28702 eth.drpc.org hand-started (session-15946.scope), script deleted
rpc readiness        validator-5  PASS       ready=True degraded=False event_log_writable=True finality_key=True telemetry_failures=0
disk /               validator-5  PASS       27.8 GB free (threshold 10 GB)
logrotate            validator-5  PASS       postfiat-validator-events, postfiat-rpc-events
apt-daily-upgrade    validator-5  PASS       service inactive
VERDICT: READY WITH ATTENTION - 55 PASS, 5 ATTENTION, 0 FAIL (2026-10-01T12:05:53Z, 6 s)
```
