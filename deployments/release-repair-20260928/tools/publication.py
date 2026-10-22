from runner import *
tag = sys.argv[1] if len(sys.argv) > 1 else 'final'
venv = REPO/'.venv-docs'
if not venv.exists(): venv.symlink_to('/home/postfiatchad/repos/postfiatl1v2/.venv-docs')
subprocess.run(['git', 'add', 'deployments/release-repair-20260928'], cwd=REPO, check=True)
res = {}
end = DEADLINE
for name, cmd in (('strict-docs', ['.venv-docs/bin/mkdocs', 'build', '--strict', '--site-dir', str(ROOT/'docs-site')]), ('public-doc-links', ['scripts/public-doc-links']), ('public-secret-scan', ['scripts/public-secret-scan'])):
    n = name if tag == 'final' else f'{tag}-{name}'
    r = run(n, cmd, timeout=900, deadline=end)
    res[name] = r['status']
p = ROOT/'publication-gates.json'
d = json.loads(p.read_text()) if p.exists() else {}
d[tag] = dict(results=res, completed_at=now(), scope='tracked tree with the packet staged')
if tag == 'final': d.update(res)
write(p, d)
print(json.dumps(res), flush=True)
