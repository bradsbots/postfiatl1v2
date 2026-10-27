import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import {
  CHAIN_ID,
  GENESIS_HASH,
  LEGACY_CHAIN_IDS,
} from './utils.js';

test('public wallet defaults are bound to the live WAN devnet domain', () => {
  assert.equal(CHAIN_ID, 'postfiat-wan-devnet-2');
  assert.equal(
    GENESIS_HASH,
    'ce22ca8c932da0998b484483a09647138a30e0bf44408dd49a8d6d452787ad25521aff3ed334da07e150a7233a3e90a9',
  );
  assert.deepEqual(LEGACY_CHAIN_IDS, ['postfiat-wan-devnet']);
});

// formatBalance must not follow the browser locale: WalletHome's wrap/unwrap
// Max and Half fill `formatBalance(balance).replace(/,/g, '')` and parse it
// with pftToAtoms, so any other grouping separator changes the amount.
test('formatBalance groups with en-US separators in every locale', () => {
  const script = [
    "const { formatBalance, pftToAtoms } = await import('./src/lib/utils.js');",
    'const out = [5000000000n, 1234500000n, 999500000n].map((atoms) => {',
    '  const shown = formatBalance(atoms);',
    "  return `${shown}=${pftToAtoms(shown.replace(/,/g, ''))}`;",
    '});',
    "process.stdout.write(out.join(' '));",
  ].join('\n');
  for (const locale of ['en_US.UTF-8', 'de_DE.UTF-8', 'fr_FR.UTF-8']) {
    const run = spawnSync(process.execPath, ['--input-type=module', '-e', script], {
      cwd: new URL('../../', import.meta.url),
      env: { ...process.env, LC_ALL: locale, LANG: locale },
      encoding: 'utf8',
    });
    assert.equal(run.status, 0, run.stderr);
    assert.equal(run.stdout, '5,000=5000000000 1,234.5=1234500000 999.5=999500000', locale);
  }
});
