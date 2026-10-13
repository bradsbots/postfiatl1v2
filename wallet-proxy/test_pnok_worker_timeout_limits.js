'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { isDeepStrictEqual } = require('node:util');
const vectors = require('./pnok-worker-timeout-vectors.json');

// Guard effects independently of the module's injected watchdog. No timer runs.
let nativeTimerAttempts = 0;
const timerGuard = () => {
    nativeTimerAttempts += 1;
    throw new Error('native timer is outside the configuration-admission test');
};
const originalSetTimeout = global.setTimeout;
const originalSetInterval = global.setInterval;
global.setTimeout = timerGuard;
global.setInterval = timerGuard;

function tagged(value) {
    return typeof value === 'number' && !Number.isFinite(value)
        ? { nonfinite: String(value) } : value;
}

function materialize(config, recipe) {
    switch (recipe.kind) {
        case 'omit': return;
        case 'null': config.worker_timeout_ms = null; return;
        case 'number':
        case 'string':
        case 'boolean': config.worker_timeout_ms = recipe.value; return;
        case 'nonfinite':
            assert.ok(recipe.value === 'NaN' || recipe.value === 'Infinity');
            config.worker_timeout_ms = recipe.value === 'NaN' ? Number.NaN : Number.POSITIVE_INFINITY;
            return;
        default: throw new Error(`unsupported input recipe ${recipe.kind}`);
    }
}

function entries(directory) {
    return fs.existsSync(directory) ? fs.readdirSync(directory).sort() : null;
}

const records = [];
try {
    const modulePath = require.resolve('./pnok-fix-jobs');
    const sourceSha256 = crypto.createHash('sha256').update(fs.readFileSync(modulePath)).digest('hex');
    const { create } = require(modulePath);
    for (const vector of vectors.cases) {
        const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pnok-timeout-admission-'));
        const jobsRoot = path.join(root, 'jobs');
        const config = { ...vectors.config };
        materialize(config, vector.timeout_input);
        const rawInput = {
            js_typeof: typeof config.worker_timeout_ms,
            own_property: Object.hasOwn(config, 'worker_timeout_ms'),
            tagged_value: Object.hasOwn(config, 'worker_timeout_ms')
                ? tagged(config.worker_timeout_ms) : { omitted: true },
        };
        assert.deepStrictEqual(rawInput, vector.expected_raw_input, vector.id);
        const observed = {
            admitted: false, exception_class: null, exception_code: null, exception_message: null,
            returned_api_keys: null, close_called: false,
            root_entries_before: entries(root), jobs_root_exists_before: fs.existsSync(jobsRoot),
            root_entries_after_create: null, jobs_root_exists_after_create: false,
            jobs_entries_after_create: null, root_entries_after_close: null, jobs_entries_after_close: null,
            set_interval_calls: 0, set_interval_delay_ms: null, watchdog_unref_calls: 0,
            interval_callback_invocations: 0, clear_interval_calls: 0, clear_interval_token_matches: null,
            spawn_calls: 0, fetch_calls: 0, process_alive_calls: 0,
        };
        assert.deepStrictEqual(observed.root_entries_before, []);
        assert.equal(observed.jobs_root_exists_before, false);
        const forbidden = (counter) => () => {
            observed[counter] += 1;
            throw new Error(`${counter} is outside the configuration-admission test`);
        };
        const token = { unref() { observed.watchdog_unref_calls += 1; } };
        let subject;
        try {
            try {
                subject = create({}, {
                    config, env: {}, root, now: () => 1900000000000,
                    spawn: forbidden('spawn_calls'), fetch: forbidden('fetch_calls'),
                    processAlive: forbidden('process_alive_calls'),
                    setInterval(callback, delay) {
                        assert.equal(typeof callback, 'function');
                        observed.set_interval_calls += 1;
                        observed.set_interval_delay_ms = delay;
                        // The callback is deliberately never invoked.
                        return token;
                    },
                    clearInterval(actualToken) {
                        observed.clear_interval_calls += 1;
                        observed.clear_interval_token_matches = actualToken === token;
                    },
                });
                observed.admitted = true;
                observed.returned_api_keys = Object.keys(subject).sort();
            } catch (error) {
                observed.exception_class = error.constructor.name;
                observed.exception_code = error.code ?? null;
                observed.exception_message = error.message;
            }
            observed.root_entries_after_create = entries(root);
            observed.jobs_root_exists_after_create = fs.existsSync(jobsRoot);
            observed.jobs_entries_after_create = entries(jobsRoot);
            if (subject) {
                subject.closePnokFixWalletJobs();
                observed.close_called = true;
            }
            observed.root_entries_after_close = entries(root);
            observed.jobs_entries_after_close = entries(jobsRoot);
            const baseExpected = vectors.outcomes[vector.base_admitted ? 'admitted' : 'rejected'];
            const fixedExpected = vectors.outcomes[vector.fixed_admitted ? 'admitted' : 'rejected'];
            const record = {
                id: vector.id, timeout_input: vector.timeout_input, raw_input: rawInput,
                supplied_config: JSON.parse(JSON.stringify(config, (_key, value) => tagged(value))),
                observed, matches_base: isDeepStrictEqual(observed, baseExpected),
                matches_fixed: isDeepStrictEqual(observed, fixedExpected),
            };
            records.push(record);
            console.log(JSON.stringify({ case: record }));
            assert.equal(observed.spawn_calls + observed.fetch_calls + observed.process_alive_calls, 0);
            assert.equal(nativeTimerAttempts, 0);
        } finally {
            fs.rmSync(root, { recursive: true, force: true });
        }
    }
    const summary = {
        runtime: process.version, source_sha256: sourceSha256,
        oracle_sha256: vectors.independent_oracle_sha256, cases: records.length,
        admitted: records.filter((record) => record.observed.admitted).length,
        rejected: records.filter((record) => !record.observed.admitted).length,
        base_mismatches: records.filter((record) => !record.matches_base).map((record) => record.id),
        fixed_mismatches: records.filter((record) => !record.matches_fixed).map((record) => record.id),
        native_timer_attempts: nativeTimerAttempts,
    };
    console.log(JSON.stringify({ summary }));
    assert.deepStrictEqual(summary.fixed_mismatches, [], 'PNOK worker timeout configuration limits');
    console.log('PNOK worker timeout admission tests passed (25/25)');
} finally {
    global.setTimeout = originalSetTimeout;
    global.setInterval = originalSetInterval;
}
