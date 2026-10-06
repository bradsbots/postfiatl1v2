"""Continuation of history.py with six parallel replays (time box). Keeps the records history.py already wrote. Local only."""
from runner import *
import threading
from concurrent.futures import ThreadPoolExecutor
OLDPKT = REPO/'deployments/release-repair-20260916'
old = json.loads((OLDPKT/'old-binary-service-receipt.json').read_text())['startup'][0]
v2 = json.loads((OLDPKT/'v2-service-receipt-final.json').read_text())['finality_statuses'][0]
CAND = ROOT/'binaries/candidate-1'; OLD = ROOT/'binaries/rollback'
SAVED = pathlib.Path('/home/postfiatchad/.cache/release-repair-20260928/post-v2')
prior = json.loads((ROOT/'history-run.json').read_text())['checks']
checks = list(prior); done = {c['name'] for c in prior if c.get('status') == 'PASS'}
mutex = threading.Lock(); pool = ThreadPoolExecutor(6)


def save():
    write(ROOT/'history-run.json', dict(source_commit=SOURCE, binary_sha256=sha(CAND), rollback_binary_sha256=sha(OLD), checks=checks, live_mutations=False, updated_at=now()))


def add(rec):
    with mutex: checks.append(rec); save()
    return rec


def verify(name, binary, data, expected, checkpoint=False):
    if name in done: return next(c for c in prior if c['name'] == name)
    rec = run(name, [binary, 'verify-finalized-checkpoint' if checkpoint else 'verify-state', '--data-dir', data], timeout=900)
    if rec['status'] == 'PASS':
        try:
            result = json.loads(pathlib.Path(rec['stdout']).read_text())
            block = result if checkpoint else result['block_log']
            observed = dict(block_height=block.get('checkpoint_height' if checkpoint else 'block_count'), block_tip_hash=block.get('checkpoint_block_hash' if checkpoint else 'tip_hash'), state_root=block.get('checkpoint_state_root' if checkpoint else 'state_root'))
            passed = result.get('verified') is True and block.get('verified') is True and all(observed[k] == expected[k] for k in observed)
            rec.update(status='PASS' if passed else 'FAIL', verified=result.get('verified'), observed=observed, expected={k: expected[k] for k in observed})
            if not passed: rec['error'] = 'verification or certified identity mismatch'
        except Exception as e: rec.update(status='FAIL', error=str(e))
    write(ROOT/'reports'/f'{name}.json', rec)
    return add(rec)


def parallel(jobs):
    return [f.result() for f in [pool.submit(verify, *j) for j in jobs]]


def lane_a():
    parallel([(f'original-validator-{i}', CAND, ROOT/'working'/f'validator-{i}', old) for i in range(6)])
    if 'governance-prepare' not in done:
        prep = add(run('governance-prepare', ['python3', ROOT/'tools/governance_prepare.py'], cwd=ROOT/'tools', timeout=600))
        if prep['status'] != 'PASS': return
    while subprocess.run(['pgrep', '-f', 'tools/focused2.py'], capture_output=True).returncode == 0: time.sleep(5)
    add(run('governance-gate', ['python3', ROOT/'tools/services.py', 'governance'], cwd=ROOT/'tools', timeout=900))
    receipt = ROOT/'v2-service-receipt.json'
    if not receipt.exists(): return
    r = json.loads(receipt.read_text()); r.pop('key_staging', None); write(receipt, r)
    if r.get('result') != 'PASS': return
    expected = r['finality_statuses'][0]
    parallel([(f'fresh-v2-validator-{i}', CAND, ROOT/'working'/f'validator-{i}', expected) for i in range(6)])
    parallel([(f'rollback-checkpoint-v2-validator-{i}', OLD, ROOT/'working'/f'validator-{i}', expected, True) for i in range(6)])
    verify('rollback-full-v2-validator-0', OLD, ROOT/'working/validator-0', expected)


def lane_b():
    parallel([(f'saved-v2-validator-{i}', CAND, SAVED/f'validator-{i}', v2) for i in (4, 5)])


threads = [threading.Thread(target=f) for f in (lane_a, lane_b)]
for t in threads: t.start()
for t in threads: t.join()
write(ROOT/'operational-complete.json', dict(completed_at=now(), source_commit=SOURCE))
print(f'{now()} operational sequence complete', flush=True)
