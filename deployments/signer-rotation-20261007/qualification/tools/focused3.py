"""Focused suites for the changes after the 2026-10-05 full suite (672b707c..tip) and the release's own suites."""
import datetime, json, os, pathlib, subprocess, time
ROOT = pathlib.Path('/home/postfiatchad/.cache/release-signer-rotation-20261007')
REPO = pathlib.Path('/home/postfiatchad/repos/postfiatl1v2')
ENV = os.environ | dict(CARGO_BUILD_JOBS='6', CARGO_TERM_COLOR='never', RUST_TEST_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
SUITES = [
    ('execution-signer-rotation-dry-run', ['cargo', 'test', '--locked', '-p', 'postfiat-execution', '--lib', 'signer_committee_rotation_dry_run', '--', '--test-threads=2']),
    ('node-signer-rotation-dry-run', ['cargo', 'test', '--locked', '-p', 'postfiat-node', '--lib', 'signer_committee_rotation_dry_run', '--', '--test-threads=2']),
]
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
results = []
for name, cmd in SUITES:
    start = time.monotonic(); rec = dict(name=name, command=cmd, cwd=str(REPO), started_at=now())
    out = ROOT/'logs'/f'activation-{name}.log'
    with out.open('wb') as f:
        code = subprocess.run(cmd, cwd=REPO, env=ENV, stdout=f, stderr=subprocess.STDOUT).returncode
    text = out.read_text(errors='replace')
    summary = [l for l in text.splitlines() if l.startswith('test result:') and ' 0 passed;' not in l] or [l for l in text.splitlines() if ' passed' in l][-1:]
    rec.update(exit_code=code, status='PASS' if code == 0 else 'FAIL', elapsed_seconds=round(time.monotonic()-start, 1), summary=summary, log=f'logs/activation-{name}.log', completed_at=now())
    results.append(rec)
    (ROOT/'activation-suites.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(), suites=results), indent=2)+'\n')
    print(f'{now()} {rec["status"]} {name} {summary}', flush=True)
