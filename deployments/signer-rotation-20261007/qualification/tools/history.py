"""History, rotation and rollback checks with the new build (2026-09-28 tools/history.py and run_canary.py). Local only."""
from runner import *
import shutil, threading
OLDPKT = REPO/'deployments/release-repair-20260916'
old = json.loads((OLDPKT/'old-binary-service-receipt.json').read_text())['startup'][0]
v2 = json.loads((OLDPKT/'v2-service-receipt-final.json').read_text())['finality_statuses'][0]
CAND = ROOT/'binaries/candidate-1'; OLD = ROOT/'binaries/rollback'
CANARY = pathlib.Path('/home/postfiatchad/.postfiat/deployments/combined-fastpay-20260928/evidence')
PUB = pathlib.Path('/home/postfiatchad/.postfiat/deployments/cobalt-activation-8694b99d/snapshot-keys/snapshot-publisher.public.json')
checks = []; mutex = threading.Lock()


def save():
    write(ROOT/'history-run.json', dict(source_commit=SOURCE, binary_sha256=sha(CAND), rollback_binary_sha256=sha(OLD), checks=checks, live_mutations=False, updated_at=now()))


def add(rec):
    with mutex: checks.append(rec); save()
    return rec


def verify(name, binary, data, expected, checkpoint=False):
    with lock('replay', 2):
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


def canary():
    C = ROOT/'canary-1050'; C.mkdir(exist_ok=True)
    state = json.loads((CANARY/'rollout-state.json').read_text()); backup = state['backup']
    assert backup.get('verified') is True and backup['height'] == 1050
    exp = dict(block_height=backup['height'], block_tip_hash=backup['tip'], state_root=backup['state_root'])
    signed = CANARY/'pre-rollout-backup/backup-signed'
    assert sha(signed/'snapshot.signed-manifest.json') == backup['signed_manifest_sha256']
    tampered = C/'tampered-signed'
    shutil.copytree(signed, tampered)
    m = json.loads((tampered/'snapshot.signed-manifest.json').read_text())
    def flip(o):
        for k, v in o.items():
            if 'signature' in k and isinstance(v, str) and len(v) > 8:
                o[k] = v[:-1] + ('0' if v[-1] != '0' else '1'); return True
            if isinstance(v, dict) and flip(v): return True
        return False
    assert flip(m)
    (tampered/'snapshot.signed-manifest.json').write_text(json.dumps(m, indent=2))
    imp = run('canary-import-signed', [CAND, 'snapshot-import-signed-finalized-checkpoint', '--data-dir', C/'signed-import', '--snapshot-dir', signed, '--trusted-publisher-key-file', PUB, '--node-id', 'validator-1'], timeout=600)
    add(imp)
    bad = run('canary-import-tampered-signature', [CAND, 'snapshot-import-signed-finalized-checkpoint', '--data-dir', C/'tampered-import', '--snapshot-dir', tampered, '--trusted-publisher-key-file', PUB, '--node-id', 'validator-1'], timeout=300)
    bad.update(expected='nonzero exit (rejection)', status='PASS' if bad.get('exit_code') not in (0, None) else 'FAIL'); add(bad)
    shutil.rmtree(tampered); shutil.rmtree(C/'tampered-import', ignore_errors=True)
    if imp['status'] != 'PASS': return
    verify('canary-1050-checkpoint-new', CAND, C/'signed-import', exp, checkpoint=True)
    verify('canary-1050-full-new', CAND, C/'signed-import', exp)
    # Rollback: the deployed executable reads the data written by the new build.
    verify('canary-1050-checkpoint-rollback', OLD, C/'signed-import', exp, checkpoint=True)
    verify('canary-1050-full-rollback', OLD, C/'signed-import', exp)


def lane_a():
    for i in range(6): verify(f'original-validator-{i}', CAND, ROOT/'working'/f'validator-{i}', old)
    with lock('services'):
        prep = add(run('governance-prepare', ['python3', ROOT/'tools/governance_prepare.py'], cwd=ROOT/'tools', timeout=600))
        if prep['status'] != 'PASS': return
        add(run('governance-gate', ['python3', ROOT/'tools/services.py', 'governance'], cwd=ROOT/'tools', timeout=900))
    receipt = ROOT/'v2-service-receipt.json'
    if receipt.exists():
        r = json.loads(receipt.read_text()); r.pop('key_staging', None); write(receipt, r)
        if r.get('result') == 'PASS':
            expected = r['finality_statuses'][0]
            for i in range(6): verify(f'fresh-v2-validator-{i}', CAND, ROOT/'working'/f'validator-{i}', expected)
            for i in range(6): verify(f'rollback-checkpoint-v2-validator-{i}', OLD, ROOT/'working'/f'validator-{i}', expected, checkpoint=True)
            verify('rollback-full-v2-validator-0', OLD, ROOT/'working/validator-0', expected)


def lane_b():
    canary()
    for i in (4, 5): verify(f'saved-v2-validator-{i}', CAND, pathlib.Path('/home/postfiatchad/.cache/release-repair-20260928/post-v2')/f'validator-{i}', v2)


while not (ROOT/'node-builds.json').exists(): time.sleep(5)
assert json.loads((ROOT/'node-builds.json').read_text())['result'] == 'PASS', 'builds did not reproduce'
threads = [threading.Thread(target=f) for f in (lane_a, lane_b)]
for t in threads: t.start()
for t in threads: t.join()
write(ROOT/'operational-complete.json', dict(completed_at=now(), source_commit=SOURCE))
print(f'{now()} operational sequence complete', flush=True)
