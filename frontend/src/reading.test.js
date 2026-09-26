import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readingForLanguage, resolvePlayback } from './reading.js';

test('the ordinal persists through language changes without using the other language file', () => {
  assert.equal(readingForLanguage('fa_2', 'azb'), 'azb_2');
  assert.equal(readingForLanguage('azb_2', 'fa'), 'fa_2');
  assert.equal(readingForLanguage('fa_5', 'azb'), null);
});

test('only the selected Reading continues on the next page; a missing slot never falls back', () => {
  const available = [{ id: 'fa_1', audio_url: '/api/book/audio/next/fa_1' }];
  assert.equal(resolvePlayback('fa_1', available, true).shouldPlay, true);
  assert.equal(resolvePlayback('fa_1', available, false).shouldPlay, false);
  assert.deepEqual(resolvePlayback('fa_2', available, true),
    { selected: null, missing: true, shouldPlay: false });
});
