"""Free space only from this run's own disposable data, and only when the disk runs low."""
from runner import *
import shutil
def free(): return shutil.disk_usage(ROOT).free
def log(msg): print(f'{now()} {msg} (free {free()/2**30:.1f} GiB)', flush=True)
log('guard start')
while True:
    f = free()
    if f < 8*1024**3 and (ROOT/'target-2').exists():
        b = json.loads((ROOT/'node-builds.json').read_text()) if (ROOT/'node-builds.json').exists() else {}
        if b.get('result') not in (None, 'RUNNING', 'INCOMPLETE'):
            subprocess.run(['find', str(ROOT/'target-2'), '-delete'])
            log('deleted target-2 (build 2 finished and hashed; binary kept in binaries/candidate-2)')
    if f < 6*1024**3:
        for i in range(6):
            d = ROOT/'post-v2'/f'validator-{i}'; r = ROOT/'reports'/f'post-v2-validator-{i}.json'
            if d.exists() and r.exists() and json.loads(r.read_text()).get('status') == 'PASS':
                subprocess.run(['find', str(d), '-delete']); log(f'deleted verified disposable copy post-v2/validator-{i}')
                break
        else:
            if f < 2*1024**3: log('LOW DISK: nothing left that the guard may delete')
    time.sleep(10)
