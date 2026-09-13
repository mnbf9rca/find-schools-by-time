const text = (value) => (value == null ? '' : String(value));
const pair = (main, extra) =>
  main == null ? '' : extra == null ? String(main) : `${main} (${extra})`;
const percent = (value) => (value == null ? '' : `${value}%`);

export const COLUMNS = [
  { label: 'Name', key: 'name', cell: (r) => text(r.name) },
  { label: 'Type', key: 'type', cell: (r) => text(r.type) },
  { label: 'Postcode', key: 'postcode', cell: (r) => text(r.postcode) },
  { label: 'Sixth form', key: 'sixth_form', cell: (r) => text(r.sixth_form) },
  { label: 'Minutes', key: 'minutes', cell: (r) => text(r.minutes) },
  { label: 'Students', key: 'students', cell: (r) => text(r.students) },
  { label: 'Progress', key: 'progress', cell: (r) => pair(r.progress, r.progress_banding) },
  { label: 'Average result', key: 'aps', cell: (r) => pair(r.grade, r.aps) },
  { label: 'Completed programme', key: 'retained_percent', cell: (r) => percent(r.retained_percent) },
  { label: 'AAB or higher incl. 2 facilitating subjects', key: 'aab_percent', cell: (r) => percent(r.aab_percent) },
  { label: 'Best 3 A levels', key: 'best3_aps', cell: (r) => pair(r.best3_grade, r.best3_aps) },
  { label: 'Website', key: 'website', cell: () => '', link: true },
];

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

export const DEFAULT_SORT = { key: 'minutes', direction: 'asc' };

export let sort = { ...DEFAULT_SORT };

export function toggle(key) {
  const ascending = sort.key !== key || sort.direction === 'desc';
  sort = { key, direction: ascending ? 'asc' : 'desc' };
  return sort;
}

export function reset() {
  sort = { ...DEFAULT_SORT };
  return sort;
}
