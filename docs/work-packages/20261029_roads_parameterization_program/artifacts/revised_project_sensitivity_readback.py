"""Additive readback: classify source-proven chntyp.txt as generated diagnostic."""
import hashlib
import json
from pathlib import Path

ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261103/revised-project-sensitivity-v1')
ART=Path(__file__).resolve().parent
NAMES=('w4-f30','w8-f30','w4-f60','w8-f60')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    dest=ROOT/'qualified-readback.json'
    assert not dest.exists()
    original=read(ROOT/'declaration.json'); continuation=read(ROOT/'continuation-declaration.json')
    assert sha(ROOT/'declaration.json')==continuation['prior_declaration_sha256']
    assert sha(ROOT/'w4-f30-readback.json')==continuation['first_receipt_sha256']
    assert 'Nongeometry runtime input drift' in (ROOT/'continuation-execution.log').read_text()
    source=Path(original['source'])
    for path,value in original['source_inventory'].items(): assert sha(source/path)==value,path
    rows=[read(ROOT/(name+'-readback.json')) for name in NAMES]
    ids=set(rows[0]['geometry'])
    invariant={name:value for name,value in rows[0]['runtime_inputs'].items() if name!='chntyp.txt'}
    table=[]
    for name,row in zip(NAMES,rows):
        assert set(row['geometry'])==ids
        for path,value in row['input_output_hashes'].items(): assert sha(ROOT/name/path)==value,path
        baseline=read(ROOT/name/'baseline-before.json')
        for path,value in baseline.items(): assert sha(ROOT/name/path)==value,path
        actual={path:value for path,value in row['runtime_inputs'].items() if path!='chntyp.txt'}
        assert actual==invariant
        summary=row['segment_summary']
        table.append(dict(case=row['case'],profiles=row['completed_profiles'],
            full_modeled_area_m2=row['accounting']['modeled_area_m2'],
            roads_profile_area_m2=sum(x['modeled_area_m2'] for x in summary),
            roads_mean_annual_sediment_kg=sum(x['sediment_yield_kg'] for x in summary),
            roads_mean_annual_runoff_m3=sum(x['runoff_volume_m3'] for x in summary),
            mixed_mean_annual=row['annual'],
            role_boundary_sediment_kg_yr={role:sum(x['sediment_boundary_kg_yr'] for x in row['role_boundaries'] if x['role']==role) for role in ('road','fill','buffer')},
            protected_baseline_files=len(baseline),artifact_count=len(row['input_output_hashes']),
            generated_chntyp_sha256=sha(ROOT/name/'wepp/roads/runs/chntyp.txt'),
            readback_sha256=sha(ROOT/(name+'-readback.json'))))
    for rid in ids:
        assert len({row['input_output_hashes'][f'wepp/roads/runs/p{rid}.slp'] for row in rows})==4
        for extension in ('man','sol','cli'):
            assert len({row['input_output_hashes'][f'wepp/roads/runs/p{rid}.{extension}'] for row in rows})==1
    interactions={}
    for key in ('roads_mean_annual_sediment_kg','roads_mean_annual_runoff_m3'):
        values=[r[key] for r in table]
        interactions[key]=dict(values=values,width_effect=values[1]-values[0],fill_effect=values[2]-values[0],
            interaction=values[3]-values[1]-values[2]+values[0])
    values=[r['roads_mean_annual_sediment_kg']/r['roads_profile_area_m2'] for r in table]
    interactions['roads_sediment_density_kg_m2_yr']=dict(values=values,interaction=values[3]-values[1]-values[2]+values[0])
    result=dict(status='completed_with_explicit_generated_diagnostic_disposition',
        original_declaration_sha256=sha(ROOT/'declaration.json'),continuation_declaration_sha256=sha(ROOT/'continuation-declaration.json'),
        interrupted_attempts_retained=True,source_files_preserved=len(original['source_inventory']),
        native_calls=sum(row['completed_profiles']+1 for row in rows),
        comparison_disposition='Only chntyp.txt excluded from input parity; source e0abe058 wshdrv516-519 and wshcqi139-154 prove generated write-only diagnostic. Original comparator failure retained.',
        invariant_runtime_files=len(invariant),four_distinct_slopes_per_profile=True,
        contexts=table,interactions=interactions,readback_script_sha256=sha(__file__),
        final_execution_log_sha256=sha(ROOT/'continuation-execution.log'))
    dest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (ART/'revised-project-sensitivity-results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'],native_calls=result['native_calls'],readback_sha256=sha(dest))))


if __name__=='__main__': main()
