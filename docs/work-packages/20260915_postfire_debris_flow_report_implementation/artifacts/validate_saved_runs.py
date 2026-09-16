"""Compare read-only report projections with genuine saved parquet, without jobs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import pyarrow.parquet as pq

from wepppy.nodb.mods.postfire_debris_flow import production, report


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runid')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not args.runid or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.runid):
        raise ValueError('Invalid run ID')
    wd = Path('/wc1/runs') / args.runid[:2] / args.runid
    accepted = production.state_at(wd)['last_successful_run']
    assert accepted is not None
    paths = list(wd.glob('*.nodb')) + [wd / 'redisprep.dump']
    paths += [wd / relative for relative in accepted['artifacts']]
    paths += [p for p in (wd / 'postfire_debris_flow').iterdir() if p.is_file()]
    protected = {p: checksum(p) for p in paths if p.is_file()}
    started = time.monotonic()
    assessment = report.open_assessment(wd, 'config', accepted['id'])
    opened = time.monotonic() - started
    queries = []
    for duration in (15, 30, 60):
        query = dict(report.DEFAULT_QUERY, duration_minutes=duration)
        started = time.monotonic()
        payload = report.view(assessment, query)
        elapsed = time.monotonic() - started
        directory = wd / 'postfire_debris_flow' / 'attempts' / accepted['id'] / 'results'
        event_rows = pq.read_table(directory / 'events.parquet').to_pylist()
        wanted = [row for row in event_rows if row['duration_minutes'] == duration]
        wanted.sort(key=lambda row: row['row_ordinal'])
        assert payload['events']['rows'] == wanted[:100]
        assert payload['events']['total'] == len(wanted)
        assert payload['events']['unfiltered_total'] == len(wanted)
        assert payload['design'] == pq.read_table(directory / 'design.parquet').to_pylist()
        assert payload['inverse'] == [row for row in pq.read_table(directory / 'inverse.parquet').to_pylist()
                                      if row['target_probability'] == .5]
        assert payload['summary']['model'] == accepted.get('model', 'M1')
        for name in production.result_files(accepted):
            with report.open_attachment(assessment, name) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            assert actual == checksum(directory / name)
        queries.append(dict(duration=duration, query_seconds=elapsed,
                            total_events=len(wanted), page_rows=len(payload['events']['rows'])))
    assessment.recheck()
    assert production.state_at(wd)['last_successful_run'] == accepted
    assert {p: checksum(p) for p in protected} == protected
    result = dict(runid=args.runid, model=payload['summary']['model'], attempt_id=accepted['id'],
                  assessment_id=payload['summary']['assessment_id'], current=payload['summary']['current'],
                  frequency_source=payload['summary']['frequency_source'],
                  open_seconds=opened, queries=queries, protected_files=len(protected), unchanged=True,
                  manifest_sha256=checksum(directory / 'manifest.json'),
                  scientific_table_sha256={name: checksum(directory / f'{name}.parquet')
                                           for name in ('events', 'design', 'inverse')})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
