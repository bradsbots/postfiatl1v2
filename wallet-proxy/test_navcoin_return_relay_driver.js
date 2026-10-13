'use strict';

const assert = require('node:assert');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { loadConfig } = require('./navcoin-return-relay-driver');

const DRIVER = path.join(__dirname, 'navcoin-return-relay-driver.js');
const RANGE_ERROR = /NAVCoin return import timeout is outside the supported range/;

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'navcoin-return-driver-test-'));

function stub(name, body) {
    const file = path.join(dir, name);
    fs.writeFileSync(file, body, { mode: 0o644 });
    fs.chmodSync(file, 0o644);
    return { file, sha256: crypto.createHash('sha256').update(body).digest('hex') };
}

const burnInspect = stub('burn-inspect.py', 'print("{}")\n');
const returnImport = stub('return-import.sh', '#!/usr/bin/env bash\nexit 0\n');

const base = {
    schema: 'postfiat-navcoin-return-relay-driver-config-v1',
    route_id: 'test-route', route_config_digest: 'aa'.repeat(48),
    controller: `0x${'bb'.repeat(20)}`, wrapped_token: `0x${'cc'.repeat(20)}`,
    native_nav_asset_id: 'dd'.repeat(48), native_asset_code: 'TST', wrapped_token_symbol: 'wTST',
    burn_report_schema: 'test-burn-v1', validator_data_dir: '/var/lib/test',
    repo: dir, python: '/usr/bin/python3',
    burn_inspect_script: burnInspect.file, burn_inspect_script_sha256: burnInspect.sha256,
    return_import_script: returnImport.file, return_import_script_sha256: returnImport.sha256,
    node_binary: '/opt/postfiat/releases/test-1/postfiat-node', node_binary_sha256: 'ee'.repeat(32),
    cast_binary: '/bin/false', ethereum_rpc: 'http://rpc.invalid', validator2_host: 'test.invalid',
};

let counter = 0;
function writeConfig(extra) {
    const file = path.join(dir, `config-${counter += 1}.json`);
    fs.writeFileSync(file, JSON.stringify({ ...base, ...extra }), { mode: 0o600 });
    fs.chmodSync(file, 0o600);
    return file;
}

try {
    // Absent or null falls back to the existing one-hour default.
    assert.strictEqual(loadConfig(writeConfig({})).import_timeout_ms, 3_600_000);
    assert.strictEqual(loadConfig(writeConfig({ import_timeout_ms: null })).import_timeout_ms, 3_600_000);

    // In-range integers are kept; a digit string is normalised to a number.
    for (const value of [1_000, 3_600_000, 86_400_000]) {
        assert.strictEqual(loadConfig(writeConfig({ import_timeout_ms: value })).import_timeout_ms, value);
    }
    const normalised = loadConfig(writeConfig({ import_timeout_ms: '3600000' })).import_timeout_ms;
    assert.strictEqual(normalised, 3_600_000);
    assert.strictEqual(typeof normalised, 'number');

    // Values execFile would reject, overflow to a ~1 ms timer, or silently replace are refused.
    for (const value of [0, 999, -1, 1.5, 86_400_001, 2_147_483_648, 86_400_000_000, 'abc', '', true, []]) {
        assert.throws(() => loadConfig(writeConfig({ import_timeout_ms: value })), RANGE_ERROR,
            `import_timeout_ms=${JSON.stringify(value)} must be refused`);
    }

    // A refused config stops the CLI before any job work, exit 1, like an identity mismatch.
    const cli = spawnSync(process.execPath, [DRIVER, 'readiness', '--config',
        writeConfig({ import_timeout_ms: 2_147_483_648 })], { encoding: 'utf8', timeout: 30_000 });
    assert.strictEqual(cli.status, 1);
    assert.match(cli.stderr, RANGE_ERROR);
} finally {
    fs.rmSync(dir, { recursive: true, force: true });
}

process.stdout.write('navcoin return relay driver config tests passed\n');
