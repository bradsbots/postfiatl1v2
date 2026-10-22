from runner import *
import shutil, hmac
os.umask(0o077)
old = pathlib.Path('/home/postfiatchad/.cache/combined-release-20260915')
prior = pathlib.Path('/home/postfiatchad/.cache/release-repair-20260916')
R4 = pathlib.Path('/home/postfiatchad/.local/lib/postfiat/releases/combined-fastpay-20260925/postfiat-node')
R4_SHA = 'd66cecc36426ce05ced8730b2439a27285c6b404688acd13dc23594b884eabd6'
assert sha(R4) == R4_SHA, 'deployed combined-fastpay-20260925 binary hash mismatch'
for group, source in [('working', old/'raw'), ('post-v2', prior/'working'), ('rollback', old/'raw')]:
    for i in range(6):
        dst = ROOT/group/f'validator-{i}'
        if (ROOT/'reports'/f'relocation-{group}-validator-{i}.json').exists(): continue
        assert not dst.exists()
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['cp', '-a', '--reflink=auto', str(source/f'validator-{i}'), str(dst)], check=True)
        ptr = dst/'transactional_generation.json'
        body, marker = ptr.read_bytes().rsplit(b'\npftmac1:', 1)
        key = (dst/'.integrity.key').read_bytes()
        mac = lambda b: hmac.new(key, b'postfiat.storage.state-file.v1:state file\0'+b, hashlib.sha3_384).hexdigest()
        assert len(key) == 48 and hmac.compare_digest(mac(body), marker.strip().decode())
        before = json.loads(body); after = dict(before)
        generation = pathlib.Path(before['database_directory']).name
        assert generation == 'transactional-generation' or generation.startswith('transactional-generation-')
        assert before['database_file'] == 'postfiat-state-v1.redb'
        assert (dst/generation/before['database_file']).is_file()
        after['database_directory'] = str(dst/generation)
        new = json.dumps(after, indent=2).encode()
        ptr.write_bytes(new+b'\npftmac1:'+mac(new).encode()+b'\n')
        write(ROOT/'reports'/f'relocation-{group}-validator-{i}.json', dict(original_mac_verified=True, changed_field='database_directory', logical_state_changed=False, source=str(source/f'validator-{i}'), before=before, after=after))
        print(f'{now()} Cloned and authenticated {group}/validator-{i}', flush=True)
keys = pathlib.Path('/home/postfiatchad/.cache/signing-fix-qualification-20260909/local-clone-gate-fresh')
for i in range(6):
    d = ROOT/'isolated-signers'/f'validator-{i}'; d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(keys/f'validator-{i}'/'validator_keys.json', d/'validator_keys.json')
shutil.copy2('/home/postfiatchad/.cache/signing-fix-qualification-20260909/local-clone-gate/topology.json', ROOT/'topology.json')
shutil.copy2(R4, ROOT/'binaries/rollback')
assert sha(ROOT/'binaries/rollback') == R4_SHA
write(ROOT/'preparation.json', dict(source_commit=SOURCE, completed_at=now(), scope='new disposable disk-backed clones; authenticated local database-pointer relocation only', groups={'working': str(old/'raw'), 'post-v2': str(prior/'working'), 'rollback': str(old/'raw')}, old_binary_source=str(R4), old_binary_sha256=sha(ROOT/'binaries/rollback'), topology_sha256=sha(ROOT/'topology.json'), live_mutations=False))
print(f'{now()} preparation complete', flush=True)
