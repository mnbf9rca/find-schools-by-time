import assert from 'node:assert/strict';
import { COLUMNS, comparator, DEFAULT_SORT, reset, sort, toggle } from './sort.js';

const rows = [
  { name: 'Beta', minutes: 10, progress: -0.42, grade: 'A', aps: 45.0, best3_grade: 'A', best3_aps: 46.0 },
  { name: 'alpha', minutes: 2, progress: 0.18, grade: 'A+', aps: 50.44, best3_grade: 'A+', best3_aps: 50.58 },
  { name: 'Gamma', minutes: 20, progress: -1.5, grade: 'E', aps: 9.5, best3_grade: 'E', best3_aps: 9.0 },
  { name: 'Delta', minutes: 100, progress: null, grade: null, aps: null, best3_grade: null, best3_aps: null },
];

const order = (key, direction) =>
  [...rows].sort(comparator(key, direction)).map((r) => r.name);
const keyOf = (label) => COLUMNS.find((c) => c.label === label).key;

// Numbers compare numerically: text ordering would put 100 between 10 and 2.
assert.deepEqual(order('minutes', 'asc'), ['alpha', 'Beta', 'Gamma', 'Delta']);
assert.deepEqual(order('minutes', 'desc'), ['Delta', 'Gamma', 'Beta', 'alpha']);

// Negative progress scores sort below positive ones, and below each other correctly:
// text ordering would put -0.42 before -1.5.
assert.deepEqual(order('progress', 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order('progress', 'desc'), ['alpha', 'Beta', 'Gamma', 'Delta']);

// Text compares with localeCompare, so case does not split the order.
assert.deepEqual(order('name', 'asc'), ['alpha', 'Beta', 'Delta', 'Gamma']);

// The Average result and Best 3 A levels columns sort on their point scores. Sorting by
// grade text would give Beta, alpha, Gamma, the reverse of the first pair below.
assert.deepEqual(order(keyOf('Average result'), 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order(keyOf('Best 3 A levels'), 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order(keyOf('Average result'), 'desc'), ['alpha', 'Beta', 'Gamma', 'Delta']);

// Null sorts last whichever direction is asked for.
assert.equal(order('aps', 'asc').at(-1), 'Delta');
assert.equal(order('aps', 'desc').at(-1), 'Delta');

// Blank text fields share null's missing-last ordering, without hiding numeric zero.
for (const direction of ['asc', 'desc']) {
  const compare = comparator('website', direction);
  const websites = ['', 'https://b.example', null, 'https://a.example', undefined];
  const ordered = websites.map(website => ({ website })).sort(compare).map(r => r.website);
  assert.deepEqual(ordered, direction === 'asc'
    ? ['https://a.example', 'https://b.example', '', null, undefined]
    : ['https://b.example', 'https://a.example', '', null, undefined]);
  for (const missing of ['', null, undefined]) {
    assert.equal(compare({ website: '' }, { website: missing }), 0);
    assert.equal(compare({ website: missing }, { website: '' }), 0);
  }
  assert.equal(comparator('students', direction)({ students: 0 }, { students: '' }), -1);
}

// The same header toggles to descending; a different header starts ascending again.
assert.deepEqual(reset(), { key: 'minutes', direction: 'asc' });
assert.deepEqual(toggle('aps'), { key: 'aps', direction: 'asc' });
assert.deepEqual(toggle('aps'), { key: 'aps', direction: 'desc' });
assert.deepEqual(toggle('name'), { key: 'name', direction: 'asc' });
assert.deepEqual(sort, { key: 'name', direction: 'asc' });

// A fresh search resets to travel time ascending, from wherever the user left the sort.
toggle('aps');
toggle('aps');
assert.notDeepEqual(sort, DEFAULT_SORT);
assert.deepEqual(reset(), DEFAULT_SORT);
assert.deepEqual(sort, { key: 'minutes', direction: 'asc' });
assert.deepEqual(
  [...rows].sort(comparator(sort.key, sort.direction)).map((r) => r.minutes),
  [2, 10, 20, 100]);

const cell = (label, row) => COLUMNS.find((c) => c.label === label).cell(row);
assert.equal(cell('Students', { students: 167 }), '167');
assert.equal(cell('Progress', { progress: 0.18, progress_banding: 'Above average' }), '0.18 (Above average)');
assert.equal(cell('Progress', { progress: 0, progress_banding: null }), '0');
assert.equal(cell('Average result', { grade: 'A', aps: 50.44 }), 'A (50.44)');
assert.equal(cell('Completed programme', { retained_percent: 0 }), '0%');
assert.equal(cell('AAB or higher incl. 2 facilitating subjects', { aab_percent: 65.7 }), '65.7%');
assert.equal(cell('Best 3 A levels', { best3_grade: 'A', best3_aps: 50.58 }), 'A (50.58)');
for (const column of COLUMNS.slice(5, 11)) assert.equal(column.cell({}), '');
for (const direction of ['asc', 'desc']) {
  assert.equal(comparator('aps', direction)({ aps: null }, { aps: null }), 0);
}
console.log('sort.js ok');
