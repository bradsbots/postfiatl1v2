from runner import *
import shutil
PACKET = REPO/'deployments/release-repair-20260928'
PACKET.mkdir(parents=True, exist_ok=True)
for sub in ('history', 'logs', 'receipts'): (PACKET/sub).mkdir(exist_ok=True)
PRIVATE = ('governance-create.', 'governance-sign-', 'governance-assemble.', 'governance-batch.')
def read(path, default=None): return json.loads(path.read_text()) if path.exists() else default
def copy(src, dst):
    if src.is_file(): shutil.copy2(src, PACKET/dst)
def normalize(value):
    if isinstance(value, dict): return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list): return [normalize(v) for v in value]
    if isinstance(value, str) and value.startswith(str(ROOT/'logs')+'/'):
        if pathlib.Path(value).name.startswith(PRIVATE): return value
        return 'logs/'+pathlib.Path(value).name
    return value
reports = {}
HISTORY = ('original-validator-', 'post-v2-validator-', 'fresh-v2-validator-', 'old-binary-checkpoint-', 'final-candidate-on-rollback-')
for p in sorted((ROOT/'reports').glob('*.json')):
    rec = read(p); reports[p.stem] = rec
    if rec.get('status') == 'RUNNING': continue
    write(PACKET/'receipts'/p.name, normalize(rec))
    if p.stem.startswith('canary-'): continue
    if p.stem.startswith(HISTORY):
        if 'stdout' in rec: copy(pathlib.Path(rec['stdout']), 'history/'+p.stem+'.stdout.json')
        if 'stderr' in rec: copy(pathlib.Path(rec['stderr']), 'history/'+p.stem+'.stderr.log')
running = {n for n, r in reports.items() if r.get('status') == 'RUNNING'}
for p in sorted((ROOT/'logs').iterdir()):
    if p.is_file() and not p.name.startswith(PRIVATE) and not p.name.startswith('canary-') and p.name.split('.')[0] not in running:
        copy(p, 'logs/'+p.name)
for p in sorted((ROOT/'interrupted').glob('*')):
    if p.is_file(): copy(p, 'logs/interrupted-'+p.name)
CB = PACKET/'canary-backup'
for sub in ('logs', 'receipts'): (CB/sub).mkdir(parents=True, exist_ok=True)
for p in sorted((ROOT/'reports').glob('canary-*.json')):
    rec = read(p)
    if rec.get('status') == 'RUNNING': continue
    write(CB/'receipts'/p.name, normalize(rec))
for p in sorted((ROOT/'logs').glob('canary-*')):
    if p.name.split('.')[0] not in running: copy(p, 'canary-backup/logs/'+p.name)
for name in ('result.json', 'prepare_rollout.sh', 'run_canary.py', 'rollout-state.summary.json', 'prepare-rollout.log', 'backup-skip.json', 'stage-compare.json'):
    if (ROOT/'canary-backup'/name).exists(): copy(ROOT/'canary-backup'/name, 'canary-backup/'+name)
for group in ('v2-services', 'old-binary-services'):
    logdir = ROOT/group/'logs'
    if logdir.exists():
        for p in sorted(logdir.glob('*.log')): copy(p, 'logs/'+group+'-'+p.name)
for name in ('preparation.json', 'node-builds.json', 'history-run.json', 'fresh-v2-history-run.json', 'software-gates.json', 'v2-service-receipt.json', 'old-binary-service-receipt.json', 'canary-backup.json', 'ci-observation.json', 'operational-complete.json', 'task-node.json', 'publication-gates.json', 'checkpoint-push.json', 'full-workspace-tests.json'):
    if (ROOT/name).exists(): write(PACKET/name, normalize(read(ROOT/name)))
def st(name): return reports.get(name, {}).get('status', 'PENDING')
def group(names):
    s = [st(n) for n in names]
    if all(x == 'PASS' for x in s): return 'PASS'
    if any(x in ('FAIL', 'STOPPED_MEMORY', 'BLOCKED_MEMORY') for x in s): return 'FAIL'
    return 'INCOMPLETE'
builds = read(ROOT/'node-builds.json', {})
v2 = read(ROOT/'v2-service-receipt.json', {})
old = read(ROOT/'old-binary-service-receipt.json', {})
q = dict(
    source_commit=SOURCE, updated_at=now(), deployed=False,
    executables=[b.get('binary_sha256') for b in builds.get('builds', [])], reproducibility=builds.get('result', 'PENDING'),
    original_1020=group([f'original-validator-{i}' for i in range(6)]),
    saved_v2_1021=group([f'post-v2-validator-{i}' for i in range(6)]),
    fresh_v2_1021=group([f'fresh-v2-validator-{i}' for i in range(6)]),
    canary_backup=read(ROOT/'canary-backup/result.json', {}).get('result', 'PENDING'),
    governance_gate=v2.get('result', st('governance-gate')),
    rollback=dict(checkpoints=group([f'old-binary-checkpoint-{i}' for i in range(6)]), services=old.get('result', st('rollback-services')), candidate_full_replay=st('final-candidate-on-rollback-validator-0')),
    software={r['name']: r['status'] for r in read(ROOT/'software-gates.json', {}).get('stages', [])},
    full_workspace_tests=reports.get('full-workspace-tests', {}).get('status', 'PENDING'),
)
write(PACKET/'qualification.json', q)
print(json.dumps(q, indent=1))
