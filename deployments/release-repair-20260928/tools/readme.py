from runner import *
PACKET = REPO/'deployments/release-repair-20260928'
FINAL = len(sys.argv) > 1 and sys.argv[1] == 'final'
def read(p, d=None):
    p = ROOT/p
    return json.loads(p.read_text()) if p.exists() else d
def rep(n): return read(f'reports/{n}.json', {})
def st(n):
    s = rep(n).get('status', 'NOT RUN' if FINAL else 'PENDING')
    return 'IN PROGRESS' if s == 'RUNNING' else s
def grp(names):
    s = [st(n) for n in names]
    if all(x == 'PASS' for x in s): return 'PASS'
    if any(x in ('FAIL', 'STOPPED_MEMORY', 'BLOCKED_MEMORY', 'TIMEOUT') for x in s): return 'FAIL'
    return 'NOT COMPLETE' if FINAL else 'PENDING'
b = read('node-builds.json', {}); builds = b.get('builds', [])
h = [x.get('binary_sha256', 'pending') for x in builds] + ['pending'] * (2 - len(builds))
v2 = read('v2-service-receipt.json', {}); old = read('old-binary-service-receipt.json', {})
sw = {r['name']: r for r in read('software-gates.json', {}).get('stages', [])}
def sws(n):
    r = sw.get(n)
    if not r: return 'NOT RUN' if FINAL else 'PENDING'
    s = r['status']
    if s in ('PASS', 'FAIL') and 'tests_passed' in r:
        s += f": {r['tests_passed']} passed" + (f", {r['tests_failed']} failed" if r.get('tests_failed') else '') + (f", {r['tests_ignored']} ignored" if r.get('tests_ignored') else '')
    return s
canary = read('canary-backup/result.json', {})
co = canary.get('observed', {})
canary_s = canary.get('result', 'PENDING')
if canary_s == 'PASS': canary_s += f": checkpoint verified, full history replayed to {co.get('replay_block_count')}, root `{str(co.get('replay_root'))[:8]}…`"
skip = read('canary-backup/backup-skip.json')
if skip: canary_s = 'SKIPPED (see reason); ' + canary_s
fs = rep('full-workspace-tests')
fss = fs.get('status', 'PENDING')
if fss == 'RUNNING': fss = f"PENDING: still running at packet time (started {fs.get('started_at','')[11:16]}Z)"
elif 'tests_passed' in fs: fss += f": {fs.get('groups')} groups, {fs['tests_passed']:,} passed, {fs.get('tests_failed')} failed, {fs.get('tests_ignored')} ignored"
rows = [
    ('Two matching node executables', b.get('result', 'PENDING'), '[Build records](node-builds.json)'),
    ('Six original full-history checks, height 1020 (through block 1011)', grp([f'original-validator-{i}' for i in range(6)]), '[History run](history-run.json)'),
    ('Six saved V2 full-history checks, height 1021', grp([f'post-v2-validator-{i}' for i in range(6)]), '[History run](history-run.json)'),
    ('Six fresh V2 full-history checks, height 1021', grp([f'fresh-v2-validator-{i}' for i in range(6)]), '[Fresh V2 history](fresh-v2-history-run.json)'),
    ('Current-chain replay, fresh signed validator-1 canary backup', canary_s, '[Result](canary-backup/result.json)'),
    ('Fix: reproduce-first test (non-signer view-0 proposer anchors the held effect)', sws('fix-reproduce-first'), '[Log](logs/fix-reproduce-first.stdout)'),
    ('Timeout vote and view recovery, node bin tests', sws('view-recovery-bin'), '[Log](logs/view-recovery-bin.stdout)'),
    ('Timeout votes form a timeout certificate, node lib test', sws('timeout-votes-lib'), '[Log](logs/timeout-votes-lib.stdout)'),
    ('FastPay committee, non-signer anchor, recovery and checkpoint restore, node lib tests', sws('fastpay-committee-lib'), '[Log](logs/fastpay-committee-lib.stdout)'),
    ('node-fastpay (all node lib `fastpay` tests)', sws('node-fastpay'), '[Log](logs/node-fastpay.stdout)'),
    ('Local governed rotation: both startup orders, convergence, restart', v2.get('result', st('governance-gate')), '[Gate log](logs/governance-gate.stdout), [receipt](v2-service-receipt.json)'),
    ('Rollback: six checkpoint verifications, deployed `d66cecc3…`', grp([f'old-binary-checkpoint-{i}' for i in range(6)]), '[History run](history-run.json)'),
    ('Rollback: deployed services start and restart on six copies', old.get('result', st('rollback-services')), '[Log](logs/rollback-services.stdout), [receipt](old-binary-service-receipt.json)'),
    ('Rollback: new build full replay of restored validator-0', st('final-candidate-on-rollback-validator-0'), '[Receipt](receipts/final-candidate-on-rollback-validator-0.json)'),
    ('Workspace check', sws('workspace-check'), '[Log](logs/workspace-check.stderr)'),
    ('Rust formatting', sws('format'), '[Log](logs/format.stdout)'),
    ('Proof public-input inventory', sws('proof-input-inventory'), '[Log](logs/proof-input-inventory.stdout)'),
    ('Workspace Clippy, `-D warnings`', sws('workspace-clippy'), '[Log](logs/workspace-clippy.stderr)'),
    ('fastpay-types', sws('fastpay-types'), '[Log](logs/fastpay-types.stdout)'),
    ('fastpay-execution', sws('fastpay-execution'), '[Log](logs/fastpay-execution.stdout)'),
    ('cobalt-handoff-tests', sws('cobalt-handoff-tests'), '[Log](logs/cobalt-handoff-tests.stdout)'),
    ('live-replay-supply', sws('live-replay-supply'), '[Log](logs/live-replay-supply.stdout)'),
    ('warm-latency', sws('warm-latency') + ' (5-minute budget, still compiling); rerun with a longer budget: ' + (lambda r: (r.get('status', 'PENDING') + (f": {r['tests_passed']} passed" if r.get('status') == 'PASS' else '')) if r.get('status') != 'RUNNING' else 'IN PROGRESS')(rep('warm-latency-rerun')), '[Log](logs/warm-latency.stdout), [rerun](logs/warm-latency-rerun.stdout)'),
    ('Full workspace test suite (background, local)', fss, '[Log](logs/full-workspace-tests.stdout), [receipt](receipts/full-workspace-tests.json)'),
]
pub = read('publication-gates.json', {})
for n in ('strict-docs', 'public-doc-links', 'public-secret-scan'):
    rows.append((n if n != 'strict-docs' else 'mkdocs build --strict', pub.get(n, 'PENDING'), f'[Log](logs/{n}.stdout)'))
table = '| Check | Result | Evidence |\n|---|---|---|\n' + '\n'.join(f'| {a} | {r} | {e} |' for a, r, e in rows)
def cell(n): return st(n).replace('NOT RUN', 'NOT RUN')
vt = '| Validator copy | Original, 1020 | Saved V2, 1021 | Fresh V2, 1021 | Rollback checkpoint (`d66cecc3…`) |\n|---|---|---|---|---|\n' + '\n'.join(f'| validator-{i} | {cell(f"original-validator-{i}")} | {cell(f"post-v2-validator-{i}")} | {cell(f"fresh-v2-validator-{i}")} | {cell(f"old-binary-checkpoint-{i}")} |' for i in range(6))
(ROOT/'readme-table.md').write_text(table + '\n\n' + vt + '\n')
print(table); print(); print(vt)
