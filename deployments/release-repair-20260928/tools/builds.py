from runner import *
import shutil
flags = ' '.join([f'--remap-path-prefix={ROOT}/source-{i}=/src/postfiatl1v2' for i in (1, 2)]+[f'--remap-path-prefix={ROOT}/target-{i}=/target' for i in (1, 2)])
common = dict(SOURCE_DATE_EPOCH='1789514690', CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER='/usr/bin/gcc', RUSTFLAGS=flags)
builds = []
for i in (1, 2):
    cwd = ROOT/f'source-{i}'
    resumed = cwd.exists()
    if not resumed:
        subprocess.run(['git', 'worktree', 'add', '--detach', str(cwd), SOURCE], cwd=REPO, check=True)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip() == SOURCE
    clean = subprocess.check_output(['git', 'status', '--porcelain'], cwd=cwd, text=True) == ''
    assert clean
    target = ROOT/f'target-{i}'
    cache = pathlib.Path(f'/home/postfiatchad/.cache/qualify-fix-20260922/target-{i}')
    if not resumed:
        subprocess.run(['cp', '-a', '--reflink=auto', str(cache), str(target)], check=True)
    rec = run(f'node-build-{i}', ['cargo', 'build', '--release', '--locked', '-p', 'postfiat-node', '--bin', 'postfiat-node'], cwd, common | dict(CARGO_TARGET_DIR=str(target)), timeout=1500)
    rec.update(source_commit=SOURCE, source_tree=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=cwd, text=True).strip(), source_clean_at_collection=clean, cargo_lock_sha256=sha(cwd/'Cargo.lock'), cache_origin=str(cache), cache_scope='separate copy of existing dependency cache; not empty-cache', resumed_after_driver_interruption=resumed)
    if resumed: rec['resume_note'] = 'first driver process was terminated when its tool session ended; its cargo build kept running in the same tree/target, then this identical command completed the build'
    if rec['status'] == 'PASS':
        binary = ROOT/'binaries'/f'candidate-{i}'
        shutil.copy2(target/'release/postfiat-node', binary)
        rec.update(binary_sha256=sha(binary), binary_bytes=binary.stat().st_size, binary_path=str(binary))
        dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
        (ROOT/'logs'/f'node-build-{i}-dynamic.stdout').write_text(dynamic)
        rec['has_rpath_or_runpath'] = any(t in dynamic for t in ('(RPATH)', '(RUNPATH)'))
        comment = subprocess.run(['readelf', '-p', '.comment', str(binary)], capture_output=True, text=True).stdout
        (ROOT/'logs'/f'node-build-{i}-comment.stdout').write_text(comment)
        rec['zig_in_comment'] = 'zig' in comment.lower()
        rec['source_clean_after_build'] = subprocess.check_output(['git', 'status', '--porcelain'], cwd=cwd, text=True) == ''
        if rec['has_rpath_or_runpath'] or not rec['source_clean_after_build'] or rec['zig_in_comment']:
            rec.update(status='FAIL', error='RUNPATH, linker or source cleanliness gate failed')
    write(ROOT/'reports'/f'node-build-{i}.json', rec)
    builds.append(rec)
    write(ROOT/'node-builds.json', dict(result='RUNNING' if i == 1 else 'INCOMPLETE', builds=builds))
if all(b['status'] == 'PASS' for b in builds):
    cmp = run('node-reproducibility', ['cmp', ROOT/'binaries/candidate-1', ROOT/'binaries/candidate-2'])
    result = cmp['status']
else:
    cmp = None; result = 'FAIL'
write(ROOT/'node-builds.json', dict(result=result, source_commit=SOURCE, builds=builds, comparison=cmp, scope='Two clean source trees; distinct copied caches; identical remaps; GCC linker; unmodified executables'))
print(json.dumps(dict(result=result, hashes=[b.get('binary_sha256') for b in builds])), flush=True)
