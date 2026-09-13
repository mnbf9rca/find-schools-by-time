import assert from 'node:assert/strict';
import { COLUMNS, comparator, csvField, csvRows, DEFAULT_SORT, reset, sort, toggle } from './sort.js';

const rows = [
  { name: 'Beta', minutes: 10, progress: -0.42, grade: 'A', aps: 45.0, best3_grade: 'A', best3_aps: 46.0 },
  { name: 'alpha', minutes: 2, progress: 0.18, grade: 'A+', aps: 50.44, best3_grade: 'A+', best3_aps: 50.58 },
  { name: 'Gamma', minutes: 20, progress: -1.5, grade: 'E', aps: 9.5, best3_grade: 'E', best3_aps: 9.0 },
  { name: 'Delta', minutes: 100, progress: null, grade: null, aps: null, best3_grade: null, best3_aps: null },
];

const order = (key, direction) =>
  [...rows].sort(comparator(key, direction)).map((r) => r.name);
const indexOf = (label) => {
  const index = COLUMNS.findIndex((c) => c.label === label);
  assert.notEqual(index, -1, `Missing column: ${label}`);
  return index;
};
const keyOf = (label) => COLUMNS[indexOf(label)].key;

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
assert.deepEqual(order(keyOf('Average result grade'), 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order(keyOf('Best 3 A levels grade'), 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order(keyOf('Average result grade'), 'desc'), ['alpha', 'Beta', 'Gamma', 'Delta']);

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

// Header identity is its position: adjacent grade/points headers share a key.
const minutesColumn = indexOf('Minutes');
const nameColumn = indexOf('Name');
assert.deepEqual(reset(), { column: minutesColumn, key: 'minutes', direction: 'asc' });
for (const [grade, points, key] of [
  ['Average result grade', 'Average result points', 'aps'],
  ['Best 3 A levels grade', 'Best 3 A levels points', 'best3_aps'],
]) {
  const column = indexOf(grade);
  const neighbour = indexOf(points);
  assert.equal(neighbour, column + 1);
  assert.deepEqual(toggle(column), { column, key, direction: 'asc' });
  assert.deepEqual(toggle(neighbour), { column: neighbour, key, direction: 'asc' });
  assert.deepEqual(toggle(neighbour), { column: neighbour, key, direction: 'desc' });
  assert.deepEqual(toggle(column), { column, key, direction: 'asc' });
  assert.deepEqual(toggle(column), { column, key, direction: 'desc' });
}
assert.deepEqual(toggle(nameColumn), { column: nameColumn, key: 'name', direction: 'asc' });
assert.deepEqual(sort, { column: nameColumn, key: 'name', direction: 'asc' });

// A fresh search resets to travel time ascending, from wherever the user left the sort.
assert.notDeepEqual(sort, DEFAULT_SORT);
assert.deepEqual(reset(), DEFAULT_SORT);
assert.deepEqual(sort, { column: minutesColumn, key: 'minutes', direction: 'asc' });
assert.deepEqual(
  [...rows].sort(comparator(sort.key, sort.direction)).map((r) => r.minutes),
  [2, 10, 20, 100]);

const cell = (label, row) => COLUMNS.find((c) => c.label === label).cell(row);
assert.equal(indexOf('Gender'), indexOf('Sixth form') + 1);
assert.equal(keyOf('Gender'), 'gender');
assert.equal(cell('Gender', { gender: 'Girls' }), 'Girls');
assert.equal(indexOf('Religious character'), indexOf('Gender') + 1);
assert.equal(keyOf('Religious character'), 'religious_character');
assert.equal(cell('Religious character', { religious_character: 'Church of England' }), 'Church of England');
assert.equal(cell('Students', { students: 167 }), '167');
assert.equal(cell('Progress', { progress: 0.18, progress_banding: 'Above average' }), '0.18 (Above average)');
assert.equal(cell('Progress', { progress: 0, progress_banding: null }), '0');
for (const [label, key, expected] of [
  ['Average result grade', 'aps', 'A'],
  ['Average result points', 'aps', '50.44'],
  ['Best 3 A levels grade', 'best3_aps', 'B'],
  ['Best 3 A levels points', 'best3_aps', '40.58'],
]) {
  assert.equal(keyOf(label), key);
  assert.equal(cell(label, { grade: 'A', aps: 50.44, best3_grade: 'B', best3_aps: 40.58 }), expected);
}
assert.equal(cell('Completed programme', { retained_percent: 0 }), '0%');
assert.equal(cell('AAB or higher incl. 2 facilitating subjects', { aab_percent: 65.7 }), '65.7%');
for (const column of COLUMNS) assert.equal(column.cell({}), '');
for (const direction of ['asc', 'desc']) {
  assert.equal(comparator('aps', direction)({ aps: null }, { aps: null }), 0);
}
// CSV quoting must also handle a standalone CR, without changing raw numbers.
for (const [value, expected] of [
  ['plain', 'plain'], ['School, London', '"School, London"'],
  ['School "A"', '"School ""A"""'], ['line\nfeed', '"line\nfeed"'],
  ['carriage\rreturn', '"carriage\rreturn"'], [null, ''], [undefined, ''],
  [0, '0'], [65.7, '65.7'], ['École', 'École'],
]) assert.equal(csvField(value), expected);

const exportRow = {
  urn: 123456, name: 'École', type: 'Academy', postcode: 'SW1A 1AA',
  sixth_form: 'Has a sixth form', gender: 'Girls', religious_character: 'Church of England', minutes: 42, students: null,
  progress: 0, progress_banding: 'Average', grade: 'A', aps: 50.44,
  retained_percent: 90.1, aab_percent: 65.7, best3_grade: 'B', best3_aps: 40.58,
  website: 'https://school.example',
};
const headers = ['URN', ...COLUMNS.flatMap(c => c.key === 'progress'
  ? [c.label, 'Progress description'] : [c.label])];
const exported = csvRows([exportRow, { ...exportRow, urn: 654321, name: 'Second' }]);
assert.equal(exported.length, 3);
assert.deepEqual(exported[0].split(','), headers);
const fields = exported[1].split(',');
assert.equal(fields.length, headers.length);
assert.equal(fields[headers.indexOf('Students')], '');
assert.deepEqual(Object.fromEntries(headers.map((h, i) => [h, fields[i]])), {
  URN: '123456', Name: 'École', Type: 'Academy', Postcode: 'SW1A 1AA',
  'Sixth form': 'Has a sixth form', Gender: 'Girls', 'Religious character': 'Church of England', Minutes: '42', Students: '',
  Progress: '0', 'Progress description': 'Average',
  'Average result grade': 'A', 'Average result points': '50.44',
  'Completed programme': '90.1', 'AAB or higher incl. 2 facilitating subjects': '65.7',
  'Best 3 A levels grade': 'B', 'Best 3 A levels points': '40.58',
  Website: 'https://school.example',
});
assert.equal(exported[2].split(',')[0], '654321');
assert.deepEqual(csvRows([]), [exported[0]]);
assert.equal(csvRows([{}])[1], ','.repeat(headers.length - 1));
assert.equal(csvRows([{ ...exportRow, name: 'School, "A"' }])[1].split(',Academy')[0],
  '123456,"School, ""A"""');
for (const column of COLUMNS) {
  const field = column.label === 'Average result grade' ? 'grade'
    : column.label === 'Best 3 A levels grade' ? 'best3_grade' : column.key;
  assert.equal(column.value(exportRow), exportRow[field]);
}
console.log('sort.js: sorting, split columns and CSV checks passed');
