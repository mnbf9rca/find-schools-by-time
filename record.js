import schools from './schools.json' with { type: 'json' };

const schoolCount = schools.length;

// Planes: public_transport, walking, cycling, driving. Verify the manifest hash first.
// 65535 means over cap, outside the pruning radius, or not computed.
export function decode(buffer, modeIndex, schoolIndex) {
  const view = ArrayBuffer.isView(buffer)
    ? new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength)
    : new DataView(buffer);
  if (view.byteLength !== 4 * 2 * schoolCount) {
    throw new RangeError('Record length does not match the school list');
  }
  if (!Number.isInteger(modeIndex) || modeIndex < 0 || modeIndex >= 4
      || !Number.isInteger(schoolIndex) || schoolIndex < 0 || schoolIndex >= schoolCount) {
    throw new RangeError('Mode or school index out of range');
  }
  const value = view.getUint16(2 * (modeIndex * schoolCount + schoolIndex), true);
  if (value > 5400 && value < 65535) throw new RangeError('Corrupt record value');
  return value;
}
