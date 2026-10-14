'use strict';

function parseBooleanEnv(name, fallback) {
    const raw = process.env[name];
    if (raw === undefined || String(raw).trim() === '') return fallback;
    const token = String(raw).trim().toLowerCase();
    if (token === 'true' || token === '1') return true;
    if (token === 'false' || token === '0') return false;
    throw new Error(`${name} must be true or false`);
}

module.exports = { parseBooleanEnv };
