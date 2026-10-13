'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');

const {
    AMOUNT,
    CONFIRMATION,
    create,
    loopbackUpstream,
    requestJson,
} = require('./a666-roundtrip');

function withDeadline(promise, ms, label) {
    let timer;
    const deadline = new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${label}: still pending after ${ms} ms`)), ms);
    });
    return Promise.race([promise, deadline]).finally(() => clearTimeout(timer));
}

async function withUpstream(handler, run) {
    const upstream = http.createServer(handler);
    await new Promise((resolve) => upstream.listen(0, '127.0.0.1', resolve));
    try {
        return await run(new URL(`http://127.0.0.1:${upstream.address().port}`));
    } finally {
        upstream.closeAllConnections();
        await new Promise((resolve) => upstream.close(resolve));
    }
}

assert.throws(() => loopbackUpstream('https://127.0.0.1:8787'), /loopback HTTP/);
assert.throws(() => loopbackUpstream('http://example.com:8787'), /loopback HTTP/);
assert.equal(loopbackUpstream('http://localhost:8787').hostname, 'localhost');

(async () => {
    const calls = [];
    const service = create({}, {
        upstream: 'http://127.0.0.1:8787',
        requestJson: async (_upstream, pathname, options) => {
            calls.push({ pathname, options });
            return { statusCode: 200, payload: { ok: true } };
        },
    });

    await service.a666RoundtripStatus();
    await service.a666RoundtripStart({ amount: AMOUNT, confirmation: CONFIRMATION });
    assert.deepEqual(calls.map((call) => [call.pathname, call.options.method]), [
        ['/api/a666-roundtrip/status', 'GET'],
        ['/api/a666-roundtrip/start', 'POST'],
    ]);
    assert.deepEqual(calls[1].options.body, { amount: AMOUNT, confirmation: CONFIRMATION });
    await assert.rejects(
        service.a666RoundtripStart({ amount: '10000000', confirmation: CONFIRMATION }),
        /fixed 10\.000000 USDC/,
    );
    await assert.rejects(
        service.a666RoundtripStart({ amount: AMOUNT, confirmation: CONFIRMATION, private_key: 'forbidden' }),
        /fixed 10\.000000 USDC/,
    );

    const requests = [];
    const server = http.createServer((req, res) => {
        const chunks = [];
        req.on('data', (chunk) => chunks.push(chunk));
        req.on('end', () => {
            requests.push({
                authorization: req.headers.authorization,
                body: Buffer.concat(chunks).toString('utf8'),
                method: req.method,
                url: req.url,
            });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ok: true }));
        });
    });
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    try {
        const live = create({}, { upstream: `http://127.0.0.1:${server.address().port}` });
        await live.a666RoundtripStatus();
        await live.a666RoundtripStart({ amount: AMOUNT, confirmation: CONFIRMATION });
        assert.equal(requests[0].authorization, undefined, 'browser proxy bearer token must not reach StakeHub');
        assert.deepEqual(requests.map(({ method, url }) => [method, url]), [
            ['GET', '/api/a666-roundtrip/status'],
            ['POST', '/api/a666-roundtrip/start'],
        ]);
        assert.deepEqual(JSON.parse(requests[1].body), { amount: AMOUNT, confirmation: CONFIRMATION });
    } finally {
        await new Promise((resolve) => server.close(resolve));
    }

    // The loopback service drops the connection after headers and part of the body.
    await withUpstream((_req, res) => {
        res.writeHead(200, { 'Content-Type': 'application/json', 'Content-Length': '4096' });
        res.write('x'.repeat(100), () => res.socket.destroy());
    }, async (url) => {
        await withDeadline(assert.rejects(
            requestJson(url, '/x', { timeoutMs: 30_000 }),
            { code: 'a666_roundtrip_unavailable', message: 'A666 round-trip service closed the response early' },
        ), 2_000, 'mid-body disconnect');
    });

    // Complete responses still resolve, whatever the status code.
    await withUpstream((_req, res) => {
        res.writeHead(503, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'busy' }));
    }, async (url) => {
        assert.deepEqual(await requestJson(url, '/x'), { statusCode: 503, payload: { error: 'busy' } });
    });

    // Oversize and stall keep their own codes.
    await withUpstream((_req, res) => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        const chunk = Buffer.alloc(64 * 1024, 0x20);
        let sent = 0;
        const pump = () => {
            while (sent < 32 && !res.destroyed) {
                sent += 1;
                if (!res.write(chunk)) return res.once('drain', pump);
            }
            return undefined;
        };
        pump();
    }, async (url) => {
        await withDeadline(assert.rejects(
            requestJson(url, '/x', { timeoutMs: 30_000 }),
            { code: 'a666_roundtrip_response_too_large' },
        ), 2_000, 'oversize');
    });
    await withUpstream((_req, res) => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.write('{"ok":');
    }, async (url) => {
        await withDeadline(assert.rejects(
            requestJson(url, '/x', { timeoutMs: 200 }),
            { code: 'a666_roundtrip_timeout' },
        ), 2_000, 'stall');
    });

    // A refused connection is still unavailable.
    const closed = await withUpstream(() => {}, async (url) => url);
    await withDeadline(assert.rejects(
        requestJson(closed, '/x', { timeoutMs: 1_000 }),
        { code: 'a666_roundtrip_unavailable' },
    ), 2_000, 'refused');

    console.log('A666 round-trip proxy adapter passed');
})().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
