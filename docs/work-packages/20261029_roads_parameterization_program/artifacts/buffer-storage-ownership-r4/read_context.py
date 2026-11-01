"""Retain reviewed hydraulic support beside target storage without mixing epochs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--response-manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    d = json.loads(a.response.read_text())
    before = sha(a.response)
    manifest_before = sha(a.response_manifest)
    if manifest_before != 'b81e3bae199037e737e9aab730408f25130774b124024d3dae12a62db40b09fe':
        raise ValueError('Accepted response manifest drift')
    manifest = json.loads(a.response_manifest.read_text())
    # Summary must occur in the already accepted publication manifest.
    if manifest['files']['summary.json'] != before:
        raise ValueError('Response summary not bound by publication manifest')
    rows = []
    for pair in d['rows']:
        for mode, roles in enumerate(pair['target_day_roles_off_on']):
            if [r['ofe'] for r in roles] != [1, 2, 3]:
                raise ValueError('Missing or duplicate role support')
            upstream, buffer = roles[1:]
            handoff = buffer['receiving_duration_handoff']
            row = dict(case=pair['case'], lane=pair['lane'], mode=mode,
                day=buffer['day'], local_buffer_length_m=buffer['geometry_native_m']['local_length'],
                buffer_width_m=buffer['geometry_native_m']['width'],
                final_upstream_effective_length_m=upstream['effective_plane_length_m'],
                final_upstream_surface_boundary_m3=upstream['surface_boundary_m3'],
                final_buffer_effective_length_m=buffer['effective_plane_length_m'],
                final_buffer_surface_boundary_m3=buffer['surface_boundary_m3'],
                final_buffer_duration_s=buffer['effective_duration_s'],
                final_buffer_peak_m_s=buffer['peak_m_s'],
                receiving_duration_incoming_sediment_kg_m=None if handoff is None else handoff['incoming_event_using_current_duration_kg_m'],
                buffer_outgoing_sediment_kg_m=buffer['published_boundary_sediment_kg_m'])
            row.update({'hourly_local_'+k+'_m': v for k,v in buffer['hourly_local_depth_sums_m'].items()})
            row.update({'hourly_upstream_'+k+'_m': v for k,v in buffer['hourly_upstream_depth_sums_m'].items()})
            rows.append(row)
    expected = {(f'B{i}', lane, mode) for i in range(1, 10) for lane in ('legacy', 'modern') for mode in (0, 1)}
    if len(rows) != 36 or {(r['case'],r['lane'],r['mode']) for r in rows} != expected:
        raise ValueError('Incomplete/duplicate case-mode support')
    with (a.out/'hydraulic-context.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader(); w.writerows(rows)
    if sha(a.response) != before or sha(a.response_manifest) != manifest_before:
        raise ValueError('Input changed')
    (a.out/'receipt.json').write_text(json.dumps(dict(passed=True, rows=len(rows),
        source_sha256=before, manifest_sha256=sha(a.response_manifest), reader_sha256=sha(Path(__file__)),
        table_sha256=sha(a.out/'hydraulic-context.csv'),
        support='Final IRS surface boundaries/duration and full-day hourly sums are distinct from GRNA entry storage. Upstream hourly depths use upstream local support; no area conversion or complete water closure inferred.'), indent=2)+'\n')


if __name__ == '__main__':
    main()
