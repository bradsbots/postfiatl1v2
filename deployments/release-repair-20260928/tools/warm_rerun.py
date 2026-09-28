from runner import *
import re
TT = '/home/postfiatchad/.cache/release-repair-20260918/test-target'
testenv = dict(CARGO_TARGET_DIR=TT, CARGO_PROFILE_TEST_OPT_LEVEL='2', CARGO_PROFILE_TEST_DEBUG_ASSERTIONS='true', CARGO_PROFILE_TEST_OVERFLOW_CHECKS='true')
rec = run('warm-latency-rerun', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--bin', 'postfiat-node', 'fastswap_service::tests::persistent_wallet_driver_meets_isolated_warm_latency_gate', '--', '--ignored', '--exact', '--nocapture', '--test-threads=2'], extra=testenv, timeout=1500, deadline=DEADLINE-datetime.timedelta(minutes=6))
rec['purpose'] = 'rerun of warm-latency with a longer budget after the first attempt timed out while still compiling'
if rec['status'] in ('PASS', 'FAIL'):
    text = pathlib.Path(rec['stdout']).read_text(errors='replace')
    rec['tests_passed'] = sum(map(int, re.findall(r'test result: \w+\. (\d+) passed;', text)))
    rec['tests_failed'] = sum(map(int, re.findall(r'passed; (\d+) failed;', text)))
if rec['status'] in ('TIMEOUT', 'NOT_RUN_TIMEBOX'): rec.update(status='DEFERRED', reason=f"local budget ({rec['status']}) expired; no passing result claimed")
write(ROOT/'reports/warm-latency-rerun.json', rec)
