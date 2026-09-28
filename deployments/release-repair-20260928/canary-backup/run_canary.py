"""Replay the fresh signed validator-1 canary backup with the new build. Local only."""
import shutil, sys
sys.path.insert(0, '/home/postfiatchad/.cache/release-repair-20260928/tools')
from runner import *
C = ROOT/'canary-backup'
E = pathlib.Path('/home/postfiatchad/.postfiat/deployments/combined-fastpay-20260928/evidence')
PUB = pathlib.Path('/home/postfiatchad/.postfiat/deployments/cobalt-activation-8694b99d/snapshot-keys/snapshot-publisher.public.json')
CAND = ROOT/'binaries/candidate-1'
def crun(name, cmd, expect_fail=False, replay=False):
    rec = run(f'canary-{name}', cmd, cwd=C, timeout=1500, deadline=STARTED+datetime.timedelta(hours=3))
    if expect_fail:
        rec['expected'] = 'nonzero exit (rejection)'
        rec['status'] = 'PASS' if rec.get('exit_code') not in (0, None) else 'FAIL'
    write(ROOT/'reports'/f'canary-{name}.json', rec)
    return rec
state = json.loads((E/'rollout-state.json').read_text())
backup = state['backup']
assert backup.get('verified') is True
out = dict(started_at=now(), source_commit=SOURCE, binary_sha256=sha(CAND), trusted_public_key_sha256=sha(PUB), rollout_backup=backup)
signed = C/'backup-signed'
if not signed.exists():
    shutil.copytree(E/'pre-rollout-backup/backup-signed', signed)
out['signed_manifest_sha256'] = sha(signed/'snapshot.signed-manifest.json')
assert out['signed_manifest_sha256'] == backup['signed_manifest_sha256']
tampered = C/'tampered-signed'
if not tampered.exists():
    shutil.copytree(signed, tampered)
    m = json.loads((tampered/'snapshot.signed-manifest.json').read_text())
    def flip(o):
        for k, v in o.items():
            if 'signature' in k and isinstance(v, str) and len(v) > 8:
                o[k] = ('0' if v[-1] != '0' else '1').join([v[:-1], '']); return True
            if isinstance(v, dict) and flip(v): return True
        return False
    out['tamper_applied'] = flip(m)
    (tampered/'snapshot.signed-manifest.json').write_text(json.dumps(m, indent=2))
steps = {}
steps['import-signed'] = crun('import-signed', [CAND, 'snapshot-import-signed-finalized-checkpoint', '--data-dir', C/'signed-import', '--snapshot-dir', signed, '--trusted-publisher-key-file', PUB, '--node-id', 'validator-1'])
steps['import-tampered-signature'] = crun('import-tampered-signature', [CAND, 'snapshot-import-signed-finalized-checkpoint', '--data-dir', C/'tampered-import', '--snapshot-dir', tampered, '--trusted-publisher-key-file', PUB, '--node-id', 'validator-1'], expect_fail=True)
steps['verify-checkpoint-signed'] = crun('verify-checkpoint-signed', [CAND, 'verify-finalized-checkpoint', '--data-dir', C/'signed-import'])
steps['status-signed'] = crun('status-signed', [CAND, 'status', '--data-dir', C/'signed-import'])
with lock('replay', 2):
    wait_memory()
    steps['verify-state-signed'] = crun('verify-state-signed', [CAND, 'verify-state', '--data-dir', C/'signed-import'])
status = json.loads(pathlib.Path(steps['status-signed']['stdout']).read_text())
vs = json.loads(pathlib.Path(steps['verify-state-signed']['stdout']).read_text()) if steps['verify-state-signed']['status'] == 'PASS' else {}
cp = json.loads(pathlib.Path(steps['verify-checkpoint-signed']['stdout']).read_text()) if steps['verify-checkpoint-signed']['status'] == 'PASS' else {}
bl = vs.get('block_log', {})
out['observed'] = dict(status_height=status.get('block_height'), status_tip=status.get('block_tip_hash'), status_root=status.get('state_root'),
    checkpoint_verified=cp.get('verified'), checkpoint_height=cp.get('checkpoint_height'), checkpoint_tip=cp.get('checkpoint_block_hash'), checkpoint_root=cp.get('checkpoint_state_root'),
    replay_verified=vs.get('verified'), replay_block_log_verified=bl.get('verified'), replay_block_count=bl.get('block_count'), replay_tip=bl.get('tip_hash'), replay_root=bl.get('state_root'))
o = out['observed']
agree = (o['replay_verified'] is True and o['replay_block_log_verified'] is True and o['checkpoint_verified'] is True
         and o['replay_block_count'] == o['status_height'] == backup['height'] == o['checkpoint_height']
         and o['replay_tip'] == o['status_tip'] == backup['tip'] == o['checkpoint_tip']
         and o['replay_root'] == o['status_root'] == backup['state_root'] == o['checkpoint_root'])
out['steps'] = {k: dict(status=v['status'], exit_code=v.get('exit_code'), elapsed_seconds=v.get('elapsed_seconds')) for k, v in steps.items()}
out['result'] = 'PASS' if agree and all(v['status'] == 'PASS' for v in steps.values()) else 'FAIL'
out['completed_at'] = now()
write(C/'result.json', out)
print(json.dumps(dict(result=out['result'], observed=o), indent=1), flush=True)
