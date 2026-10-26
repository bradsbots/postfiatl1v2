import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { parseNavcoinUnits } from './navcoin-primary-route.js';
import * as utils from './utils.js';

// The pfUSDC withdraw field's own pattern (BridgeWithdraw.jsx `atoms()`).
const WITHDRAW_AMOUNT_RE = /^\d+(\.\d{0,6})?$/;

function component(name) {
  return readFileSync(new URL(`../components/${name}`, import.meta.url), 'utf8');
}

test('MAX amounts are written as plain decimals the amount fields accept', () => {
  assert.equal(typeof utils.formatAmountInput, 'function', 'utils.js exports formatAmountInput');
  const cases = [
    [999_500_000n, '999.5'],
    [1_000_000_000n, '1000'],
    [1_234_500_000n, '1234.5'],
    [9_007_199_254_740_991n, '9007199254.740991'],
    [1n, '0.000001'],
  ];
  for (const [atoms, expected] of cases) {
    const field = utils.formatAmountInput(atoms, 6);
    assert.equal(field, expected);
    assert.equal(parseNavcoinUnits(field, 6), atoms, `NAV-coin field accepts ${field}`);
    assert.match(field, WITHDRAW_AMOUNT_RE, `withdraw field accepts ${field}`);
  }
  assert.equal(utils.formatAmountInput('1234500000', 6), '1234.5');
  assert.equal(utils.formatAmountInput(1_234_500n, 3), '1234.5');
  assert.equal(utils.formatAmountInput(1_000n, 0), '1000');
});

test('MAX amounts do not depend on the browser locale', () => {
  const script = [
    "const { formatAmountInput } = await import('./src/lib/utils.js');",
    "const { parseNavcoinUnits } = await import('./src/lib/navcoin-primary-route.js');",
    "const field = formatAmountInput(1234500000n, 6);",
    'process.stdout.write(`${field} ${parseNavcoinUnits(field, 6)}`);',
  ].join('\n');
  for (const locale of ['en_US.UTF-8', 'de_DE.UTF-8', 'fr_FR.UTF-8']) {
    const run = spawnSync(process.execPath, ['--input-type=module', '-e', script], {
      cwd: new URL('../../', import.meta.url),
      env: { ...process.env, LC_ALL: locale, LANG: locale },
      encoding: 'utf8',
    });
    assert.equal(run.status, 0, run.stderr);
    assert.equal(run.stdout, '1234.5 1234500000', locale);
  }
});

test('MAX buttons fill the amount field with formatAmountInput', () => {
  const navcoin = component('NavcoinPrimaryMarket.jsx');
  assert.match(navcoin, /setAmount\(formatAmountInput\(maximum, market\.decimals\)\)/);
  assert.doesNotMatch(navcoin, /setAmount\(formatNavcoinUnits\(/);
  const withdraw = component('BridgeWithdraw.jsx');
  assert.match(withdraw, /setAmount\(formatAmountInput\(maximum, 6\)\)/);
  assert.doesNotMatch(withdraw, /setAmount\(units\(/);
});
