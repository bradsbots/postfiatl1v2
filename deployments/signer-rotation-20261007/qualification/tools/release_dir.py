"""Generate the machine-made parts of deployments/signer-rotation-20261007/ from the local stage and qualification."""
import hashlib, json, pathlib, re, shutil, sys
R = 'signer-rotation-20261007'; PREV = 'combined-fastpay-20260928'
Q = pathlib.Path('/home/postfiatchad/.cache/release-signer-rotation-20261007')
SRC_TREE = pathlib.Path(sys.argv[1])
OUT = SRC_TREE/'deployments'/R; OLD = SRC_TREE/'deployments'/PREV
S = pathlib.Path(f'/home/postfiatchad/.postfiat/deployments/{R}/stage')
C = S/'rootfs/etc/postfiat/releases'/R; U = S/'rootfs/etc/systemd/system'
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
OUT.mkdir(parents=True, exist_ok=True)
# Generated files: 12 units, 12 environment files, six bindings, topology, two circuit metadata files.
dst = OUT/'rootfs/etc'
shutil.copytree(U, dst/'systemd/system', dirs_exist_ok=True)
(dst/'postfiat/releases'/R).mkdir(parents=True, exist_ok=True)
for f in sorted(C.iterdir()):
    if f.name not in ('deployment-manifest.json', 'deployment.public.json'):
        shutil.copy2(f, dst/'postfiat/releases'/R/f.name)
shutil.copy2(C/'deployment-manifest.json', OUT/'deployment-manifest.signed.json')
for name, target in (('stage-report.json', 'stage-report.template.json'), ('validator-bindings.signing.json', 'validator-bindings.signing.template.json')):
    (OUT/target).write_text((S/name).read_text().replace(str(S), '@STAGE@'))
manifest = json.loads((C/'deployment-manifest.json').read_text())
old_input = json.loads((OLD/'manifest-input.unsigned.json').read_text())
inp = dict(old_input)
inp.update(deployment_id=R, previous_release_id=PREV, git_revision=manifest['git_revision'], binary_sha256=manifest['binary_sha256'],
           service_unit_file='rootfs/etc/systemd/system/postfiat-validator-0-rpc.service',
           environment_file=f'rootfs/etc/postfiat/releases/{R}/validator-0.rpc.env',
           service_unit_sha256=manifest['service_unit_sha256'], environment_sha256=manifest['environment_sha256'],
           validator_bindings=manifest['validator_bindings'], topology_sha256=manifest['topology_sha256'],
           swap_circuit_metadata_sha256=manifest['swap_circuit_metadata_sha256'],
           private_egress_circuit_metadata_sha256=manifest['private_egress_circuit_metadata_sha256'],
           trusted_publisher=manifest['publisher'], trusted_publisher_file_sha256=sha(C/'deployment.public.json'))
for k in ('chain_id', 'genesis_hash', 'build_profile', 'build_features', 'protocol_version', 'rpc_schema'):
    assert inp[k] == manifest[k], k
assert sha(OUT/inp['service_unit_file']) == inp['service_unit_sha256'] and sha(OUT/inp['environment_file']) == inp['environment_sha256']
(OUT/'manifest-input.unsigned.json').write_text(json.dumps(inp, indent=2)+'\n')
shutil.copy2(OLD/'inventory.txt', OUT/'inventory.txt')
shutil.copy2(Q/'node-builds.json', OUT/'node-builds.json')
# Scripts adapted from the previous release.
lp = (OLD/'local-preflight.py').read_text().replace(f'for {PREV} (adapted from ../combined-fastpay-20260925)', f'for {R} (adapted from ../{PREV})').replace(f'deploy-{PREV}', f'deploy-{R}')
(OUT/'local-preflight.py').write_text(lp)
of = (OLD/'observe-fleet.py').read_text()
of = of.replace(f'observation for {PREV}', f'observation for {R}').replace('the rest on combined-fastpay-20260925', f'the rest on {PREV}')
of = re.sub(r'PREVIOUS = \{.*?\n\}', 'PREVIOUS = {\n    "release_id": "combined-fastpay-20260928",\n    "binary_sha256": "1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a",\n    "build_git_revision": "c93b2137",\n    "manifest_sha256": "d2fdb687311341450c9b4c87d4d66d9edf1b79d3302a7705e8be7155f8c85928",\n}', of, flags=re.S)
(OUT/'observe-fleet.py').write_text(of)
dp = (OLD/'demo-preflight.py').read_text().replace(f'({PREV})', f'({R})')
(OUT/'demo-preflight.py').write_text(dp)
# rollback-one.sh: back to combined-fastpay-20260928 with that release's unit hashes.
rb = (OLD/'rollback-one.sh').read_text()
rb = rb.replace('combined-fastpay-20260928 to\n# combined-fastpay-20260925 (executable d66cecc3...)', f'{R} to\n# {PREV} (executable 1f8b332d...)')
rb = rb.replace('combined-fastpay-20260925', PREV).replace('d66cecc36426ce05ced8730b2439a27285c6b404688acd13dc23594b884eabd6', '1f8b332d9f482cdcf6ccf5cc15307ebd5d9bf0058b7a6db80a7132690d97e24a')
rb = rb.replace(f'../{PREV}/rollback-one.sh', '../combined-fastpay-20260928/rollback-one.sh')
rb = rb.replace('2026-09-25 release directory', '2026-09-28 release directory').replace('the local\n# 2026-09-25 stage', 'the local\n# 2026-09-28 stage').replace('2026-09-25 executable', '2026-09-28 executable').replace('signed 2026-09-25 manifest', 'signed 2026-09-28 manifest')
rb = rb.replace('validator-1 backup at height\n# 1050 in the rollout evidence', 'validator-1 backup taken on\n# 2026-10-07 in the rollout evidence')
for kind, suffix in (('transport', ''), ('rpc', '-rpc')):
    for i in range(6):
        want = sha(OLD/f'rootfs/etc/systemd/system/postfiat-validator-{i}{suffix}.service')
        rb = re.sub(rf'(declare -A want_{kind}=\((?:\n  \[validator-\d\]=[0-9a-f]+)*?\n  \[validator-{i}\]=)[0-9a-f]+', rf'\g<1>{want}', rb)
(OUT/'rollback-one.sh').write_text(rb); (OUT/'rollback-one.sh').chmod(0o755)
print('generated', sum(1 for p in OUT.rglob('*') if p.is_file()), 'files')
