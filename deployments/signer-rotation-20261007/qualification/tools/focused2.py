"""Focused suites for the changes after the 2026-10-05 full suite (672b707c..tip) and the release's own suites."""
import datetime, json, os, pathlib, subprocess, time
ROOT = pathlib.Path('/home/postfiatchad/.cache/release-signer-rotation-20261007')
REPO = pathlib.Path('/home/postfiatchad/repos/postfiatl1v2')
ENV = os.environ | dict(CARGO_BUILD_JOBS='6', CARGO_TERM_COLOR='never', RUST_TEST_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
T = ['--', '--test-threads=2']
SUITES = [
    ('fix-reproduce-first', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'fastpay_non_signer_view_zero_proposer_anchors_held_effect', *T]),
    ('view-recovery-bin', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--bin', 'postfiat-node', '--', 'finality_view_recovery', 'consensus_v2_timeout_vote_rpc_is_finality_gated_and_durably_signed', 'activated_consensus_v2_transport_survives_failed_view_zero_proposer', '--test-threads=2']),
    ('timeout-votes-lib', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'timeout_votes_reconstruct_hotstuff_timeout_certificate', *T]),
    ('fastpay-committee-lib', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', '--', 'fastpay_payment_safety', 'fastpay_recovery_node', 'fastpay_non_signer_anchor', 'finalized_checkpoint_snapshot_restores_transactional_storage_without_legacy_replay', '--test-threads=2']),
    ('fastpay-types', ['cargo', 'test', '--locked', '-p', 'postfiat-types', '--lib', 'fastpay_recovery_type_tests', *T]),
    ('fastpay-execution', ['cargo', 'test', '--locked', '-p', 'postfiat-execution', '--lib', 'owned_transfer_recovery_tests', *T]),
    ('cobalt-handoff-tests', ['cargo', 'test', '-p', 'postfiat-node', '--lib', '--locked', 'cobalt_handoff::tests', *T]),
    ('live-replay-supply', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'archive_bridge_claim_matches_live_orchard_supply_at_activation', *T]),
    ('types-bridge-policy-update', ['cargo', 'test', '--locked', '-p', 'postfiat-types', '--lib', 'bridge_policy_update', *T]),
    ('execution-bridge-policy-update', ['cargo', 'test', '--locked', '-p', 'postfiat-execution', '--lib', 'bridge_policy_update', *T]),
]
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
results = []
for name, cmd in SUITES:
    start = time.monotonic(); rec = dict(name=name, command=cmd, cwd=str(REPO), started_at=now())
    out = ROOT/'logs'/f'release-{name}.log'
    with out.open('wb') as f:
        code = subprocess.run(cmd, cwd=REPO, env=ENV, stdout=f, stderr=subprocess.STDOUT).returncode
    text = out.read_text(errors='replace')
    summary = [l for l in text.splitlines() if l.startswith('test result:') and ' 0 passed;' not in l] or [l for l in text.splitlines() if ' passed' in l][-1:]
    rec.update(exit_code=code, status='PASS' if code == 0 else 'FAIL', elapsed_seconds=round(time.monotonic()-start, 1), summary=summary, log=f'logs/release-{name}.log', completed_at=now())
    results.append(rec)
    (ROOT/'release-suites.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(), suites=results), indent=2)+'\n')
    print(f'{now()} {rec["status"]} {name} {summary}', flush=True)
