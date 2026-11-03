"""Independent raw-table review of the bounded controller geometry study."""
from pathlib import Path
import hashlib
import json
import math

import pyarrow.parquet as pq

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/revised-project-sensitivity-v1')
ART = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    qualified = json.loads((ROOT / 'qualified-readback.json').read_text())
    results = []
    for context in qualified['contexts']:
        name = context['case']['name']
        root = ROOT / name
        receipt_path = ROOT / (name + '-readback.json')
        assert sha(receipt_path) == context['readback_sha256']
        receipt = json.loads(receipt_path.read_text())
        for relative, expected in receipt['input_output_hashes'].items():
            assert sha(root / relative) == expected, (name, relative)
        folder = root / 'wepp/roads/output/interchange'
        passes = pq.read_table(folder / 'H.pass.parquet').to_pandas()
        water = pq.read_table(folder / 'H.wat.parquet').to_pandas()
        elements = pq.read_table(folder / 'H.element.parquet').to_pandas()
        summaries = pq.read_table(folder / 'roads_segment_loss_summary.parquet').to_pylist()
        records = json.loads((root / 'wepp/roads/segments/roads.segment.pass.manifest.json').read_text())
        ids = {r['segment_run_id'] for r in records if r.get('status') == 'completed'}
        assert ids == {r['segment_run_id'] for r in summaries}
        export = runoff = area = 0.
        role_sediment = dict(road=0., fill=0., buffer=0.)
        max_export_difference = 0.
        for row in summaries:
            identifier = row['segment_run_id']
            p = passes[passes.wepp_id == identifier]
            w = water[water.wepp_id == identifier]
            assert len(p) == 5844 and len(p[['year', 'julian']].drop_duplicates()) == 5844
            assert set(p.year) == set(range(2000, 2016))
            mass = float((p.runvol * p[[f'sedcon_{i}' for i in range(1, 6)]].sum(axis=1)).sum() / 16)
            volume = float(p.runvol.sum() / 16)
            local_area = math.fsum(w.groupby('ofe_id').Area.first())
            assert math.isclose(mass, row['sediment_yield_kg'], rel_tol=1e-10, abs_tol=1e-10)
            assert math.isclose(volume, row['runoff_volume_m3'], rel_tol=1e-10, abs_tol=1e-10)
            assert local_area == row['modeled_area_m2']
            max_export_difference = max(max_export_difference, abs(mass-row['sediment_yield_kg']))
            export += mass; runoff += volume; area += local_area
            width = receipt['geometry'][str(identifier)]['width']
            for ofe, role in ((1, 'road'), (2, 'fill'), (3, 'buffer')):
                e = elements[(elements.wepp_id == identifier) & (elements.ofe_id == ofe)]
                mass = float(e.SedLeave.sum() * width / 16)
                role_sediment[role] += mass
                original = next(r for r in receipt['role_boundaries'] if r['segment_run_id'] == identifier and r['role'] == role)
                assert math.isclose(mass, original['sediment_boundary_kg_yr'], rel_tol=1e-10, abs_tol=1e-10)
        assert math.isclose(export, context['roads_mean_annual_sediment_kg'], rel_tol=1e-10)
        assert math.isclose(runoff, context['roads_mean_annual_runoff_m3'], rel_tol=1e-10)
        assert math.isclose(area, context['roads_profile_area_m2'], rel_tol=1e-10)
        results.append(dict(case=name, profiles=len(ids), profile_export_kg_yr=export,
                            profile_runoff_m3_yr=runoff, profile_area_m2=area,
                            export_density_kg_m2_yr=export/area, role_sediment_kg_yr=role_sediment,
                            max_summary_export_difference_kg_yr=max_export_difference,
                            raw_artifacts_verified=len(receipt['input_output_hashes'])))
    result = dict(qualified_readback_sha256=sha(ROOT/'qualified-readback.json'),
                  independent_reader_sha256=sha(__file__), contexts=results,
                  attribution='mixed Roads profile export, not road-prism detachment or watershed outlet yield')
    dest = ART/'revised-project-independent-science-readback.json'
    with dest.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
