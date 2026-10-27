# VR-01: first observations of the vote record defect (2026-10-27)

Read-only observations after the `index-v3-20261027` rollout. No host was changed; no fix is proposed here.
Code references are at `main` `d728f895` (the deployed source). Records:
[release branch `observed/vote-record/`](https://github.com/postfiatorg/postfiatl1v2/tree/release/index-v3-20261027/deployments/index-v3-20261027/observed/vote-record).

## What was observed

- validator-2's record for 1160 (`block-vote-records/height-00000000000000001160.json`) lists validators 1–5
  as `accepted` and validator-0 as `no_answer`, although validator-0's event log shows it accepted both vote
  requests and the batch for 1160.
- validator-0 (proposer of 1158) and validator-1 (proposer of 1159) have no `block-vote-records` directory.
- Every certificate from 1154 to 1160 carried 5 of 6 votes: validator-2 was missing at 1155–1159 and
  validator-0 at 1160.

## The missing records at 1158 and 1159: the rounds ran the old executable

The faucet grant does not use the node services. StakeHub runs `transport-peer-certified-mempool-round` over
SSH on the proposer host with `ce22.runtime_binary` (`StakeHub pft_wallet/ce22.py:109-119`, `:409-418`). The
sheet's §5 keeps `runtime_binary` on the previous release until the last validator is applied, so the rounds for
1154–1159 ran the `exchange-readiness-20261023` executable, which has no record writer. `runtime_binary` pointed
at this release from 1160 on, and the 1160 round wrote a record. In the node both round entry points reach the
writer: the mempool round calls the batch round (`crates/node/src/transport_runtime.rs:4306`), which writes the
record at `:3925`. So this part is the rollout procedure, not the "one of two proposer paths" hypothesis.

## The `no_answer` at 1160: a late answer lost after the deadline

Times on validator-2 (file modification times in the round's artifact directory and data directory):

| Event | Time (UTC) |
|---|---|
| Block proposal written | 11:42:17.17 |
| Prepare vote files: validator-5, 4, 1, 3 | 11:42:18.66, 18.88, 18.99, 19.28 |
| Prepare vote file: validator-0 | 11:42:19.49 |
| Precommit vote file: validator-0 | 11:42:21.52 |
| Block certificate written | 11:42:39.36 |
| Vote record written | 11:43:20.93 |

With `--quorum-early-full-propagation` the round stops collecting at four remote votes
(`transport_runtime.rs:3240`, `:3354-3376`); validator-3's vote at 19.28 completed them, so validator-0's answer
at 19.49 (2.3 s after the proposal) arrived after the quorum and stayed in the channel for the late-vote writer
(`:3375`). The record should therefore list validator-0 as `accepted` with `answered_after_quorum: true`.

The record was written 63.8 s after the proposal, after the 60 s round deadline
(`deadline: vote_requests_start + timeout_ms`, `:3941`). The writer is reached only after the round's local apply
and outbox maintenance (`:3925`). If it is reached after the deadline, its drain loop breaks on
`remaining.is_zero()` (`:2933`) before it reads the outcome that is already queued, and every peer without an
observation is written as `no_answer` with `answered_after_quorum: false` (`:2972-2978`).

**Suspected cause:** `crates/node/src/transport_runtime.rs:2933`, the late-vote loop exits on an expired deadline
without draining outcomes already received. Of the three hypotheses this is the background late-vote writer, with
the deadline handling as its trigger. Not yet established: why the round reached the writer about 40 s after the
certificate (the CLI's report is not kept by StakeHub), and whether validator-2's absence from the 1155–1159
certificates is the same late-answer pattern under the old executable.

## Next

A next-release fix with a test that queues a late answer and reaches the writer after the deadline. Consensus
never reads the record, so the deployed release stays.
