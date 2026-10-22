from runner import *
import threading
while True:
    b = ROOT/'node-builds.json'
    if b.exists() and json.loads(b.read_text()).get('result') not in ('RUNNING', 'INCOMPLETE'): break
    time.sleep(2)
def mark():
    rep = ROOT/'reports/full-workspace-tests.json'
    while True:
        try:
            d = json.loads(rep.read_text())
            if 'pid' in d: BACKGROUND.write_text(str(d['pid'])); return
        except Exception: pass
        time.sleep(0.5)
threading.Thread(target=mark, daemon=True).start()
rec = run('full-workspace-tests', ['cargo', 'test', '--workspace', '--locked', '-j', '2', '--no-fail-fast'], cwd=ROOT/'source-1', extra=dict(CARGO_TARGET_DIR=str(ROOT/'target-1')), timeout=5*3600, separate=False, deadline=STARTED+datetime.timedelta(hours=6))
text = pathlib.Path(rec['stdout']).read_text(errors='replace')
import re
rec["groups"] = len(re.findall(r"^test result: ", text, re.M))
rec['tests_passed'] = sum(map(int, re.findall(r'test result: \w+\. (\d+) passed;', text)))
rec['tests_failed'] = sum(map(int, re.findall(r'passed; (\d+) failed;', text)))
rec['tests_ignored'] = sum(map(int, re.findall(r'failed; (\d+) ignored;', text)))
rec['failed_tests'] = sorted(set(re.findall(r'^test (\S+) \.\.\. FAILED$', text, re.M)))
write(ROOT/'reports/full-workspace-tests.json', rec)
BACKGROUND.unlink(missing_ok=True)
