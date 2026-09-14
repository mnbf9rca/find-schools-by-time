"""Four little-endian uint16 planes indexed by the URN-sorted schools.json list.

encode takes four school-length sequences: transit, walking, cycling, driving.
Inputs are nonnegative seconds or 65535. Seconds round half up before the cap;
public transport stores the smaller of normalized transit and walking.
The sentinel 65535 means over cap, outside the pruning radius, or not computed.
Callers must verify the manifest's school index hash before decoding.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

MODES = ('public_transport', 'walking', 'cycling', 'driving')
SCHOOL_COUNT = len(json.loads((Path(__file__).resolve().parents[1] / 'schools.json').read_text()))
SENTINEL = 65535
CAP = 5400


def school_index_hash(urns):
    return hashlib.sha256('\n'.join(sorted(urns)).encode('utf-8')).hexdigest()


def encode(values):
    if len(values) != len(MODES) or any(len(plane) != SCHOOL_COUNT for plane in values):
        raise ValueError('Expected four planes matching the school list length')
    planes = []
    for plane in values:
        normalized = []
        for value in plane:
            if not math.isfinite(value) or value < 0:
                raise ValueError('Seconds must be finite and nonnegative')
            whole = math.floor(value)
            seconds = whole + (value - whole >= 0.5)
            normalized.append(seconds if seconds <= CAP else SENTINEL)
        planes.append(normalized)
    planes[0] = [min(transit, walk) for transit, walk in zip(planes[0], planes[1])]
    return struct.pack(f'<{len(MODES) * SCHOOL_COUNT}H', *(value for plane in planes for value in plane))


def decode(buffer, mode_index, school_index):
    if memoryview(buffer).nbytes != len(MODES) * 2 * SCHOOL_COUNT:
        raise ValueError('Record length does not match the school list')
    if (type(mode_index) is not int or not 0 <= mode_index < len(MODES)
            or type(school_index) is not int or not 0 <= school_index < SCHOOL_COUNT):
        raise ValueError('Mode or school index out of range')
    value, = struct.unpack_from('<H', buffer, 2 * (mode_index * SCHOOL_COUNT + school_index))
    if CAP < value < SENTINEL:
        raise ValueError('Corrupt record value')
    return value
