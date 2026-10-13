'use strict';

const assert = require('node:assert');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { create, canonicalJobId } = require('./navcoin-return-jobs');
const { terminalError } = require('./navcoin-return-relay-driver');

const ROUTE_ID = 'pftl-qnav-ethereum-wqNAV-qusd-v1';
const OTHER_ROUTE_ID = 'pftl-rnav-ethereum-wrNAV-rusd-v1';
const ROUTE_DIGEST = 'aa'.repeat(48);
const CONTROLLER = `0x${'bb'.repeat(20)}`;
const TOKEN = `0x${'cc'.repeat(20)}`;
const ASSET = 'dd'.repeat(48);
const TX = `0x${'11'.repeat(32)}`;
const LEGACY_A666_ROUTE_ID = 'pftl-a666-ethereum-wA666-usdc-v1';

const config = {
    schema: 'postfiat-navcoin-return-relay-config-v1', enabled: true,
    route_id: ROUTE_ID, route_config_digest: ROUTE_DIGEST,
    controller: CONTROLLER, wrapped_token: TOKEN, native_nav_asset_id: ASSET,
    driver_bin: process.execPath, driver_args: ['run-job', '--job-file', '{job_file}'],
    readiness_args: ['readiness'], cwd: process.cwd(), max_amount_atoms: '250000000000',
    worker_timeout_ms: 60_000,
};

function request(amount = '5000000') {
    return {
        route_id: ROUTE_ID, route_config_digest: ROUTE_DIGEST, transaction_hash: TX,
        ethereum_sender: `0x${'22'.repeat(20)}`, pftl_recipient: `pf${'33'.repeat(20)}`,
        native_nav_asset_id: ASSET, amount_atoms: amount, return_nonce: '44'.repeat(32),
    };
}

(async () => {
    assert.throws(
        () => create({}, { config: { ...config, readiness_timeout_ms: 99 } }),
        /readiness timeout.*supported range/,
    );
    assert.throws(
        () => create({}, { config: { ...config, readiness_args: new Array(65).fill('x') } }),
        /readiness arguments.*bound/,
    );
    assert.strictEqual(terminalError(new Error('temporary Ethereum RPC failure')), false);
    assert.strictEqual(terminalError(Object.assign(new Error('binding'), { terminal: true })), true);
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pft-navcoin-return-jobs-'));
    let nextPid = 700_000;
    const alive = new Set();
    const spawns = [];
    const options = {
        root, config, watchdogMs: 60_000,
        execFileAsync: async () => ({ stdout: JSON.stringify({
            ok: true, ready: true, route_id: ROUTE_ID, route_config_digest: ROUTE_DIGEST,
            controller: CONTROLLER,
        }) }),
        processAlive: pid => alive.has(pid),
        processStartToken: pid => alive.has(pid) ? `start-${pid}` : null,
        spawn: (bin, args) => {
            const child = new EventEmitter();
            child.pid = ++nextPid;
            child.unref = () => {};
            child.kill = signal => { alive.delete(child.pid); child.killedWith = signal; return true; };
            alive.add(child.pid);
            spawns.push({ bin, args, child });
            return child;
        },
    };
    const subject = create({}, options);
    try {
        assert.strictEqual((await subject.navcoinReturnRelayReadiness(ROUTE_ID)).ready, true);
        assert.strictEqual((await subject.navcoinReturnRelayReadiness(OTHER_ROUTE_ID)).ready, false);
        const jobs = await Promise.all([
            subject.submitNavcoinReturnRelayJob(request()),
            subject.submitNavcoinReturnRelayJob(request()),
        ]);
        assert.strictEqual(jobs[0].job_id, canonicalJobId(ROUTE_ID, TX));
        assert.notStrictEqual(canonicalJobId(ROUTE_ID, TX), canonicalJobId(OTHER_ROUTE_ID, TX));
        assert.deepStrictEqual(jobs.map(row => row.idempotent_replay).sort(), [false, true]);
        assert.strictEqual(spawns.length, 1, 'idempotent replay must launch one return worker');
        assert.strictEqual(subject.navcoinReturnRelayJobsForRecipient(ROUTE_ID, request().pftl_recipient, 20).length, 1);
        assert.strictEqual(subject.navcoinReturnRelayJobsForRecipient(ROUTE_ID, `pf${'99'.repeat(20)}`, 20).length, 0);
        await assert.rejects(subject.submitNavcoinReturnRelayJob(request('6000000')),
            error => error.code === 'navcoin_return_job_binding_conflict');
        assert.strictEqual(subject.navcoinReturnRelayJobStatus(OTHER_ROUTE_ID, jobs[0].job_id), null);
        subject.closeNavcoinReturnRelayJobs();
        assert.strictEqual(spawns[0].child.killedWith, 'SIGTERM');
    } finally {
        subject.closeNavcoinReturnRelayJobs();
        fs.rmSync(root, { recursive: true, force: true });
    }
    // amount_atoms must be a canonical unsigned decimal before BigInt(): the raw string is bound
    // into job.json and the request fingerprint, and the worker driver refuses anything else.
    const amountRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'pft-navcoin-return-amount-'));
    const amountJobs = create({}, {
        ...options, root: amountRoot,
        config: { ...config, max_amount_atoms: '18446744073709551615' },
    });
    try {
        let txCounter = 0;
        const nextTx = () => `0x${(0xa000 + (++txCounter)).toString(16).padStart(64, '0')}`;
        const withAmount = (amount, tx) => ({ ...request(), amount_atoms: amount, transaction_hash: tx });
        for (const [amount, stored] of [
            ['100', '100'], ['1', '1'], ['18446744073709551615', '18446744073709551615'],
            [100, '100'], [' 100 ', '100'],
        ]) {
            const job = await amountJobs.submitNavcoinReturnRelayJob(withAmount(amount, nextTx()));
            assert.strictEqual(job.request.amount_atoms, stored, `amount ${JSON.stringify(amount)} must be accepted`);
        }
        for (const amount of [
            '0100', '0x64', '0o144', '0b1100100', '1e2', '-1', '0', '+1', '1.0',
            '18446744073709551616', '', 'abc', '9'.repeat(400),
        ]) {
            const tx = nextTx();
            await assert.rejects(amountJobs.submitNavcoinReturnRelayJob(withAmount(amount, tx)),
                error => error.code === 'invalid_navcoin_return_relay_request',
                `amount ${JSON.stringify(amount.slice(0, 24))} must be refused`);
            assert.strictEqual(amountJobs.navcoinReturnRelayJobStatus(ROUTE_ID, canonicalJobId(ROUTE_ID, tx)), null,
                `refused amount ${JSON.stringify(amount.slice(0, 24))} must not leave a job`);
        }
        // JSON.parse rounds numbers above 2^53-1 (9007199254740993 -> 9007199254740992): refuse them.
        for (const raw of ['9007199254740993', '9007199254740992', '18446744073709551615']) {
            const amount = JSON.parse(raw);
            const tx = nextTx();
            await assert.rejects(amountJobs.submitNavcoinReturnRelayJob(withAmount(amount, tx)),
                error => error.code === 'invalid_navcoin_return_relay_request',
                `JSON number amount ${raw} must be refused`);
            assert.strictEqual(amountJobs.navcoinReturnRelayJobStatus(ROUTE_ID, canonicalJobId(ROUTE_ID, tx)), null);
        }
        const safe = await amountJobs.submitNavcoinReturnRelayJob(withAmount(JSON.parse('9007199254740991'), nextTx()));
        assert.strictEqual(safe.request.amount_atoms, '9007199254740991');
        const exact = await amountJobs.submitNavcoinReturnRelayJob(withAmount('9007199254740993', nextTx()));
        assert.strictEqual(exact.request.amount_atoms, '9007199254740993');
        // A refused non-canonical amount must not bind the tx hash: the canonical request still queues.
        const boundTx = nextTx();
        await assert.rejects(amountJobs.submitNavcoinReturnRelayJob(withAmount('0x64', boundTx)),
            error => error.code === 'invalid_navcoin_return_relay_request');
        const canonical = await amountJobs.submitNavcoinReturnRelayJob(withAmount('100', boundTx));
        assert.strictEqual(canonical.job_id, canonicalJobId(ROUTE_ID, boundTx));
        assert.strictEqual(canonical.idempotent_replay, false);
        assert.strictEqual(canonical.request.amount_atoms, '100');
    } finally {
        amountJobs.closeNavcoinReturnRelayJobs();
        fs.rmSync(amountRoot, { recursive: true, force: true });
    }
    const disabled = create({}, { env: {} });
    assert.strictEqual((await disabled.navcoinReturnRelayReadiness(ROUTE_ID)).ready, false);
    await assert.rejects(disabled.submitNavcoinReturnRelayJob(request()),
        error => error.code === 'navcoin_return_relay_not_configured');

    const legacyRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'pft-a666-return-recovery-'));
    const legacyTx = `0x${'66'.repeat(32)}`;
    const legacyJobId = canonicalJobId(LEGACY_A666_ROUTE_ID, legacyTx);
    const legacyJobRoot = path.join(legacyRoot, 'jobs', legacyJobId.slice(2));
    fs.mkdirSync(legacyJobRoot, { recursive: true, mode: 0o700 });
    fs.writeFileSync(path.join(legacyJobRoot, 'job.json'), JSON.stringify({
        schema: 'postfiat-a666-return-relay-job-v1',
        job_id: legacyJobId,
        status: 'queued',
        request: {
            route_id: LEGACY_A666_ROUTE_ID,
            route_config_digest: ROUTE_DIGEST,
            transaction_hash: legacyTx,
        },
    }));
    fs.writeFileSync(path.join(legacyJobRoot, 'worker-state.json'), JSON.stringify({
        schema: 'postfiat-a666-return-relay-state-v1',
        job_id: legacyJobId,
        status: 'accepted',
        transaction_hash: legacyTx,
        route_id: LEGACY_A666_ROUTE_ID,
        updated_at_unix: Math.floor(Date.now() / 1000),
        retryable: false,
        return_burn_id: '77'.repeat(32),
    }));
    const legacy = create({}, {
        ...options,
        root: legacyRoot,
        config: { ...config, route_id: LEGACY_A666_ROUTE_ID },
    });
    try {
        assert.strictEqual(
            legacy.navcoinReturnRelayJobStatus(LEGACY_A666_ROUTE_ID, legacyJobId).status,
            'accepted',
            'the generic wallet must recover durable jobs written by the deployed A666 schema',
        );
    } finally {
        legacy.closeNavcoinReturnRelayJobs();
        fs.rmSync(legacyRoot, { recursive: true, force: true });
    }

    const multiRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'pft-navcoin-return-routes-'));
    const secondDigest = 'ee'.repeat(48);
    const secondController = `0x${'ff'.repeat(20)}`;
    const multi = create({}, {
        ...options,
        root: multiRoot,
        config: undefined,
        configs: [config, { ...config, route_id: OTHER_ROUTE_ID,
            route_config_digest: secondDigest, controller: secondController,
            readiness_args: ['readiness', '--route-id', OTHER_ROUTE_ID] }],
        execFileAsync: async (_bin, args) => {
            const second = args.includes(OTHER_ROUTE_ID);
            return { stdout: JSON.stringify({ ok: true, ready: true,
                route_id: second ? OTHER_ROUTE_ID : ROUTE_ID,
                route_config_digest: second ? secondDigest : ROUTE_DIGEST,
                controller: second ? secondController : CONTROLLER }) };
        },
    });
    try {
        assert.strictEqual((await multi.navcoinReturnRelayReadiness(ROUTE_ID)).ready, true);
        assert.strictEqual((await multi.navcoinReturnRelayReadiness(OTHER_ROUTE_ID)).ready, true);
    } finally {
        multi.closeNavcoinReturnRelayJobs();
        fs.rmSync(multiRoot, { recursive: true, force: true });
    }
})().catch((error) => {
    process.stderr.write(`${error.stack || error}\n`);
    process.exitCode = 1;
});
