"""Summarize verified factorial effects and retained failed-runtime evidence."""
from pathlib import Path
import hashlib
import json
import statistics

HERE = Path(__file__).resolve().parent
ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031/runtime-bridge-r3')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    return dict(count=len(values), median=statistics.median(values) if values else None,
                minimum=min(values) if values else None, maximum=max(values) if values else None)


def main():
    path = HERE / 'runtime-bridge-r3-verification.json'; verified = json.loads(path.read_text())
    rows = verified['rows']; assert len(rows) == 128
    cells = {(tuple(row['case'].values()), row['lane']): row for row in rows}
    assert len(cells) == 128
    contrasts = []
    for position, factor in enumerate(('hourly', 'PMET', 'snow')):
        for lane in sorted({r['lane'] for r in rows if r['lane'][position] == '0'}):
            on = lane[:position] + '1' + lane[position + 1:]
            for group in ('residual', 'passing_control'):
                pairs = [(off, cells[(key, on)]) for (key, code), off in cells.items() if code == lane and off['group'] == group]
                valid = [(off, yes) for off, yes in pairs if off['physical_pass'] and yes['physical_pass']]
                contrasts.append(dict(factor=factor, off=lane, on=on, group=group, pairs=len(pairs), physical_pairs=len(valid),
                                      on_recovers=sum(not off['within'] and yes['within'] for off, yes in valid),
                                      on_loses=sum(off['within'] and not yes['within'] for off, yes in valid),
                                      sediment_on_minus_off_kg_yr=stats([yes['export_kg_yr'] - off['export_kg_yr'] for off, yes in valid]),
                                      surface_out_on_minus_off_m3_yr={role: stats([yes['water_ofes'][i]['surface_out_m3_yr'] - off['water_ofes'][i]['surface_out_m3_yr'] for off, yes in valid]) for i, role in enumerate(('road', 'fill', 'buffer'))}))
    failures = []
    for row in rows:
        if row['physical_pass']:
            continue
        folder = ROOT / row['lane'] / '-'.join(row['case'].values())
        stdout = folder / 'runs/stdout'
        failures.append(dict(case=row['case'], lane=row['lane'], group=row['group'], record_sha256=row['record_sha256'],
                             stdout_sha256=sha(stdout), guard_lines=[line.strip() for line in stdout.read_text().splitlines() if 'HOURLY_WATER_UNMET' in line]))
    assert len(failures) == 5 and all(f['guard_lines'] for f in failures)
    result = dict(verified_cells=128, physical_pass=123, rejected_native_failures=5,
                  verification_sha256=sha(path), contrasts=contrasts, failures=failures,
                  residual_daily_PMET_misses=[r for r in rows if r['lane'] == '011' and r['group'] == 'residual' and not r['within']],
                  limitation='Selected11residual and5control inputs; diagnostic paired effects, not global configuration acceptance or complete water-budget closure.')
    (HERE / 'runtime-bridge-r3-effects.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Verified24grouped factor contrasts; retained5guard failures', flush=True)


if __name__ == '__main__':
    main()
