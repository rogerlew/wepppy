"""Explicitly curate scientific inputs; never copy controller/account metadata."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil

DATA = Path(__file__).parent / 'data'
SHARED = ('wepp_ui.txt', 'snow.txt', 'pmetpara.txt', 'gwcoeff.txt', 'chan.inp', 'chntyp.txt', 'tc.txt')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def climate_dates(path):
    rows = [line.split() for line in Path(path).read_text().splitlines()[15:] if line.strip()]
    if not rows or any(len(row) != 13 or not all(math.isfinite(float(v)) for v in row) for row in rows):
        raise ValueError('Climate must contain finite, complete daily records')
    dates = [dt.date(int(row[2]), int(row[1]), int(row[0])) for row in rows]
    expected = [dates[0] + dt.timedelta(days=i) for i in range((dates[-1]-dates[0]).days+1)]
    if dates != expected or (dates[0].month, dates[0].day) != (1, 1) or (dates[-1].month, dates[-1].day) != (12, 31):
        raise ValueError('Climate must contain unique consecutive complete calendar years')
    return dates


def extract(source: Path):
    source = source.resolve(strict=True)
    manifest = source / 'wepp/roads/segments/roads.segment.pass.manifest.json'
    records = sorted((r for r in json.loads(manifest.read_text()) if r.get('status') == 'completed'
                      and r['segment_length_m'] > 0), key=lambda r: (r['segment_length_m'], r['segment_id']))
    if not records:
        raise ValueError('Source has no completed positive-length Roads profiles')
    chosen = dict(zip(('short', 'median', 'long'), (records[0], records[(len(records)-1)//2], records[-1])))
    keys = ('segment_id', 'segment_length_m', 'slope_pct_clamped', 'road_width_m', 'target_hillslope_wepp_id')
    geometry = {name: {key: row[key] for key in keys} for name, row in chosen.items()}
    climate = source / 'wepp/runs' / f"p{chosen['median']['target_hillslope_wepp_id']}.cli"
    dates = climate_dates(climate)
    sources = {str(manifest.relative_to(source)): digest(manifest), str(climate.relative_to(source)): digest(climate)}
    (DATA / "shared").mkdir(parents=True, exist_ok=True)
    shutil.copy2(climate, DATA/'site.cli')
    for name in SHARED:
        path = source/'wepp/runs'/name
        sources[str(path.relative_to(source))] = digest(path)
        shutil.copy2(path, DATA/'shared'/name)
    # Read only the selected binary field, never serialize the controller state.
    binary = json.loads((source/'wepp.nodb').read_text())['py/state']['_wepp_bin']
    result = {'source_run': source.name, 'source_artifact_sha256': sources,
              'selection': 'completed positive-length segments; sort by length then segment_id; shortest/lower median/longest',
              'completed_source_profiles': len(records), 'geometry': geometry,
              'source_lengths_m': [r['segment_length_m'] for r in records],
              'climate_first_day': str(dates[0]), 'climate_last_day': str(dates[-1]),
              'daily_records': len(dates), 'simulation_years': len({d.year for d in dates}),
              'header_years_note': 'Original header advertises 100; actual scientific record has 16 years.',
              'binary': binary, 'fixture_sha256': {str(p.relative_to(DATA)): digest(p) for p in [DATA/'site.cli', *(DATA/'shared'/n for n in SHARED)]}}
    (DATA/'site.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.source), indent=2))
