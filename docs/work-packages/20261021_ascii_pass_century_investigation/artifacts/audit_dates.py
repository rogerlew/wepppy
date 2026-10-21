"""Stream audit retained input dates against sequential model/PASS days."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
climate = []
with (root / 'runs/pw0.cli').open() as stream:
    for _ in range(15):
        next(stream)
    for line in stream:
        if line.strip():
            d, m, y = map(int, line.split()[:3])
            dt = datetime.date(y, m, d)
            climate.append((y, dt.timetuple().tm_yday, m, d))
expected = [(y, d) for y in range(1, 201)
            for d in range(1, 367 if y % 4 == 0 else 366)]
report = {'climate_rows': len(climate), 'legacy_model_days': len(expected),
          'first_counter_mismatch': next({'ordinal': i + 1, 'model': key,
                                         'climate': climate[i]}
                                        for i, key in enumerate(expected[:len(climate)])
                                        if key != climate[i][:2]), 'files': {}}
for path in sorted((root / 'output').glob('H*.pass.dat')) + [root / 'output/pass_pw0.txt']:
    count = 0
    mismatch = []
    guard_mismatches = []
    century_tails = []
    sources = 0
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for lineno, raw in enumerate(stream, 1):
            digest.update(raw)
            if raw.startswith((b'EVENT', b'SUBEVENT', b'NO EVENT')):
                kind = raw[:8].decode().strip()
                key = tuple(map(int, raw[8:].split()[:2]))
                if count >= len(expected) or key != expected[count]:
                    mismatch.append((lineno, count + 1, key))
                if key[0] in (99, 100, 101, 102, 103, 199, 200) and key[1] >= 365:
                    century_tails.append({'key': key, 'kind': kind,
                                          'climate': climate[count] if count < len(climate) else None})
                count += 1
            elif raw.startswith(b'SOURCES3'):
                sources += 1
                key = tuple(map(int, raw.split()[1:3]))
                idx = count - 1
                if idx < len(climate):
                    # wshred passes year from STMGET and sdate from the model loop.
                    requested = (climate[idx][0], expected[idx][1])
                    if key != requested:
                        guard_mismatches.append({'line': lineno, 'ordinal': count,
                                                 'master': key, 'requested': requested,
                                                 'climate': climate[idx]})
    report['files'][path.name] = {'sha256': digest.hexdigest(), 'days': count,
                                'legacy_key_mismatches': mismatch[:10],
                                'sources_records': sources,
                                'first_guard_mismatch': guard_mismatches[:1],
                                'century_tails': century_tails if path.name == 'pass_pw0.txt' else []}
print(json.dumps(report, indent=2))
