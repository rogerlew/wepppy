"""Read-only national count bound plus real-writer witnesses; no production edits."""
import argparse
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import sqlite3

from wepppy.soils.ssurgo import ssurgo
from wepppy.wepp.soils import horizon_boundary

DEFAULTS = dict(sandtotal_r=66.8, claytotal_r=7.0, om_r=7.0,
                cec7_r=11.3, sandvf_r=10.0, smr=55.5)
# Necessary conditions only: missing hydraulic fields may be estimated later.
# Omitting restrictive-layer truncation makes this an upper bound, not a census
# of successfully generated profiles. Defaults never replace numeric zeros.
ELIGIBLE = """coalesce(desgnmaster,'O') NOT GLOB 'O*'
AND hzdepb_r IS NOT NULL AND coalesce(sandtotal_r,66.8)>0
AND coalesce(claytotal_r,7.0)>0 AND coalesce(cec7_r,11.3)>0"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    before = args.database.stat()
    conn = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    raw_counts = dict(conn.execute('SELECT cokey,count(*) FROM chorizon GROUP BY cokey'))
    eligible_counts = dict(conn.execute(
        f'SELECT cokey,count(*) FROM chorizon WHERE {ELIGIBLE} GROUP BY cokey'))
    maximum = max(eligible_counts.values())
    winners = [key for key, count in eligible_counts.items() if count == maximum]
    marks = ','.join('?' for _ in winners)
    mukeys = {row[0] for row in conn.execute(
        f'SELECT mukey FROM component WHERE cokey IN ({marks})', winners)}
    view = ssurgo.SurgoCollectionWorkerViewFactory(conn=conn).build(mukeys, 'National SSURGO 2026-10-01; read-only capacity inventory')
    for mukey, components in view._components.items():
        aggregate = dict(conn.execute('SELECT * FROM muaggatt WHERE mukey=?', (mukey,)).fetchone())
        for component in components:
            # The SDA component query joins these map-unit attributes.
            for key in ('muname', 'wtdepannmin', 'flodfreqdcd', 'aws025wta', 'aws0150wta', 'hydgrpdcd', 'drclassdcd'):
                component[key] = aggregate[key]

    # Exercise the canonical boundary implementation with only the capacity guard
    # lifted in this disposable process. All source files remain unchanged.
    source = inspect.getsource(horizon_boundary)
    assert source.count('nsl > 10') == 1 and source.count('nsl >= 10') == 1
    namespace = {}
    exec(compile(source.replace('nsl > 10', 'nsl > 1000000').replace('nsl >= 10', 'nsl >= 1000000'), '<inventory-only-boundary>', 'exec'), namespace)
    normalize = namespace['ensure_200mm_boundary']
    original = ssurgo.ensure_200mm_boundary
    witnesses = []
    try:
        ssurgo.ensure_200mm_boundary = lambda text: text
        for mukey in sorted(mukeys):
            soil = ssurgo.WeppSoil(view, mukey, horizon_defaults=DEFAULTS)
            assert soil.valid()
            raw = soil.build_file_contents()
            normalized = normalize(raw)
            records = [line for line in normalized.splitlines() if line.strip() and not line.lstrip().startswith('#')]
            # These witness names/textures are quoted and may contain spaces.
            header = list(horizon_boundary._TOKEN.finditer(records[3]))
            count = int(header[2].group())
            depths = [float(line.split()[0]) for line in records[4:4+count]]
            assert count == soil.num_layers + 1
            assert depths.count(200.0) == 1
            assert normalize(normalized) == normalized
            (args.output/f'{mukey}-raw.sol').write_text(raw)
            (args.output/f'{mukey}-normalized.sol').write_text(normalized)
            location = dict(conn.execute('SELECT m.muname,l.areasymbol,l.areaname FROM mapunit m JOIN legend l USING(lkey) WHERE m.mukey=?', (mukey,)).fetchone())
            witnesses.append(dict(mukey=mukey, cokey=soil.majorComponent.cokey,
                component=soil.majorComponent.compname, percent=soil.majorComponent.comppct_r,
                raw_horizons=len(soil.horizons), valid_mask=list(map(bool, soil.horizons_mask)),
                emitted=soil.num_layers, normalized=count, depths_mm=depths,
                restrictive_index=soil.res_lyr_i, location=location,
                rejected=[dict(chkey=h.chkey, name=h.hzname, clay=h.claytotal_r) for h,m in zip(soil.horizons,soil.horizons_mask) if not m]))
    finally:
        ssurgo.ensure_200mm_boundary = original
    after = args.database.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    report = dict(database=str(args.database.resolve()), bytes=before.st_size,
        mtime_ns=before.st_mtime_ns, source_unchanged_size_mtime=True,
        writer_source=str(Path(ssurgo.__file__).resolve()),
        writer_sha256=hashlib.sha256(Path(ssurgo.__file__).read_bytes()).hexdigest(),
        components_total=conn.execute('SELECT count(*) FROM component').fetchone()[0],
        components_with_horizons=len(raw_counts), horizons=sum(raw_counts.values()),
        raw_histogram=dict(sorted(Counter(raw_counts.values()).items())),
        eligible_upper_bound_histogram=dict(sorted(Counter(eligible_counts.values()).items())),
        eligible_predicate=ELIGIBLE, maximum_raw=max(raw_counts.values()),
        maximum_eligible=maximum, maximum_generated_proven=max(w['normalized'] for w in witnesses),
        all_source_horizons_plus_split_capacity=max(raw_counts.values())+1,
        witnesses=witnesses)
    assert report['maximum_generated_proven'] == maximum+1
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='witnesses'},indent=2))
    print('Writer witnesses:',len(witnesses))


if __name__ == '__main__':
    main()
