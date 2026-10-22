from runner import *
import re
while True:
    b = ROOT/'node-builds.json'
    if b.exists() and json.loads(b.read_text()).get('result') not in ('RUNNING', 'INCOMPLETE'): break
    time.sleep(2)
time.sleep(20)  # let the background full suite start first
stages = []
TT = '/home/postfiatchad/.cache/release-repair-20260918/test-target'
testenv = dict(CARGO_TARGET_DIR=TT, CARGO_PROFILE_TEST_OPT_LEVEL='2', CARGO_PROFILE_TEST_DEBUG_ASSERTIONS='true', CARGO_PROFILE_TEST_OVERFLOW_CHECKS='true')
def gate(name, cmd, env=None, timeout=300, optional=False, purpose=None):
    rec = run(name, cmd, extra=env, timeout=timeout)
    if purpose: rec['purpose'] = purpose
    if optional and rec['status'] in ('TIMEOUT', 'NOT_RUN_TIMEBOX'):
        rec.update(status='DEFERRED', reason=f"local budget ({rec['status']}) expired; no passing result claimed")
    if 'test' in cmd and rec['status'] in ('PASS', 'FAIL'):
        text = pathlib.Path(rec['stdout']).read_text(errors='replace')
        rec['tests_passed'] = sum(map(int, re.findall(r'test result: \w+\. (\d+) passed;', text)))
        rec['tests_failed'] = sum(map(int, re.findall(r'passed; (\d+) failed;', text)))
        rec['tests_ignored'] = sum(map(int, re.findall(r'failed; (\d+) ignored;', text)))
        rec['tests_run'] = sorted(set(re.findall(r'^test (\S+) \.\.\. ok$', text, re.M)))
        if rec['status'] == 'PASS' and rec['tests_passed'] == 0: rec.update(status='FAIL', reason='test command selected zero passing tests')
    write(ROOT/'reports'/f'{name}.json', rec)
    stages.append(rec)
    write(ROOT/'software-gates.json', dict(source_commit=SOURCE, stages=stages, workspace_tests='full workspace suite runs in the background; see reports/full-workspace-tests.json', updated_at=now()))
    return rec
T = ['--', '--test-threads=2']
gate('fix-reproduce-first', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'fastpay_non_signer_view_zero_proposer_anchors_held_effect', *T], testenv, timeout=1800, purpose='fix: validator-5 (non-signer) proposes at view 0 right after a FastPay payment; the block certifies at view 0 with the effect anchored; identical tip, root and ledger on all six')
gate('view-recovery-bin', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--bin', 'postfiat-node', '--', 'finality_view_recovery', 'consensus_v2_timeout_vote_rpc_is_finality_gated_and_durably_signed', 'activated_consensus_v2_transport_survives_failed_view_zero_proposer', '--test-threads=2'], testenv, timeout=1800, optional=True, purpose='timeout-vote RPC, view-recovery chunk envelope, failed view-0 proposer skipped by a timeout certificate (n4, n6)')
gate('timeout-votes-lib', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'timeout_votes_reconstruct_hotstuff_timeout_certificate', *T], testenv, timeout=1500, optional=True, purpose='timeout votes reconstruct a HotStuff timeout certificate')
gate('fastpay-committee-lib', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', '--', 'fastpay_payment_safety', 'fastpay_recovery_node', 'fastpay_non_signer_anchor', 'finalized_checkpoint_snapshot_restores_transactional_storage_without_legacy_replay', '--test-threads=2'], testenv, timeout=900, optional=True, purpose='FastPay committee signer retention, non-signer held effects, effect restore, rotated sixth validator anchor, recovery node journal, finalized-checkpoint restore')
gate('node-fastpay', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'fastpay', *T], testenv, timeout=900, optional=True, purpose='all node lib tests whose path contains fastpay')
gate('format', ['cargo', 'fmt', '--all', '--', '--check'])
gate('proof-input-inventory', ['scripts/test-proof-public-input-inventory'])
gate('workspace-check', ['cargo', 'check', '--workspace', '--locked'], dict(CARGO_TARGET_DIR=TT), timeout=1200)
gate('workspace-clippy', ['cargo', 'clippy', '--workspace', '--all-targets', '--locked', '--', '-D', 'warnings'], dict(CARGO_TARGET_DIR=TT), timeout=1500, optional=True)
gate('fastpay-types', ['cargo', 'test', '--locked', '-p', 'postfiat-types', '--lib', 'fastpay_recovery_type_tests', *T], testenv, optional=True)
gate('fastpay-execution', ['cargo', 'test', '--locked', '-p', 'postfiat-execution', '--lib', 'owned_transfer_recovery_tests', *T], testenv, optional=True)
gate('cobalt-handoff-tests', ['cargo', 'test', '-p', 'postfiat-node', '--lib', '--locked', 'cobalt_handoff::tests', *T], testenv, optional=True)
gate('live-replay-supply', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'archive_bridge_claim_matches_live_orchard_supply_at_activation', *T], testenv, optional=True)
gate('warm-latency', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--bin', 'postfiat-node', 'fastswap_service::tests::persistent_wallet_driver_meets_isolated_warm_latency_gate', '--', '--ignored', '--exact', '--nocapture', '--test-threads=2'], testenv, optional=True)
write(ROOT/'software-complete.json', dict(completed_at=now()))
