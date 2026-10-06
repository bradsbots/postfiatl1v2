"""Copy the local qualification records into deployments/signer-rotation-20261007/qualification/ and write qualification.json."""
import datetime, hashlib, json, pathlib, shutil, sys
Q = pathlib.Path('/home/postfiatchad/.cache/release-signer-rotation-20261007')
E = pathlib.Path('/home/postfiatchad/.postfiat/deployments/signer-rotation-20261007/evidence')
OUT = pathlib.Path(sys.argv[1])/'deployments/signer-rotation-20261007/qualification'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
for d in ('logs', 'reports', 'tools'):
    shutil.copytree(Q/d, OUT/d, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.tmp'))
for f in ('history-run.json', 'focused-suites.json', 'release-suites.json', 'preparation.json', 'v2-service-receipt.json',
          'local-preflight-signed.json', 'ci-main.json', 'ci-release.json', 'logs-build-driver.log', 'logs-history-driver.log',
          'logs-history2-driver.first.log', 'logs-history2-driver.log', 'logs-focused-driver.log', 'logs-focused2-driver.log'):
    if (Q/f).exists(): shutil.copy2(Q/f, OUT/(f if not f.startswith('logs-') else 'logs/'+f[5:]))
(OUT/'store-migrate').mkdir(exist_ok=True)
for f in ('dry-run.json', 'convert.json', 'second.json', 'restored-dry-run.json'):
    shutil.copy2(Q/'store-migrate'/f, OUT/'store-migrate'/f)
(OUT/'stage').mkdir(exist_ok=True)
for f in ('manifest-validity.txt', 'stage-command.stdout', 'manifest-create.stdout'):
    if (E/f).exists(): shutil.copy2(E/f, OUT/'stage'/f)
shutil.copy2(Q/'verified-record/rpc.deployment-verified.json', OUT/'stage/rpc.deployment-verified.json')
if (Q/'tasknode/task-node.json').exists(): shutil.copy2(Q/'tasknode/task-node.json', OUT/'task-node.json')
history = json.loads((Q/'history-run.json').read_text())
latest = {}
for c in history['checks']: latest[c['name']] = c
summary = dict(
    release_id='signer-rotation-20261007', source_commit=history['source_commit'], binary_sha256=history['binary_sha256'],
    rollback_binary_sha256=history['rollback_binary_sha256'], generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    builds=json.loads((Q/'node-builds.json').read_text())['result'],
    history={k: dict(status=v['status'], observed=v.get('observed'), expected=v.get('expected')) for k, v in latest.items()},
    focused_suites={s['name']: s['status'] for s in json.loads((Q/'focused-suites.json').read_text())['suites']},
    release_suites={s['name']: s['status'] for s in json.loads((Q/'release-suites.json').read_text())['suites']} if (Q/'release-suites.json').exists() else None,
    local_preflight=json.loads((Q/'local-preflight-signed.json').read_text())['result'],
    live_mutations=False, host_contact=False,
    not_done_today=['canary backup', 'fleet before-state', 'rollout', 'store conversion', 'activation'])
(OUT/'qualification.json').write_text(json.dumps(summary, indent=2)+'\n')
files = sorted(p for p in OUT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
(OUT/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(OUT)}\n' for p in files))
print(len(files), 'files')
