import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  AddressError,
  checksumAddress,
  displayAddress,
  isCanonicalAddress,
  parseAddress,
  sha3_256,
} from './address.js';

const vectors = JSON.parse(
  readFileSync(
    new URL('../../docs/fixtures/addresses/pftl-address-vectors-v1.json', import.meta.url),
    'utf8',
  ),
);

test('pure-JS SHA3-256 matches node crypto across block boundaries', () => {
  for (const length of [0, 1, 40, 69, 135, 136, 137, 271, 272, 500]) {
    const input = new Uint8Array(length);
    for (let index = 0; index < length; index += 1) input[index] = (index * 131 + length) & 0xff;
    const expected = createHash('sha3-256').update(input).digest('hex');
    assert.equal(Buffer.from(sha3_256(input)).toString('hex'), expected, `length ${length}`);
  }
});

test('published vectors: valid lowercase and checksummed addresses', () => {
  assert.equal(vectors.schema, 'postfiat.address_vectors.v1');
  assert.equal(vectors.checksum_domain, 'postfiat.address.checksum.v1');
  assert.ok(vectors.valid.length >= 4);
  for (const vector of vectors.valid) {
    assert.ok(isCanonicalAddress(vector.canonical), vector.canonical);
    assert.equal(parseAddress(vector.canonical), vector.canonical);
    assert.equal(parseAddress(vector.checksummed), vector.canonical);
    assert.equal(checksumAddress(vector.canonical), vector.checksummed);
    assert.equal(checksumAddress(vector.checksummed), vector.checksummed);
    assert.equal(displayAddress(vector.canonical), vector.checksummed);
  }
});

test('published vectors: wrong checksums are a distinct error', () => {
  assert.ok(vectors.invalid_checksum.length > 0);
  for (const vector of vectors.invalid_checksum) {
    assert.throws(
      () => parseAddress(vector.input),
      (error) => error instanceof AddressError && error.reason === 'bad_checksum' && !error.malformed,
      vector.input,
    );
    assert.equal(isCanonicalAddress(vector.input), false);
  }
});

test('published vectors: malformed addresses are rejected with their reason', () => {
  assert.ok(vectors.malformed.length >= 4);
  for (const vector of vectors.malformed) {
    assert.throws(
      () => parseAddress(vector.input),
      (error) => error instanceof AddressError && error.reason === vector.reason && error.malformed,
      JSON.stringify(vector.input),
    );
    assert.equal(isCanonicalAddress(vector.input), false);
    assert.equal(displayAddress(vector.input), vector.input);
  }
  assert.throws(() => parseAddress(undefined), AddressError);
  assert.throws(() => parseAddress(null), AddressError);
});

test('popup validates recipients through the checksum parser and signs the canonical form', () => {
  const popup = readFileSync(new URL('../popup/popup.js', import.meta.url), 'utf8');
  assert.match(popup, /from '\.\.\/lib\/address\.js'/);
  assert.match(popup, /parseAddress\(document\.getElementById\('sendTo'\)\.value\.trim\(\)\)/);
  assert.match(popup, /displayAddress\(walletAddress\)/);
});
