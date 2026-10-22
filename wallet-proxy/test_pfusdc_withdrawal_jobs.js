'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { create, jobId, normalizeRequest } = require('./pfusdc-withdrawal-jobs');

const assetId = '11'.repeat(48);
const request = normalizeRequest({
    burn_tx_id: '22'.repeat(48),
    owner: `pf${'33'.repeat(20)}`,
    ethereum_recipient: `0x${'44'.repeat(20)}`,
    amount_atoms: '1000000',
    asset_id: assetId,
}, assetId);
assert(/^[0-9a-f]{64}$/.test(jobId(request)));
assert.throws(() => normalizeRequest({ ...request, burn_tx_id: '22'.repeat(32) }, assetId), /Invalid pfUSDC/);
assert.throws(() => normalizeRequest({ ...request, seed: 'must never cross the relay boundary' }, assetId), /Invalid pfUSDC/);
// amount_atoms must be canonical decimal: BigInt() also parses prefixes and
// leading zeros, which would give one burn several job_ids.
for (const amount_atoms of [
    '0100', '0x64', '0o144', '0b1100100', '1e2', '-1', '0', '+1', '1.0',
    '18446744073709551616', '', 'abc', '9'.repeat(400),
]) {
    assert.throws(
        () => normalizeRequest({ ...request, amount_atoms }, assetId),
        /Invalid pfUSDC/,
        `amount_atoms ${JSON.stringify(amount_atoms).slice(0, 40)} must be refused`,
    );
}
for (const [amount_atoms, expected] of [
    ['100', '100'], ['1', '1'], ['18446744073709551615', '18446744073709551615'],
    [100, '100'], ['  100  ', '100'],
]) {
    assert.strictEqual(normalizeRequest({ ...request, amount_atoms }, assetId).amount_atoms, expected);
}
// JSON numbers are rounded by JSON.parse above 2^53-1, so they are accepted
// only as safe integers; larger amounts must arrive as decimal strings. Each
// case is parsed from a raw body string so the rounding really happens.
const parseAmount = (raw) => JSON.parse(`{"amount_atoms":${raw}}`).amount_atoms;
assert.strictEqual(parseAmount('9007199254740993'), 9007199254740992, 'JSON.parse rounds 2^53+1 down');
assert.strictEqual(parseAmount('9007199254740995'), 9007199254740996, 'JSON.parse rounds 2^53+3 up');
for (const raw of [
    '9007199254740993', '9007199254740995', '9007199254740992', '18446744073709551615',
    '1' + '0'.repeat(399), '-1', '0', '1.5', '100.5', '0.0',
]) {
    const amount_atoms = parseAmount(raw);
    assert.strictEqual(typeof amount_atoms, 'number');
    assert.throws(
        () => normalizeRequest({ ...request, amount_atoms }, assetId),
        /Invalid pfUSDC/,
        `JSON number amount_atoms ${raw.slice(0, 40)} must be refused`,
    );
}
for (const [raw, expected] of [
    ['9007199254740991', '9007199254740991'], ['100', '100'], ['1', '1'], ['1e2', '100'],
    ['"9007199254740993"', '9007199254740993'], ['"9007199254740995"', '9007199254740995'],
    ['"18446744073709551615"', '18446744073709551615'],
]) {
    assert.strictEqual(
        normalizeRequest({ ...request, amount_atoms: parseAmount(raw) }, assetId).amount_atoms,
        expected,
        `amount_atoms ${raw} must be preserved exactly`,
    );
}
for (const raw of [
    '"09007199254740993"', `"${'9'.repeat(400)}"`, '"-9007199254740993"', '"9007199254740993.0"',
    '"0"', '"1.5"',
]) {
    assert.throws(
        () => normalizeRequest({ ...request, amount_atoms: parseAmount(raw) }, assetId),
        /Invalid pfUSDC/,
        `string amount_atoms ${raw.slice(0, 40)} must be refused`,
    );
}
// The exact string amount and its rounded neighbour hash to different job_ids.
assert.notStrictEqual(
    jobId(normalizeRequest({ ...request, amount_atoms: parseAmount('"9007199254740993"') }, assetId)),
    jobId(normalizeRequest({ ...request, amount_atoms: parseAmount('"9007199254740992"') }, assetId)),
);
// The job_id hash scheme is unchanged for the canonical spelling.
assert.strictEqual(
    jobId(normalizeRequest({ ...request, amount_atoms: '100' }, assetId)),
    '514a998f4c415f8bb81cf652f4d906e84029793795fd8f407bdef1547e8ea0ed',
);

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pfusdc-withdrawal-jobs-'));
const script = path.join(root, 'worker.sh');
const config = path.join(root, 'config.json');
const prover = path.join(root, 'mock-prover-bin');
const elf = path.join(root, 'egress.elf');
const qualification = path.join(root, 'proof-report.json');
const vkey = `0x${'55'.repeat(32)}`;
fs.writeFileSync(script, '#!/bin/sh\nexit 0\n', { mode: 0o700 });
fs.writeFileSync(prover, '#!/bin/sh\nexit 0\n', { mode: 0o700 });
fs.writeFileSync(config, `${JSON.stringify({ pfusdc_egress_program_vkey: vkey })}\n`, { mode: 0o600 });
fs.writeFileSync(elf, 'elf', { mode: 0o600 });
fs.writeFileSync(qualification, `${JSON.stringify({ schema: 'postfiat.pfusdc.egress_proof_report.v1', program_vkey: vkey, proof_mode: 'groth16', proof_bytes: 356, public_values_bytes: 1486 })}\n`, { mode: 0o600 });

(async () => {
  const disabled = create({}, { env: {} });
  const readiness = await disabled.pfusdcWithdrawalReadiness();
    assert.strictEqual(readiness.ready, false);
  const enabled = create({}, { env: {
    PFUSDC_WITHDRAWAL_ENABLED: 'true', PFUSDC_ASSET_ID: assetId,
    PFUSDC_WITHDRAWAL_JOB_ROOT: path.join(root, 'jobs'),
    PFUSDC_WITHDRAWAL_SCRIPT: script, PFUSDC_WITHDRAWAL_CONFIG_FILE: config,
    PFUSDC_WITHDRAWAL_LOCAL_PROVER_BIN: prover, PFUSDC_WITHDRAWAL_EGRESS_ELF: elf,
    PFUSDC_WITHDRAWAL_QUALIFICATION_REPORT: qualification,
  } });
  assert.strictEqual((await enabled.pfusdcWithdrawalReadiness()).ready, true);
  enabled.closePfusdcWithdrawalJobs();

  const retryRoot = path.join(root, 'retry');
  const retryId = jobId(request);
  const retryDir = path.join(retryRoot, 'jobs', retryId);
  fs.mkdirSync(retryDir, { recursive: true, mode: 0o700 });
  const now = Math.floor(Date.now() / 1000);
  fs.writeFileSync(path.join(retryDir, 'job.json'), `${JSON.stringify({
    schema: 'postfiat-pfusdc-wallet-withdrawal-job-v1', job_id: retryId,
    status: 'failed', stage: 'Needs support', request, attempts: 3,
    created_at_unix: now, updated_at_unix: now,
    code: 'pfusdc_withdrawal_worker_failed', message: 'recoverable failure',
  }, null, 2)}\n`, { mode: 0o600 });
  const retryEnabled = create({}, { env: {
    PFUSDC_WITHDRAWAL_ENABLED: 'true', PFUSDC_ASSET_ID: assetId,
    PFUSDC_WITHDRAWAL_JOB_ROOT: retryRoot,
    PFUSDC_WITHDRAWAL_SCRIPT: script, PFUSDC_WITHDRAWAL_CONFIG_FILE: config,
    PFUSDC_WITHDRAWAL_LOCAL_PROVER_BIN: prover, PFUSDC_WITHDRAWAL_EGRESS_ELF: elf,
    PFUSDC_WITHDRAWAL_QUALIFICATION_REPORT: qualification,
  } });
  const retried = await retryEnabled.retryPfusdcWithdrawalJob(retryId);
  assert.strictEqual(retried.status, 'queued');
  assert.strictEqual(retried.idempotent_replay, false);
  assert.match(retried.stage, /Resuming safely/);
  retryEnabled.closePfusdcWithdrawalJobs();

  const orderedRoot = path.join(root, 'ordered');
  const laterRequest = normalizeRequest({
    ...request,
    burn_tx_id: '66'.repeat(48),
  }, assetId);
  const laterId = jobId(laterRequest);
  const paidDir = path.join(orderedRoot, 'jobs', retryId);
  const laterDir = path.join(orderedRoot, 'jobs', laterId);
  fs.mkdirSync(path.join(paidDir, 'pfusdc-egress'), { recursive: true, mode: 0o700 });
  fs.mkdirSync(laterDir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(path.join(paidDir, 'pfusdc-egress', 'withdrawal-result.json'), '{}\n', { mode: 0o600 });
  fs.writeFileSync(path.join(paidDir, 'job.json'), `${JSON.stringify({
    schema: 'postfiat-pfusdc-wallet-withdrawal-job-v1', job_id: retryId,
    status: 'failed', stage: 'Ethereum USDC received; accounting retry required',
    request, attempts: 3, created_at_unix: now, updated_at_unix: now,
  }, null, 2)}\n`, { mode: 0o600 });
  fs.writeFileSync(path.join(laterDir, 'job.json'), `${JSON.stringify({
    schema: 'postfiat-pfusdc-wallet-withdrawal-job-v1', job_id: laterId,
    status: 'queued', stage: 'Withdrawal burn confirmed', request: laterRequest,
    attempts: 0, created_at_unix: now + 1, updated_at_unix: now + 1,
  }, null, 2)}\n`, { mode: 0o600 });
  const ordered = create({}, { env: {
    PFUSDC_WITHDRAWAL_ENABLED: 'true', PFUSDC_ASSET_ID: assetId,
    PFUSDC_WITHDRAWAL_JOB_ROOT: orderedRoot,
    PFUSDC_WITHDRAWAL_SCRIPT: script, PFUSDC_WITHDRAWAL_CONFIG_FILE: config,
    PFUSDC_WITHDRAWAL_LOCAL_PROVER_BIN: prover, PFUSDC_WITHDRAWAL_EGRESS_ELF: elf,
    PFUSDC_WITHDRAWAL_QUALIFICATION_REPORT: qualification,
  } });
  const orderedJobs = ordered.pfusdcWithdrawalJobsForOwner(request.owner);
  assert.strictEqual(orderedJobs.find(job => job.job_id === retryId).status, 'failed');
  assert.strictEqual(orderedJobs.find(job => job.job_id === laterId).status, 'queued');
  ordered.closePfusdcWithdrawalJobs();
  fs.unlinkSync(path.join(paidDir, 'pfusdc-egress', 'withdrawal-result.json'));
  const unpaidOrdered = create({}, { env: {
    PFUSDC_WITHDRAWAL_ENABLED: 'true', PFUSDC_ASSET_ID: assetId,
    PFUSDC_WITHDRAWAL_JOB_ROOT: orderedRoot,
    PFUSDC_WITHDRAWAL_SCRIPT: script, PFUSDC_WITHDRAWAL_CONFIG_FILE: config,
    PFUSDC_WITHDRAWAL_LOCAL_PROVER_BIN: prover, PFUSDC_WITHDRAWAL_EGRESS_ELF: elf,
    PFUSDC_WITHDRAWAL_QUALIFICATION_REPORT: qualification,
  } });
  assert.strictEqual(unpaidOrdered.pfusdcWithdrawalJobStatus(laterId).status, 'queued');
  unpaidOrdered.closePfusdcWithdrawalJobs();

  // pre-#101 jobs: the proxy used to store any trimmed amount spelling BigInt()
  // parses in 1..2^64-1 and hash it into job_id. Those jobs must stay readable,
  // be resumed and keep blocking later burns, with the stored spelling kept.
  const legacyEnv = jobRoot => ({ env: {
    PFUSDC_WITHDRAWAL_ENABLED: 'true', PFUSDC_ASSET_ID: assetId,
    PFUSDC_WITHDRAWAL_JOB_ROOT: jobRoot,
    PFUSDC_WITHDRAWAL_SCRIPT: script, PFUSDC_WITHDRAWAL_CONFIG_FILE: config,
    PFUSDC_WITHDRAWAL_LOCAL_PROVER_BIN: prover, PFUSDC_WITHDRAWAL_EGRESS_ELF: elf,
    PFUSDC_WITHDRAWAL_QUALIFICATION_REPORT: qualification,
  } });
  const seed = (jobRoot, id, stored, status, createdAt) => {
    fs.mkdirSync(path.join(jobRoot, 'jobs', id), { recursive: true, mode: 0o700 });
    fs.writeFileSync(path.join(jobRoot, 'jobs', id, 'job.json'), `${JSON.stringify({
      schema: 'postfiat-pfusdc-wallet-withdrawal-job-v1', job_id: id, status,
      stage: status === 'failed' ? 'Needs support' : 'Withdrawal burn confirmed',
      request: stored, attempts: status === 'failed' ? 3 : 0,
      created_at_unix: createdAt, updated_at_unix: createdAt,
    }, null, 2)}\n`, { mode: 0o600 });
  };
  const onDisk = (jobRoot, id) => JSON.parse(fs.readFileSync(path.join(jobRoot, 'jobs', id, 'job.json'), 'utf8'));
  const legacySpellings = ['0100', '+100', '0x64', '0X64', '0o144', '0b1100100', `${'0'.repeat(40)}100`, '018446744073709551615'];
  for (const [index, amount_atoms] of legacySpellings.entries()) {
    const legacyRoot = path.join(root, `legacy-${index}`);
    const stored = { ...request, amount_atoms };
    assert.throws(() => normalizeRequest(stored, assetId), /Invalid pfUSDC/);
    const legacyId = jobId(stored);
    seed(legacyRoot, legacyId, stored, 'failed', now);
    seed(legacyRoot, laterId, laterRequest, 'queued', now + 1);
    const legacy = create({}, legacyEnv(legacyRoot));
    const status = legacy.pfusdcWithdrawalJobStatus(legacyId.toUpperCase());
    assert.strictEqual(status?.status, 'failed', `pre-#101 amount ${amount_atoms} must stay readable`);
    assert.strictEqual(status.request.amount_atoms, amount_atoms);
    assert.deepStrictEqual(Object.keys(status.request), Object.keys(request));
    assert.deepStrictEqual(
      legacy.pfusdcWithdrawalJobsForOwner(request.owner).map(job => job.job_id),
      [laterId, legacyId],
    );
    assert.strictEqual(legacy.pfusdcWithdrawalJobStatus(laterId).status, 'queued',
      `a failed pre-#101 job (${amount_atoms}) must block the later burn`);
    legacy.closePfusdcWithdrawalJobs();
  }

  // A pre-#101 job that was in flight is resumed and a failed one can be
  // retried; neither rewrites the stored spelling. An earlier canonical failed
  // burn holds the queue so no worker starts.
  const resumeRoot = path.join(root, 'legacy-resume');
  const blocker = normalizeRequest({ ...request, burn_tx_id: '77'.repeat(48) }, assetId);
  const running = { ...request, amount_atoms: '0100' };
  const failed = { ...request, burn_tx_id: '88'.repeat(48), amount_atoms: '0x64' };
  seed(resumeRoot, jobId(blocker), blocker, 'failed', now - 10);
  seed(resumeRoot, jobId(running), { ...running }, 'running', now);
  seed(resumeRoot, jobId(failed), { ...failed }, 'failed', now + 1);
  const resumed = create({}, legacyEnv(resumeRoot));
  const resumedJob = resumed.pfusdcWithdrawalJobStatus(jobId(running));
  assert.strictEqual(resumedJob?.status, 'queued');
  assert.match(resumedJob.stage, /Resuming safely/);
  assert.deepStrictEqual(onDisk(resumeRoot, jobId(running)).request, running);
  const legacyRetry = await resumed.retryPfusdcWithdrawalJob(jobId(failed).toUpperCase());
  assert.strictEqual(legacyRetry?.status, 'queued');
  assert.strictEqual(legacyRetry.idempotent_replay, false);
  assert.deepStrictEqual(onDisk(resumeRoot, jobId(failed)).request, failed);
  assert.strictEqual(resumed.pfusdcWithdrawalJobStatus(jobId(running)).status, 'queued');
  // New requests keep #101's canonical-only rule, and a pre-#101 job_id is not
  // reachable through submit.
  await assert.rejects(
    resumed.submitPfusdcWithdrawalJob({ ...request, amount_atoms: '0100' }),
    error => error.code === 'pfusdc_withdrawal_request_invalid',
  );
  resumed.closePfusdcWithdrawalJobs();

  // Refused as before: only the exact spelling hashed into job_id is readable,
  // and only under the pre-#101 rule, as a string, trimmed, with the five fields.
  const refusedRoot = path.join(root, 'legacy-refused');
  const refused = [
    ...['1e2', '-1', '0', '-0', '1.0', '18446744073709551616', '', 'abc', '9'.repeat(400), '+0x64', '1_000']
      .map(amount_atoms => ({ ...request, amount_atoms })),
    ...[' 100', '100 ', '0100\n', ' 100'].map(amount_atoms => ({ ...request, amount_atoms })),
    { ...request, amount_atoms: '0100', seed: 'x' },
    { burn_tx_id: request.burn_tx_id, owner: request.owner, ethereum_recipient: request.ethereum_recipient, amount_atoms: '0100' },
    { ...request, amount_atoms: 18446744073709551615 },
    { ...request, amount_atoms: '0100', owner: request.owner.toUpperCase() },
    { ...request, amount_atoms: '0100', burn_tx_id: `0x${request.burn_tx_id}` },
    { ...request, amount_atoms: '0100', ethereum_recipient: ` ${request.ethereum_recipient}` },
    { ...request, amount_atoms: '0100', asset_id: '12'.repeat(48) },
  ];
  refused.forEach((stored, index) => {
    const id = jobId(stored);
    seed(refusedRoot, id, stored, 'failed', now + index);
  });
  // job_id must be the hash of the stored spelling: a 0100 request filed under
  // the canonical 100 job_id is not readable.
  const mismatchId = jobId(normalizeRequest({ ...request, amount_atoms: '100' }, assetId));
  seed(refusedRoot, mismatchId, { ...request, amount_atoms: '0100' }, 'failed', now);
  const refusing = create({}, legacyEnv(refusedRoot));
  for (const stored of refused) {
    assert.strictEqual(refusing.pfusdcWithdrawalJobStatus(jobId(stored)), null,
      `stored request ${JSON.stringify(stored).slice(0, 80)} must stay unreadable`);
  }
  assert.strictEqual(refusing.pfusdcWithdrawalJobStatus(mismatchId), null);
  assert.deepStrictEqual(refusing.pfusdcWithdrawalJobsForOwner(request.owner), []);
  refusing.closePfusdcWithdrawalJobs();

  fs.chmodSync(elf, 0o622);
  assert.throws(() => create({}, { env: {
    PFUSDC_WITHDRAWAL_ENABLED: 'true', PFUSDC_ASSET_ID: assetId,
    PFUSDC_WITHDRAWAL_JOB_ROOT: path.join(root, 'unsafe'),
    PFUSDC_WITHDRAWAL_SCRIPT: script, PFUSDC_WITHDRAWAL_CONFIG_FILE: config,
    PFUSDC_WITHDRAWAL_LOCAL_PROVER_BIN: prover, PFUSDC_WITHDRAWAL_EGRESS_ELF: elf,
    PFUSDC_WITHDRAWAL_QUALIFICATION_REPORT: qualification,
  } }), /owner-controlled/);
  fs.rmSync(root, { recursive: true });
  console.log('pfUSDC withdrawal jobs regression passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
