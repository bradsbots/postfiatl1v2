from runner import *
import threading
oldpacket = REPO/'deployments/release-repair-20260916'
old = json.loads((oldpacket/'old-binary-service-receipt.json').read_text())['startup'][0]
v2 = json.loads((oldpacket/'v2-service-receipt-final.json').read_text())['finality_statuses'][0]
CAND = ROOT/'binaries/candidate-1'; OLD = ROOT/'binaries/rollback'
history = []; fresh = []; mutex = threading.Lock()
def wait_file(path):
    while not pathlib.Path(path).exists(): time.sleep(2)
def save():
    write(ROOT/'history-run.json', dict(source_commit=SOURCE, binary_sha256=sha(CAND), checks=history, live_mutations=False, updated_at=now()))
    if fresh: write(ROOT/'fresh-v2-history-run.json', dict(source_commit=SOURCE, binary_sha256=sha(CAND), scope='full replay of six freshly rotated local copies; exact newly certified tip and root', checks=fresh, updated_at=now(), live_mutations=False))
def verify(name, binary, data, expected, checkpoint=False, bucket=None):
    bucket = history if bucket is None else bucket
    with lock('replay', 2):
        if not wait_memory():
            rec = dict(name=name, status='BLOCKED_MEMORY', reason='less than 8 GiB available before replay (waited 15 min)', started_at=now())
            write(ROOT/'reports'/f'{name}.json', rec)
        else:
            rec = run(name, [binary, 'verify-finalized-checkpoint' if checkpoint else 'verify-state', '--data-dir', data], timeout=900, separate=True)
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
    with mutex: bucket.append(rec); save()
    return rec
def lane_a():
    for i in range(6): verify(f'original-validator-{i}', CAND, ROOT/'working'/f'validator-{i}', old)
    with lock('services'):
        prep = run('governance-prepare', ['python3', ROOT/'tools/governance_prepare.py'], timeout=600)
        if prep['status'] != 'PASS': return
        run('governance-gate', ['python3', ROOT/'tools/services.py', 'governance'], timeout=900)
    receipt = ROOT/'v2-service-receipt.json'
    if receipt.exists():
        r = json.loads(receipt.read_text()); r.pop('key_staging', None); write(receipt, r)
        if r.get('result') == 'PASS':
            expected = r['finality_statuses'][0]
            for i in range(6): verify(f'fresh-v2-validator-{i}', CAND, ROOT/'working'/f'validator-{i}', expected, bucket=fresh)
def lane_b():
    for i in range(6): verify(f'post-v2-validator-{i}', CAND, ROOT/'post-v2'/f'validator-{i}', v2)
    for i in range(6): verify(f'old-binary-checkpoint-{i}', OLD, ROOT/'rollback'/f'validator-{i}', old, True)
    with lock('services'):
        run('rollback-services', ['python3', ROOT/'tools/services.py', 'rollback'], timeout=900)
    verify('final-candidate-on-rollback-validator-0', CAND, ROOT/'rollback/validator-0', old)
wait_file(CAND); wait_file(ROOT/'preparation.json')
threads = [threading.Thread(target=f) for f in (lane_a, lane_b)]
for t in threads: t.start()
for t in threads: t.join()
write(ROOT/'operational-complete.json', dict(completed_at=now(), source_commit=SOURCE))
print(f'{now()} operational sequence complete', flush=True)
