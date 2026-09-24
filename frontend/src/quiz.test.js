import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { makeQuiz } from './quiz.js';

const questions = ['recall', 'infer', 'think'].flatMap((category) => [1, 2, 3].map((n) => ({
  id: `${category}-${n}`, category, answer_id: 'a',
  options: [{ id: 'a' }, { id: 'b' }, { id: 'c' }],
})));

test('three categories and immediate replay use different questions', () => {
  const first = makeQuiz(questions, {}, () => 0);
  const second = makeQuiz(questions, first.memory, () => 0);
  assert.deepEqual(first.items.map((x) => x.category), ['recall', 'infer', 'think']);
  for (let i = 0; i < 3; i++) assert.notEqual(first.items[i].id, second.items[i].id);
});

test('a single question still changes answer position on replay', () => {
  const one = [questions[0]];
  const first = makeQuiz(one, {}, () => 0);
  const second = makeQuiz(one, first.memory, () => 0);
  assert.notEqual(first.memory.positions[one[0].id], second.memory.positions[one[0].id]);
});
