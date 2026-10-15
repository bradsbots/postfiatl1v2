'use strict';

function parseBooleanValue(name, raw, fallback) {
    if (raw === undefined || String(raw).trim() === '') return fallback;
    const token = String(raw).trim().toLowerCase();
    if (token === 'true' || token === '1') return true;
    if (token === 'false' || token === '0') return false;
    throw new Error(`${name} must be true or false`);
}

function parseBooleanEnv(name, fallback) {
    return parseBooleanValue(name, process.env[name], fallback);
}

module.exports = { parseBooleanEnv, parseBooleanValue };
