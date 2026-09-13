const text = (value) => (value == null ? '' : String(value));
const pair = (main, extra) =>
  main == null ? '' : extra == null ? String(main) : `${main} (${extra})`;
const percent = (value) => (value == null ? '' : `${value}%`);

export const COLUMNS = [
  { label: 'Name', key: 'name', value: (r) => r.name, cell: (r) => text(r.name) },
  { label: 'Type', key: 'type', value: (r) => r.type, cell: (r) => text(r.type) },
  { label: 'Postcode', key: 'postcode', value: (r) => r.postcode, cell: (r) => text(r.postcode) },
  { label: 'Sixth form', key: 'sixth_form', value: (r) => r.sixth_form, cell: (r) => text(r.sixth_form) },
  { label: 'Gender', key: 'gender', value: (r) => r.gender, cell: (r) => text(r.gender) },
  { label: 'Religious character', key: 'religious_character', value: (r) => r.religious_character, cell: (r) => text(r.religious_character) },
  { label: 'Minutes', key: 'minutes', value: (r) => r.minutes, cell: (r) => text(r.minutes) },
  { label: 'Students', key: 'students', value: (r) => r.students, cell: (r) => text(r.students) },
  { label: 'Progress', key: 'progress', value: (r) => r.progress, cell: (r) => pair(r.progress, r.progress_banding) },
  { label: 'Average result grade', key: 'aps', value: (r) => r.grade, cell: (r) => text(r.grade) },
  { label: 'Average result points', key: 'aps', value: (r) => r.aps, cell: (r) => text(r.aps) },
  { label: 'Completed programme', key: 'retained_percent', value: (r) => r.retained_percent, cell: (r) => percent(r.retained_percent) },
  { label: 'AAB or higher incl. 2 facilitating subjects', key: 'aab_percent', value: (r) => r.aab_percent, cell: (r) => percent(r.aab_percent) },
  { label: 'Best 3 A levels grade', key: 'best3_aps', value: (r) => r.best3_grade, cell: (r) => text(r.best3_grade) },
  { label: 'Best 3 A levels points', key: 'best3_aps', value: (r) => r.best3_aps, cell: (r) => text(r.best3_aps) },
  { label: 'Website', key: 'website', value: (r) => r.website, cell: () => '', link: true },
  { label: 'Latitude', key: 'lat', value: (r) => r.lat, cell: (r) => r.lat?.toFixed(5) ?? '' },
  { label: 'Longitude', key: 'lng', value: (r) => r.lng, cell: (r) => r.lng?.toFixed(5) ?? '' },
];

export function csvField(value) {
  const field = text(value);
  return /[",\r\n]/.test(field) ? `"${field.replaceAll('"', '""')}"` : field;
}

export function csvRows(rows) {
  const header = ['URN', ...COLUMNS.flatMap(c => c.key === 'progress'
    ? [c.label, 'Progress description'] : [c.label])];
  return [header, ...rows.map(r => [r.urn, ...COLUMNS.flatMap(c => c.key === 'progress'
    ? [c.value(r), r.progress_banding] : [c.value(r)])])]
    .map(fields => fields.map(csvField).join(','));
}

export function comparator(key, direction) {
  const sign = direction === 'desc' ? -1 : 1;
  return (a, b) => {
    const x = a[key];
    const y = b[key];
    if ((x == null || x === '') && (y == null || y === '')) return 0;
    if (x == null || x === '') return 1;
    if (y == null || y === '') return -1;
    if (typeof x === 'number' && typeof y === 'number') return sign * (x - y);
    return sign * String(x).localeCompare(String(y));
  };
}

export const DEFAULT_SORT = { column: COLUMNS.findIndex(c => c.key === 'minutes'), key: 'minutes', direction: 'asc' };

export let sort = { ...DEFAULT_SORT };

export function toggle(column) {
  const ascending = sort.column !== column || sort.direction === 'desc';
  sort = { column, key: COLUMNS[column].key, direction: ascending ? 'asc' : 'desc' };
  return sort;
}

export function reset() {
  sort = { ...DEFAULT_SORT };
  return sort;
}
