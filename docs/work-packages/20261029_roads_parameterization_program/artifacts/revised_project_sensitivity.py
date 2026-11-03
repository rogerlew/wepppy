"""Declared full-controller width/fill sensitivity; no production formula copies."""
import argparse
from collections import Counter
import json
import hashlib
import os
import re
import datetime
from pathlib import Path
import shutil
import current_r7_roads_v2 as prior
from tests.roads.roads_project import inventory, inspect_outputs, SOURCE_UPLOAD_SHA256

seeds = prior.seeds
SOURCE = prior.SOURCE
ROOT = prior.ROOT.parent / 'revised-project-sensitivity-v1'
PROTOCOL = seeds.ART / 'revised-project-sensitivity-protocol.md'
ALIASES = ('WIDTH_M','width_m','ROAD_WIDTH_M','road_width_m',
           'FILL_LENGTH_M','fill_length_m','FILL_LEN_M','fill_len_m')
CASES = [dict(name=f'w{width}-f{fill}', width=width, fill=fill)
         for width, fill in ((4,30),(8,30),(4,60),(8,60))]


def dependencies():
    return prior.dependencies() | {str(Path(__file__)):seeds.sha(__file__), str(PROTOCOL):seeds.sha(PROTOCOL)}


def declare():
    frozen = seeds.read(prior.ROOT/'declaration.json')
    assert prior.source_snapshot() == frozen['source_inventory']
    for name, value in frozen['binaries'].items():
        assert seeds.sha(seeds.REPO/'wepp_runner/bin'/name) == value
    ROOT.mkdir(exist_ok=False)
    mask = os.umask(0); os.umask(mask)
    seeds.save(ROOT/'declaration.json', dict(cases=CASES, source=str(SOURCE),
        source_inventory=frozen['source_inventory'], binaries=frozen['binaries'],
        dependencies=dependencies(), uid=os.getuid(), gid=os.getgid(), umask=oct(mask),
        prior_declaration_sha256=seeds.sha(prior.ROOT/'declaration.json'),
        scope='public controller, existing legacy templates; no browser/RQ/deployment parity'))


def resolve(controller, properties, params):
    return controller._resolve_segment_run_inputs(properties=properties, params=params,
        segment_id='precedence-control', design='outslope_rutted', warning_counts=Counter(),
        warning_examples=[], warning_limit=20)


def clone(case):
    from wepppy.nodb.mods.roads import Roads
    from wepppy.nodb.base import clear_nodb_file_cache
    root = ROOT/case['name']
    shutil.copytree(SOURCE, root, ignore=shutil.ignore_patterns('*.log','_logs','_query_engine','export'))
    def rebase(value):
        if isinstance(value,dict): return {k:rebase(v) for k,v in value.items()}
        if isinstance(value,list): return [rebase(v) for v in value]
        if isinstance(value,str) and (value==str(SOURCE) or value.startswith(str(SOURCE)+'/')):
            return str(root)+value[len(str(SOURCE)):]
        return value
    for path in root.glob('*.nodb'):
        path.write_text(json.dumps(rebase(json.loads(path.read_text()))))
    seeds.save(root/'baseline-before.json', inventory(root,('wepp/runs','wepp/output')))
    controller = Roads.getInstance(str(root))
    uploaded = root/'roads/roads.uploaded.geojson'
    assert seeds.sha(uploaded) == SOURCE_UPLOAD_SHA256
    payload = seeds.read(uploaded)
    assert len(payload['features']) == 55
    removed = []
    for index, feature in enumerate(payload['features']):
        props = feature['properties']
        removed.append(dict(index=index, values={k:props[k] for k in ALIASES if k in props}))
        for key in ALIASES: props.pop(key,None)
        props['DESIGN'] = 'outslope_rutted'
    seeds.save(root/'removed-properties.json', removed)
    upload = root/'sensitivity-input.geojson'; seeds.save(upload,payload)
    controller.set_uploaded_geojson(str(upload))
    requested = dict(road_width_m_default=case['width'], fill_length_default_m=case['fill'])
    controller.set_params(requested)
    saved = seeds.read(root/'roads.nodb')['py/state']['_roads_params']
    assert all(saved[k] == v for k,v in requested.items())
    with Roads._instances_lock: Roads._instances.pop(str(root),None)
    clear_nodb_file_cache(root.name,wd_override=root)
    controller = Roads.getInstance(str(root))
    assert all(controller._roads_params[k] == v for k,v in requested.items())
    # Explicit valid attributes must win even when fallback values differ.
    explicit = dict(WIDTH_M=6., FILL_LENGTH_M=20.)
    a = resolve(controller,explicit,dict(saved,road_width_m_default=4,fill_length_default_m=30))
    b = resolve(controller,explicit,dict(saved,road_width_m_default=8,fill_length_default_m=60))
    assert a['road_width_m']==b['road_width_m']==6 and a['fill_length_m']==b['fill_length_m']==20
    seeds.save(root/'precedence-readback.json',dict(explicit=explicit,default4_30=a,default8_60=b,
        original_attribute_resolution=[dict(properties={k:f['properties'][k] for k in ALIASES if k in f['properties']},
            default4_30=resolve(controller,f['properties'],dict(saved,road_width_m_default=4,fill_length_default_m=30)),
            default8_60=resolve(controller,f['properties'],dict(saved,road_width_m_default=8,fill_length_default_m=60)))
            for f in seeds.read(SOURCE/'roads/roads.uploaded.geojson')['features']]))
    invalid=[]
    for value in ('bad','nan','inf','-inf'):
        props=dict(WIDTH_M=value,FILL_LENGTH_M=value,RFG_PCT=value,SOIL_TEXTURE='peat')
        row=resolve(controller,props,saved)
        assert row['road_width_m']==case['width'] and row['fill_length_m']==case['fill']
        assert all(row['resolution_sources'][key]=='roads_default' for key in ('road_width_m','fill_length_m','rfg_pct','soil_texture'))
        invalid.append(dict(properties=props,resolved=row))
    seeds.save(root/'invalid-attribute-readback.json',invalid)
    seeds.save(root/'saved-readback.json',dict(requested=requested,reloaded=controller._roads_params))
    return root, controller


def read_case(case):
    import numpy as np
    import pyarrow.parquet as pq
    from wepppy.nodb.mods.roads import Roads
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    root = ROOT/case['name']; controller = Roads.getInstance(str(root))
    receipt = lifecycle.require_current(root)
    records = seeds.read(root/'wepp/roads/segments/roads.segment.pass.manifest.json')
    completed = [r for r in records if r.get('status')=='completed' and r.get('design')=='outslope_rutted']
    assert completed and not any(r.get('status')=='failed' for r in records)
    assert len({r['segment_run_id'] for r in completed})==len(completed)
    binaries=seeds.read(ROOT/'declaration.json')['binaries']
    traces=[]
    for identifier in [r['segment_run_id'] for r in completed]+['w0']:
        path=root/f'wepp/roads/runs/p{identifier}.err'
        trace=path.read_text()
        binary='wepp_261029' if identifier=='w0' else 'wepp_261029_hill'
        role='WATERSHED' if identifier=='w0' else 'HILLSLOPE'
        assert f'binary_sha256={binaries[binary]}' in trace and 'binary_identity_status=ok' in trace
        assert f'WEPP COMPLETED {role} SIMULATION SUCCESSFULLY' in trace
        assert 'Gwcoeff parameters set' in trace
        assert 'WEPP hourly water seepage update set (UI code)' in trace
        if identifier!='w0': assert 'pmetpara.txt' in trace
        assert list(map(int,re.findall(r'SIMULATION YEAR =\s*(\d+)',trace)))==list(range(1,17))
        traces.append(dict(id=identifier,sha256=seeds.sha(path)))
    tc=root/'wepp/roads/runs/tc_out.txt'
    assert tc.is_file() and not tc.is_symlink() and not tc.samefile(root/'wepp/runs/tc_out.txt')
    features = seeds.read(root/'wepp/roads/segments/roads.inslope.monotonic.geojson')['features']
    resolved = {f['properties']['segment_id']:resolve(controller,f['properties'],controller._roads_params) for f in features}
    geometries = {}
    for row in completed:
        assert row['road_width_m']==case['width'] and row['fill_length_m']==case['fill']
        effective = resolved[row['segment_id']]
        assert effective['resolution_sources']['road_width_m']=='roads_default'
        assert effective['resolution_sources']['fill_length_m']=='roads_default'
        run_id = row['segment_run_id']
        lines = (root/f'wepp/roads/runs/p{run_id}.slp').read_text().splitlines()
        assert int(lines[1])==3
        width = float(lines[2].split()[1]); fill = float(lines[5].split()[1])
        assert width==case['width'] and fill==case['fill']
        geometries[str(run_id)] = dict(width=width,lengths=[float(lines[i].split()[1]) for i in (3,5,7)],effective=effective)
    folder = root/'wepp/roads/output/interchange'
    summary = pq.read_table(folder/'roads_segment_loss_summary.parquet').to_pylist()
    total = pq.read_table(folder/'totalwatsed3.parquet').to_pandas()
    wat = pq.read_table(folder/'H.wat.parquet').to_pandas()
    element = pq.read_table(folder/'H.element.parquet').to_pandas()
    role_rows = []
    for rid, geometry in geometries.items():
        subset=wat[wat['wepp_id']==int(rid)]
        assert len(subset)==5844*3 and subset.groupby('ofe_id').size().eq(5844).all()
        start=datetime.date(2000,1,1)
        expected={(day.year,day.timetuple().tm_yday) for day in (start+datetime.timedelta(days=i) for i in range(5844))}
        for _, group in subset.groupby('ofe_id'):
            assert set(zip(group['year'],group['julian']))==expected
        assert all(np.isfinite(subset[c]).all() for c in ('Area','P','Q','Dp','latqcc','UpStrmQ','SubRIn'))
        areas=subset.groupby('ofe_id')['Area'].first().tolist()
        expected=[geometry['width']*length for length in geometry['lengths']]
        assert np.allclose(areas,expected,rtol=0,atol=.0051), (areas,expected)
        geometry['native_wat_areas_m2']=areas
        for ofe, role in ((1,'road'),(2,'fill'),(3,'buffer')):
            water=subset[subset['ofe_id']==ofe]
            events=element[(element['wepp_id']==int(rid)) & (element['ofe_id']==ofe)]
            assert not events.empty and np.isfinite(events['SedLeave']).all() and (events['SedLeave']>=0).all()
            role_rows.append(dict(segment_run_id=int(rid),role=role,area_m2=areas[ofe-1],
                sediment_boundary_kg_yr=float(events['SedLeave'].sum()*geometry['width']/16),
                max_event_sediment_boundary_kg=float(events['SedLeave'].max()*geometry['width']),
                surface_runon_m3_yr=float((water['UpStrmQ']*water['Area']/1000).sum()/16),
                lateral_runon_m3_yr=float((water['SubRIn']*water['Area']/1000).sum()/16),
                lateral_out_m3_yr=float((water['latqcc']*water['Area']/1000).sum()/16),
                deep_percolation_m3_yr=float((water['Dp']*water['Area']/1000).sum()/16),
                q_diagnostic_mm_yr=float(water['Q'].sum()/16)))
    assert inventory(root,('wepp/runs','wepp/output'))==seeds.read(root/'baseline-before.json')
    current = prior.source_snapshot()
    assert current==seeds.read(ROOT/'declaration.json')['source_inventory']
    result=dict(case=case,completed_profiles=len(completed),receipt=receipt,geometry=geometries,native_traces=traces,
        accounting=inspect_outputs(root,'outslope_rutted'),segment_summary=summary,role_boundaries=role_rows,
        total_columns=list(total.columns),source_preserved=True,baseline_preserved=True,
        input_output_hashes=inventory(root,('wepp/roads/runs','wepp/roads/output','wepp/roads/segments')))
    for column in ('sed_del','tdet','tdep','runvol','Runoff','Lateral Flow','Percolation'):
        assert column in total and np.isfinite(total[column]).all(), column
        result.setdefault('annual',{})[column]=float(total[column].sum()/16)
        result.setdefault('max_daily',{})[column]=float(total[column].max())
    result['runtime_inputs']={}
    for path in sorted((root/'wepp/roads/runs').iterdir()):
        if not path.is_file() or path.suffix=='.err' or path.name in {'tc_out.txt','chan.out','chanwb.out'}: continue
        if path.name in {f'p{rid}.slp' for rid in geometries}: continue
        data=path.read_bytes().replace(str(root).encode(),b'<PROJECT>')
        result['runtime_inputs'][path.name]=hashlib.sha256(data).hexdigest()
    result['mean_annual_sediment_kg_m2']=result['annual']['sed_del']/result['accounting']['modeled_area_m2']
    result['yearly']=total.groupby('year')[['sed_del','tdet','tdep','runvol','Runoff']].sum().reset_index().to_dict('records')
    result['largest_sediment_days']=total.nlargest(10,'sed_del')[['year','julian','sed_del','runvol']].to_dict('records')
    seeds.save(ROOT/(case['name']+'-readback.json'),result)
    return result


def compare_results(rows):
    ids = set(rows[0]['geometry'])
    assert all(row['runtime_inputs']==rows[0]['runtime_inputs'] for row in rows), 'Nongeometry runtime input drift'
    assert all(set(row['geometry']) == ids for row in rows)
    for rid in ids:
        for extension in ('sol','man','cli'):
            name=f'wepp/roads/runs/p{rid}.{extension}'
            assert len({row['input_output_hashes'][name] for row in rows})==1, name
        name=f'wepp/roads/runs/p{rid}.slp'
        assert len({row['input_output_hashes'][name] for row in rows})==4, name
    a,b,c,d=rows
    comparisons={}
    for name in ('sed_del','runvol','Runoff','Lateral Flow','Percolation'):
        values=[row['annual'][name] for row in rows]
        comparisons[name]=dict(values=values,width_effect=values[1]-values[0],
            fill_effect=values[2]-values[0],interaction=values[3]-values[1]-values[2]+values[0])
    values=[row['mean_annual_sediment_kg_m2'] for row in rows]
    comparisons['sediment_density_kg_m2_yr']=dict(values=values,interaction=values[3]-values[1]-values[2]+values[0])
    seeds.save(ROOT/'comparison.json',dict(context_order=[c['name'] for c in CASES],
        contrasts=comparisons,distinct_slope_signatures=True,other_input_parity=True))


def run():
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    declaration=seeds.read(ROOT/'declaration.json')
    assert declaration['dependencies']==dependencies()
    assert prior.source_snapshot()==declaration['source_inventory']
    assert not (ROOT/'execution-start.json').exists()
    seeds.save(ROOT/'execution-start.json',dict(declaration_sha256=seeds.sha(ROOT/'declaration.json')))
    for case in CASES:
        assert dependencies()==declaration['dependencies']
        for name,value in declaration['binaries'].items(): assert seeds.sha(seeds.REPO/'wepp_runner/bin'/name)==value
        root,controller=clone(case)
        controller.prepare_segments(); assert not lifecycle.available(root)
        result=controller.run_roads_wepp(); assert result['status']=='completed'
        seeds.save(ROOT/(case['name']+'-completed.json'),dict(case=case,summary=result))
        read_case(case)
        print('Completed',case['name'],flush=True)
    rows=[seeds.read(ROOT/(c['name']+'-readback.json')) for c in CASES]
    compare_results(rows)
    seeds.save(ROOT/'results.json',rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','run','read'))
    args=parser.parse_args()
    if args.action=='read':
        for case in CASES: read_case(case)
    else: {'declare':declare,'run':run}[args.action]()
