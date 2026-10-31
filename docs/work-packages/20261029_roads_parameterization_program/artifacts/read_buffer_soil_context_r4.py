"""Read published SOIL histories for frozen observer seeds; no native runs.

Post hoc descriptive context, not a causal test or seed-selection amendment.
Writes only a new output root and preserves every source artifact.
"""
from pathlib import Path
import argparse
import calendar
import hashlib
import importlib
import inspect
import json

import pyarrow.parquet as pq
from wepppy.wepp.interchange._rust_interchange import (
    call_wepppyo3_interchange, require_wepppyo3_interchange, version_args,
)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    seeds = json.loads(args.seeds.read_text())
    reader = require_wepppyo3_interchange(
        'Roads published soil context', 'hillslope_soil_files_to_parquet')
    native_reader = importlib.import_module(
        reader.hillslope_soil_files_to_parquet.__module__)
    wrapper = Path(inspect.getfile(call_wepppyo3_interchange)).resolve()
    declaration = dict(scope=__doc__, seeds_sha256=sha(args.seeds),
                       script_sha256=sha(__file__),
                       reader=str(Path(reader.__file__).resolve()),
                       reader_sha256=sha(reader.__file__),
                       native_reader=str(Path(native_reader.__file__).resolve()),
                       native_reader_sha256=sha(native_reader.__file__),
                       wrapper=str(wrapper), wrapper_sha256=sha(wrapper),
                       interchange_version=list(version_args()),
                       native_runs=0, pairs=len(seeds['seeds']))
    save(args.output / 'declaration.json', declaration)
    major, minor = version_args()
    results = []
    fields = ('Poros', 'Keff', 'Suct', 'FC', 'WP', 'Rough',
              'Ki', 'Kr', 'Tauc', 'Saturation')
    for seed in seeds['seeds']:
        pair = dict(stratum=seed['stratum'], case=seed['event']['case_id'], lanes={})
        expected = {(year, day, ofe)
                    for year in range(seed['calendar_first_year'], seed['calendar_last_year'] + 1)
                    for day in range(1, 366 + calendar.isleap(year))
                    for ofe in (1, 2, 3)}
        for lane, source in seed['input_records'].items():
            record = Path(source['path'])
            assert sha(record) == source['sha256']
            data = json.loads(record.read_text())
            raw = record.parent / 'output/H1.soil.dat'
            assert sha(raw) == data['outputs'][raw.name]
            destination = args.output / f"{seed['stratum']}-{lane}.parquet"
            call_wepppyo3_interchange(
                'Roads published soil context', 'hillslope_soil_files_to_parquet',
                [str(raw)], str(destination), major, minor,
                cli_calendar_path=None, start_year=seed['calendar_first_year'],
                compression='snappy',
            )
            table = pq.read_table(destination)
            rows = table.to_pylist()
            keys = [(r['year'], r['julian'], r['OFE']) for r in rows]
            assert len(set(keys)) == len(keys) and set(keys) == expected
            ofes = []
            for ofe in (1, 2, 3):
                series = sorted((r for r in rows if r['OFE'] == ofe),
                                key=lambda r: (r['year'], r['julian']))
                target = next(r for r in series if
                              (r['year'], r['julian']) ==
                              (seed['event']['year'], seed['event']['julian']))
                observed = [r['Rough'] for r in series if r['Rough'] is not None]
                changed = next((r for r in series if
                                r['Rough'] != series[0]['Rough']), None)
                ofes.append(dict(
                    OFE=ofe, days=len(series),
                    first_day={k: series[0][k] for k in fields},
                    target_day={k: target[k] for k in fields},
                    roughness_mm=dict(first=series[0]['Rough'], minimum=min(observed),
                                      maximum=max(observed), missing=len(series)-len(observed),
                                      first_changed=None if changed is None else {
                                          k: changed[k] for k in ('year', 'julian', 'Rough')}),
                ))
            assert sha(record) == source['sha256'] and sha(raw) == data['outputs'][raw.name]
            pair['lanes'][lane] = dict(record=source, raw_sha256=sha(raw),
                                      parquet_sha256=sha(destination), rows=len(rows), ofes=ofes)
        results.append(pair)
    assert sha(args.seeds) == declaration['seeds_sha256']
    assert sha(reader.__file__) == declaration['reader_sha256']
    assert sha(native_reader.__file__) == declaration['native_reader_sha256']
    assert sha(wrapper) == declaration['wrapper_sha256']
    save(args.output / 'results.json', dict(declaration_sha256=sha(args.output/'declaration.json'),
                                           pairs=results, native_runs=0,
                                           source_artifacts_unchanged=True))
    for pair in results:
        print(pair['stratum'], {lane: data['ofes'][2]['roughness_mm']
                                for lane, data in pair['lanes'].items()}, flush=True)


if __name__ == '__main__':
    main()
