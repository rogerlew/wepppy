"""Read frozen development outputs; distinguish boundary export from net OFE exchange.

No model runs, fitting, default changes, or withheld-outcome inspection. Net
boundary differences are bookkeeping attribution, not tagged particle origins.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import statistics
import tempfile

import pyarrow.compute as pc
import pyarrow.parquet as pq
from wepppy.wepp.interchange._rust_interchange import call_wepppyo3_interchange, version_args

HERE = Path(__file__).resolve().parent
MATRIX = Path('/workdir/wepppy/out/roads-channel-accounting-20261030/U10-matrix840')
REFERENCE = Path('/wc1/runs/ro/roads-soil-benchmark-20261029/validation-v4')
TEXTURES = {'1718465': 'sand', '2711184': 'loam', '2711250': 'silt',
            '1718510': 'clay', '1856573': 'loam', '53949': 'loam', '1718494': 'loam'}
SHA = '819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boundaries(folder, record):
    path = folder / 'output/H1.element.dat'
    assert digest(path) == record['outputs'][path.name], path
    manifest = json.loads(Path('/wc1/runs/ro/roads-parameterization-program-20261030/rebaseline-v1/inputs/manifest.json').read_text())
    year = int(manifest['climates'][record['case']['climate']]['first'].split('-')[0])
    with tempfile.TemporaryDirectory(prefix='roads-role-readback-') as scratch:
        target = Path(scratch) / 'element.parquet'
        major, minor = version_args()
        call_wepppyo3_interchange('role boundary assessment', 'hillslope_element_files_to_parquet',
                                 [str(path)], str(target), major, minor,
                                 start_year=year, compression='snappy')
        table = pq.read_table(target, columns=['OFE', 'SedLeave'])
    values = table['SedLeave']
    assert pc.all(pc.is_finite(values)).as_py() and pc.min(values).as_py() >= 0, path
    totals = [pc.sum(table.filter(pc.equal(table['OFE'], ofe))['SedLeave']).as_py()
              for ofe in (1, 2, 3)]
    return [value * record['width_m'] / record['metrics']['years'] for value in totals]



def classify(row):
    if row['reference_kg_yr'] <= 1:
        return 'small_pass' if row['within'] else 'small_exceedance'
    if row['within']:
        return 'meaningful_pass'
    return 'meaningful_low' if row['ratio'] < .1 else 'meaningful_high'


def net(values):
    return [values[0], values[1] - values[0], values[2] - values[1]]


def summarize(rows):
    def median(field):
        values = [r[field] for r in rows if r[field] is not None]
        return statistics.median(values) if values else None
    return dict(cases=len(rows),
                median_road_boundary_ratio=median('road_boundary_ratio'),
                median_candidate_road_kg_yr=median('candidate_road_kg_yr'),
                median_reference_road_kg_yr=median('reference_road_kg_yr'),
                candidate_downstream_net_source=sum(r['candidate_downstream_net_kg_yr'] > 0 for r in rows),
                reference_downstream_net_source=sum(r['reference_downstream_net_kg_yr'] > 0 for r in rows),
                largest_absolute_exchange_difference={role: sum(r['largest_exchange_difference'] == role for r in rows)
                    for role in ('road', 'fill', 'buffer')})


def main():
    scores_path = MATRIX / 'magnitude-scores.json'
    scores = json.loads(scores_path.read_text())
    assert len(scores) == 840
    references, rows = {}, []
    for score in scores:
        case = score['case']
        assert case['soil'] in TEXTURES
        folder = MATRIX / 'matrix-v1' / '-'.join(case.values())
        record_path = folder / 'record.json'
        record = json.loads(record_path.read_text())
        assert record['case'] == case and record['binary_sha256'] == SHA
        assert record['physical_pass'] and record['status'] == 'completed'
        key = '-'.join((case['climate'], TEXTURES[case['soil']], case['design'], case['surface'], case['traffic'], 'legacy', 'legacy'))
        if key not in references:
            ref_folder = REFERENCE / key
            ref = json.loads((ref_folder / 'record.json').read_text())
            references[key] = (ref, boundaries(ref_folder, ref), digest(ref_folder / 'record.json'))
        ref, reference, reference_sha = references[key]
        assert score['reference_kg_yr'] == ref['metrics']['sediment_export_kg_yr']
        for name in ('p1.cli', 'p1.man', 'p1.slp'):
            assert record['inputs'][name] == ref['inputs'][name], (case, name)
            assert digest(folder / 'runs' / name) == record['inputs'][name]
        candidate = boundaries(folder, record)
        for actual, audited in zip(candidate, record['audit']['sediment']['ofes']):
            assert math.isclose(actual, audited['boundary_kg_yr'], rel_tol=1e-10, abs_tol=1e-7)
        modern_net, old_net = net(candidate), net(reference)
        delta = [a - b for a, b in zip(modern_net, old_net)]
        assert math.isclose(sum(delta), candidate[2] - reference[2], rel_tol=1e-10, abs_tol=1e-7)
        rows.append(dict(case=case, group=classify(score), candidate_boundary_kg_yr=candidate,
                         reference_boundary_kg_yr=reference, candidate_net_kg_yr=modern_net,
                         reference_net_kg_yr=old_net, exchange_difference_kg_yr=delta,
                         largest_exchange_difference=('road', 'fill', 'buffer')[max(range(3), key=lambda i: abs(delta[i]))],
                         candidate_road_kg_yr=candidate[0], reference_road_kg_yr=reference[0],
                         road_boundary_ratio=candidate[0] / reference[0] if reference[0] > 0 else None,
                         candidate_downstream_net_kg_yr=candidate[2] - candidate[0],
                         reference_downstream_net_kg_yr=reference[2] - reference[0],
                         candidate_record_sha256=digest(record_path), reference_record_sha256=reference_sha))
    groups = defaultdict(list)
    for row in rows:
        groups[row['group']].append(row)
    result = dict(cases=len(rows), unique_references=len(references), source_scores_sha256=digest(scores_path),
                  script_sha256=digest(Path(__file__)), binary_sha256=SHA,
                  limitations='Boundary net exchange is not source-tagged sediment and does not establish parameter causality. Reference uses WEPP2010/legacy soils; candidate uses repaired WEPP/generated soils and controlled fixed-site runtime sidecars. Original magnitude criteria remain unchanged; no withheld outcomes or new model runs.',
                  groups={key: summarize(value) for key, value in sorted(groups.items())}, rows=rows)
    output = HERE / 'role-boundary-assessment-v1.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
