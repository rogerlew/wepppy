"""Independent native artifact, strict audit and summary review for 47 profiles."""
from pathlib import Path
import hashlib
import json
import math

import pyarrow.parquet as pq
import rebaseline_r7_seeds as seeds

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/revised-sensitivity-v1')
ART = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    declaration = read(ROOT/'declaration-v6.json')
    rows = read(ROOT/'results.json')
    tasks = {(r['context'], r['arm']): r for r in declaration['tasks']}
    assert len(rows) == len(tasks) == 47
    results = []
    flags = []
    for result in rows:
        key = result['context'], result['arm']
        task = tasks[key]
        root = Path(task['root'])
        assert result == read(root/'result.json') and str(root) == result['root']
        prepared = task['record']
        for relative, expected in prepared['prepared_files'].items():
            assert sha(root/'wepp/roads/runs'/relative) == expected, (key, relative)
        assert sha(root/'climate/site.cli') == prepared['prepared_files']['p1.cli']
        native = read(root/'native-result.json')
        assert len(native['output_sha256']) == 7
        for relative, expected in native['output_sha256'].items():
            assert sha(root/relative) == expected, (key, relative)
        if key == ('G', 'exact'):
            assert {Path(k).name:v for k,v in native['output_sha256'].items()} == native['original_outputs']
        capsule = root/'wepp/roads'
        record = capsule/'record.json'
        particle = seeds.particles.audit(record)
        complete = seeds.pass_completeness.audit(record, declaration['climates'][result['context']])
        assert particle['passed'] == result['diagnostics']['particle_pass']
        assert complete['passed'] == result['diagnostics']['calendar_pass']
        if not particle['passed']:
            flags.append(dict(context=key[0], arm=key[1], flags=particle['flags']))
        p = pq.read_table(capsule/'output/interchange/H.pass.parquet').to_pandas()
        w = pq.read_table(capsule/'output/interchange/H.wat.parquet').to_pandas()
        years = declaration['climates'][key[0]]['years']
        export = math.fsum(p.runvol * p[[f'sedcon_{i}' for i in range(1,6)]].sum(axis=1)) / years
        runoff = math.fsum(p.runvol) / years
        area = math.fsum(w.groupby('ofe_id').Area.first())
        summary = result['response']['summary']
        assert math.isclose(export, summary['sediment_yield_kg'], rel_tol=1e-10, abs_tol=1e-10)
        assert math.isclose(runoff, summary['runoff_volume_m3'], rel_tol=1e-10, abs_tol=1e-10)
        assert area == summary['modeled_area_m2']
        assert result['diagnostics']['physical_pass']
        results.append(dict(context=key[0], arm=key[1], export_kg_yr=export,
                            runoff_m3_yr=runoff, modeled_area_m2=area,
                            export_density_kg_m2_yr=export/area,
                            strict_particle_pass=particle['passed'], calendar_pass=complete['passed'],
                            raw_output_hashes=native['output_sha256']))
    output = dict(declaration_sha256=sha(ROOT/'declaration-v6.json'),
                  results_sha256=sha(ROOT/'results.json'), reader_sha256=sha(__file__),
                  cases=len(results), exact_generated_seven_output_parity=True,
                  strict_particle_flags=flags, strict_particle_passes=sum(r['strict_particle_pass'] for r in results),
                  calendar_passes=sum(r['calendar_pass'] for r in results), profiles=results)
    with (ART/'revised-profile-independent-science-readback.json').open('x') as stream:
        json.dump(output, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k:v for k,v in output.items() if k!='profiles'}, indent=2))


if __name__ == '__main__':
    main()
