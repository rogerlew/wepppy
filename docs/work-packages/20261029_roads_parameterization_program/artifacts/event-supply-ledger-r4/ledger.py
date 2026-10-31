"""Read-only paired R4 whole-profile daily accounting; never executes WEPP."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import calendar
import datetime
from decimal import Decimal
import hashlib
import importlib.util
import json
import math
import sys

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
REPO = Path('/workdir/wepppy')
ART = REPO/'docs/work-packages/20261029_roads_parameterization_program/artifacts'
sys.path.insert(0,str(ART))
import combined_hydraulics_r4 as common
import audit_particle_closure_v2 as particles
from wepppy.wepp.interchange._rust_interchange import call_wepppyo3_interchange, version_args

P = ROOT.parent
SHA = '2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48'
KEYS = ('climate','soil','design','surface','traffic')
ROLES = ('road','fill','buffer')
sha = common.sha
save = common.save
E_FIELDS = {'Precip':'element_precip_mm','Runoff':'element_runoff_raw_mm','EffInt':'effective_intensity_mm_h','PeakRO':'element_peak_runoff_mm_h','EffDur':'effective_duration_h','Enrich':'enrichment_ratio','Keff':'keff_mm_h','Sm':'element_soil_water_raw_mm','LeafArea':'leaf_area_index','CanHgt':'canopy_height_m','Cancov':'canopy_cover_pct','IntCov':'interrill_cover_pct','RilCov':'rill_cover_pct','LivBio':'live_biomass_kg_m2','DeadBio':'dead_biomass_kg_m2','Ki':'ki_raw_million_kg_s_m4','Kr':'kr_native_printed','Tcrit':'critical_shear_pa','RilWid':'rill_width_m','SedLeave':'sediment_out_kg_m','QRain':'element_rain_runoff_raw_mm','QSnow':'element_snow_runoff_raw_mm'}
P_FIELDS = ['event','dur','tcs','runoff','runvol','sbrunv','drrunv','peakro','tdet','tdep',*[f'sedcon_{i}' for i in range(1,6)],'clot','slot','saot','laot','sdot','gwbfv','gwdsv']
B_FIELDS = ['Precip','Runoff','IR-det','Av-det','Mx-det','Det-point','Av-dep','Max-dep','Dep-point','Sed.Del','ER']
PAIR_FIELDS = ['element_present','surface_out_m3','surface_in_m3','lateral_out_m3','lateral_in_m3','precipitation_m3','rain_melt_m3','et_m3','deep_percolation_m3','soil_stock_m3','soil_stock_change_m3','snow_stock_m3','profile_depth_mm','porosity_capacity_mm','field_capacity_store_mm','wilting_store_mm','sediment_out_kg','sediment_in_kg','net_sediment_kg','surface_concentration_kg_m3','net_delivery_ratio','effective_duration_h','element_peak_runoff_mm_h','keff_mm_h','ki_si_kg_s_m4','kr_si_s_m','critical_shear_pa','interrill_cover_pct','rill_cover_pct','element_soil_water_raw_mm']


def ident(row):
    return '-'.join(str(row['case'][k]) for k in KEYS)


def check_source(path, expected):
    path=Path(path)
    assert sha(path)==expected
    r=json.loads(path.read_text())
    assert r['binary_sha256']==SHA and r['physical_pass']
    for section, sub in (('inputs','runs'),('auxiliary_inputs','runs'),('outputs','output')):
        for n,h in r.get(section,{}).items(): assert sha(path.parent/sub/n)==h,(path,n)
    return r



def geometry(record, folder):
    lines=[x for x in (Path(folder)/'runs/p1.slp').read_text().splitlines() if x and not x.startswith('#')]
    assert int(lines[1])==3 and len(lines)==9
    width_token=lines[2].split()[1];length_tokens=[lines[i].split()[1] for i in (3,5,7)]
    D=Decimal
    half=lambda token:D(10)**D(token).as_tuple().exponent/2
    width=D(width_token);lengths=list(map(D,length_tokens))
    assert width.is_finite() and width>0 and all(x.is_finite() and x>0 for x in lengths)
    width_delta=D(str(record['width_m']))-width
    length_delta=D(str(record['profile_length_m']))-sum(lengths)
    assert abs(width_delta)<=half(width_token),(record['case'],'width serialization',width_delta,half(width_token))
    assert abs(length_delta)<=sum(map(half,length_tokens)),(record['case'],'length serialization',length_delta)
    segments=[]
    for header,points in zip((3,5,7),(4,6,8)):
        n=int(lines[header].split()[0]);values=list(map(float,lines[points].replace(',',' ').split()));assert len(values)==2*n
        coordinates=values[::2];slopes=values[1::2]
        assert coordinates[0]==0 and coordinates[-1]==1 and all(a<b for a,b in zip(coordinates,coordinates[1:])) and all(x>=0 and math.isfinite(x) for x in slopes)
        segments.append(dict(coordinates=coordinates,slopes=slopes))
    return dict(width_token=width_token,length_tokens=length_tokens,emitted_width_m=float(width),record_width_m=record['width_m'],emitted_total_length_m=float(sum(lengths)),record_total_length_m=record['profile_length_m'],width_metadata_minus_emitted_decimal=str(width_delta),width_serialization_half_place_m=str(half(width_token)),total_length_metadata_minus_emitted_decimal=str(length_delta),total_length_serialization_half_place_m=str(sum(map(half,length_tokens))),emitted_to_record_width_ratio=float(width)/record['width_m'],segments=segments,source_slope_sha256=sha(Path(folder)/'runs/p1.slp'))

def dependencies():
    d=common.effective_dependencies()
    for path in [ART/'audit_particle_closure_v2.py',ART/'event-supply-retention-r4-plan.md',Path(common.__file__),Path(__file__),Path('/workdir/wepppyo3/wepp_interchange/src/hill_element.rs')]:d[str(path.resolve())]=sha(path)
    frozen=P/'param-sign-u12-combined/build/src'
    for n in ('sedout.for','contin.for','watbal.for','watbal_hourly.for','wshpas.for'):d[str((frozen/n).resolve())]=sha(frozen/n)
    for n in ('schema.rs','hill_wat.rs','hill_ebe.rs','hill_pass.rs'):
        path=Path('/workdir/wepppyo3/wepp_interchange/src')/n;d[str(path.resolve())]=sha(path)
    return d


def declare():
    assert not (ROOT/'declaration.json').exists()
    panel=P/'legacy-soil-anchors-r4/results.json';rows=json.loads(panel.read_text());assert len(rows)==116
    manifest=common.c.BATCH/'inputs/manifest.json';climates=json.loads(manifest.read_text())['climates']
    tasks=[]
    for r in rows:
        rp=Path(r['folder'])/'record.json';mp=Path(r['modern_source'])/'record.json'
        l=check_source(rp,sha(rp));m=check_source(mp,r['modern_record_sha256'])
        assert {n for n in l['inputs'] if l['inputs'][n]!=m['inputs'][n]}=={'p1.sol'}
        g=geometry(l,rp.parent);assert g==geometry(m,mp.parent)
        climate=climates[r['case']['climate']];first=int(climate['first'].split('-')[0]);last=int(climate['last'].split('-')[0])
        tasks.append(dict(geometry=g,case_id=ident(r),case={k:r['case'][k] for k in KEYS},group=r['group'],reference_kg_yr=r['reference_kg_yr'],first_year=first,last_year=last,records={'legacy':{'path':str(rp),'sha256':sha(rp)},'modern':{'path':str(mp),'sha256':sha(mp)}}))
    assert len({r['case_id'] for r in tasks})==116
    schema=dict(version=1,scope='Complete calendar, three OFEs, exact R4 legacy and generated soils; no native executions.',compatibility='New analysis-only Parquet/JSON under a separate ignored root; no existing data/schema edits.',calendar='WAT and PASS require every declared calendar day; ELEMENT and EBE retain sparse observation support and NULL for missing rows. Native ELEMENT year index is mapped using the frozen climate first year.',water='Surface Q times cumulative exact slope area /1000; all other local water depths times local exact slope area /1000. QOFE retained as raw diagnostic only. PASS volume is separately threshold-filtered.',sediment='ELEMENT kg/m times emitted hillslope width; net is out minus upstream boundary. Missing ELEMENT stays NULL. reported_delta uses zero ONLY for absent contributions to the sum of reported rows, never as a physical-zero claim.',erosion_units='Native writer scales Ki/1e6 and Kr*1e3. Preserve raw values; SI Ki=raw*1e6, Kr=raw/1e3. Current parser metadata has incomplete units; no parser rewrite.',ratios='Concentration only for positive matching physical surface volume and observed mass; delivery only for positive incoming mass. No epsilon or clipping.',particles='Versioned v2 fixed-width audit, unchanged criteria; terminal PASS class data only for EVENT. No per-OFE particle origin inference.',residual='Soil stock residual is apparent and incomplete; interception/snow/support limitations remain explicit.',comparison='Daily same-support physical differences separate from reported-row contribution differences. No WEPP2010 event comparison.',regression='Rehash all original inputs/ordinary outputs before and after conversion; freshly reparse all four output families; exact calendar and duplicate checks; annual sediment/water comparisons against accepted audits; full output readback and hash receipt.')
    schema['geometry_bridge']='Exact Decimal token intervals validate historical unrounded metadata. Ledger uses emitted width/areas. Historical sediment audits retain record width; compare via emitted_width/record_width. This changes no native/audit threshold.'
    schema['particles']+=' Particle mass audit retains historical record-width basis.'
    save(ROOT/'schema.json',schema)
    save(ROOT/'declaration.json',dict(tasks=tasks,cases=116,lanes=232,binary_sha256=SHA,source_panel_sha256=sha(panel),calendar_manifest=str(manifest.resolve()),calendar_manifest_sha256=sha(manifest),script_sha256=sha(__file__),dependencies=dependencies(),versions=dict(pyarrow=pa.__version__,duckdb=duckdb.__version__),schema_sha256=sha(ROOT/'schema.json'),geometry_preflight_cases=len(tasks),actual_preflight_case_ids=[tasks[0]['case_id'],next(t['case_id'] for t in tasks if t['case']['design']=='outunrut')]))
    print('Declared116 paired cases; no native runs',flush=True)


def sqlquote(s):return "'"+str(s).replace("'","''")+"'"

def write_table(table,path,declhash):
    meta=dict(table.schema.metadata or {});meta.update({b'roads_ledger_schema':b'1',b'declaration_sha256':declhash.encode()})
    pq.write_table(table.replace_schema_metadata(meta),path,compression='zstd')
    read=pq.read_table(path)
    assert read.equals(table,check_metadata=False)
    return dict(path=str(path),sha256=sha(path),rows=table.num_rows,columns=len(table.column_names))


def convert_lane(task,lane,dest):
    desc=task['records'][lane];r=check_source(desc['path'],desc['sha256']);folder=Path(desc['path']).parent
    dest.mkdir(parents=True,exist_ok=False)
    first,last=task['first_year'],task['last_year'];years=last-first+1
    major,minor=version_args();tables={};receipts={}
    for kind,method in [('wat','hillslope_wat_files_to_parquet'),('element','hillslope_element_files_to_parquet'),('ebe','hillslope_ebe_files_to_parquet'),('pass','hillslope_pass_files_to_parquet')]:
        path=dest/f'H.{kind}.parquet';kwargs=dict(compression='snappy')
        if kind in ('element','ebe'):kwargs['start_year']=first
        if kind in ('wat','ebe','pass'):kwargs['cli_calendar_path']=None
        if kind=='pass':kwargs['pass_family']='legacy_ascii'
        result=call_wepppyo3_interchange('Roads paired ledger',method,[str(folder/f'output/H1.{kind}.dat')],str(path),major,minor,**kwargs)
        tables[kind]=pq.read_table(path);receipts[kind]=dict(path=str(path),sha256=sha(path),rows=tables[kind].num_rows)
    expected={(y,j) for y in range(first,last+1) for j in range(1,366+calendar.isleap(y))}
    for kind in ('wat','element','ebe','pass'):
        t=tables[kind];cols=[t[n].to_pylist() for n in (('year','julian','OFE') if kind in ('wat','element') else ('year','julian'))];keys=list(zip(*cols));assert len(keys)==len(set(keys)),(task['case_id'],lane,kind,'duplicate')
        dates={(k[0],k[1]) for k in keys};assert dates<=expected
        if kind=='wat':assert set(keys)=={(y,j,i) for y,j in expected for i in (1,2,3)}
        if kind=='pass':assert dates==expected and len(keys)==len(expected)
        if kind=='element':assert set(keys)=={(y,j,i) for y,j in dates for i in (1,2,3)}
    lines=[x for x in (folder/'runs/p1.slp').read_text().splitlines() if x and not x.startswith('#')]
    g=geometry(r,folder);assert g==task['geometry']
    width=g['emitted_width_m'];audit_width=r['width_m'];width_ratio=g['emitted_to_record_width_ratio']
    areas=[width*float(lines[i].split()[1]) for i in (3,5,7)]
    geo_table=pa.Table.from_pylist([dict(OFE=i+1,role=ROLES[i],local_area_m2=areas[i],cumulative_area_m2=sum(areas[:i+1]),width_m=width,record_width_m=audit_width) for i in range(3)])
    con=duckdb.connect();con.execute('SET threads=1')
    for name,table in tables.items():con.register(name,table)
    con.register('geo',geo_table)
    eraw=', '.join(f'e."{old}" AS {new}' for old,new in E_FIELDS.items())
    base=f'''SELECT w.year,w.julian,w.sim_day_index,w.month,w.day_of_month,w.OFE,g.role,g.local_area_m2,g.cumulative_area_m2,g.width_m,g.record_width_m,
      make_date(w.year,1,1)+(w.julian-1)::INTEGER AS date,
      e.OFE IS NOT NULL AS element_present,CASE WHEN e.OFE IS NOT NULL THEN w.year-{first}+1 END AS element_native_year_index,
      w.Area AS reported_local_area_m2,w.P AS precipitation_mm,w.RM AS rain_melt_mm,w.Q AS cumulative_q_mm,w.QOFE AS qofe_raw_mm,
      w.UpStrmQ AS runon_local_mm,w.SubRIn AS lateral_in_local_mm,w.latqcc AS lateral_out_local_mm,
      w.P*g.local_area_m2/1000 AS precipitation_m3,w.RM*g.local_area_m2/1000 AS rain_melt_m3,
      w.Q*g.cumulative_area_m2/1000 AS surface_out_m3,w.UpStrmQ*g.local_area_m2/1000 AS surface_in_m3,
      w.SubRIn*g.local_area_m2/1000 AS lateral_in_m3,w.latqcc*g.local_area_m2/1000 AS lateral_out_m3,
      (w.Ep+w.Es+w.Er)*g.local_area_m2/1000 AS et_m3,w.Dp*g.local_area_m2/1000 AS deep_percolation_m3,
      w.Tile*g.local_area_m2/1000 AS tile_m3,w.Irr*g.local_area_m2/1000 AS irrigation_m3,
      w.SoilWaterTotal*g.local_area_m2/1000 AS soil_stock_m3,w."Snow-Water"*g.local_area_m2/1000 AS snow_stock_m3,
      w.SoilWaterTotal AS soil_water_total_mm,w.ProfileDepth AS profile_depth_mm,w.ProfilePorosityCap AS porosity_capacity_mm,
      w.ProfileFCStore AS field_capacity_store_mm,w.ProfileWPStore AS wilting_store_mm,w.InterceptionStorage AS interception_storage_mm,
      {eraw},e.SedLeave*g.width_m AS sediment_out_kg,e.Ki*1000000 AS ki_si_kg_s_m4,e.Kr/1000 AS kr_si_s_m
      FROM wat w JOIN geo g USING(OFE) LEFT JOIN element e USING(year,julian,OFE)'''
    con.execute('CREATE TEMP VIEW base AS '+base)
    con.execute('''CREATE TEMP VIEW flux AS SELECT *,
      CASE WHEN OFE=1 THEN 0.0 ELSE lag(sediment_out_kg) OVER(PARTITION BY year,julian ORDER BY OFE) END AS sediment_in_kg,
      soil_stock_m3-lag(soil_stock_m3) OVER(PARTITION BY OFE ORDER BY year,julian) AS soil_stock_change_m3,
      CASE WHEN OFE=1 THEN 0.0 ELSE lag(surface_out_m3) OVER(PARTITION BY year,julian ORDER BY OFE) END AS upstream_surface_out_m3,
      CASE WHEN OFE=1 THEN 0.0 ELSE lag(lateral_out_m3) OVER(PARTITION BY year,julian ORDER BY OFE) END AS upstream_lateral_out_m3
      FROM base''')
    q='''SELECT *,sediment_out_kg-sediment_in_kg AS net_sediment_kg,
      CASE WHEN surface_out_m3>0 THEN sediment_out_kg/surface_out_m3 END AS surface_concentration_kg_m3,
      CASE WHEN sediment_in_kg>0 THEN sediment_out_kg/sediment_in_kg END AS net_delivery_ratio,
      surface_out_m3=0 AND sediment_out_kg>0 AS positive_sediment_zero_surface_water,
      surface_in_m3-upstream_surface_out_m3 AS surface_transfer_difference_m3,
      lateral_in_m3-upstream_lateral_out_m3 AS lateral_transfer_difference_m3,
      rain_melt_m3+surface_in_m3+lateral_in_m3-surface_out_m3-lateral_out_m3-et_m3-deep_percolation_m3-tile_m3-soil_stock_change_m3 AS apparent_soil_residual_m3
      FROM flux ORDER BY year,julian,OFE'''
    daily=con.execute(q).fetch_arrow_table();con.register('daily',daily)
    flag_audit=particles.audit(Path(desc['path']));save(dest/'particle-audit-v2.json',flag_audit)
    flags=pa.Table.from_pylist([dict(year=x['year'],julian=x['julian'],particle_flag=True,particle_causes=','.join(x['causes'])) for x in flag_audit['flags']],schema=pa.schema([('year',pa.int16()),('julian',pa.int16()),('particle_flag',pa.bool_()),('particle_causes',pa.string())]));con.register('flags',flags)
    passcols=', '.join(f'p."{x}" AS pass_{x}' for x in P_FIELDS)
    ebecols=', '.join(f'b."{x}" AS ebe_{x.replace("-","_").replace(".","_")}' for x in B_FIELDS)
    mass=' + '.join(f'p.sedcon_{i}' for i in range(1,6))
    terminal=con.execute(f'''SELECT d.*,p.event IS NOT NULL AS pass_present,{passcols},p.event='EVENT' AS pass_class_data_present,
       CASE WHEN p.event='EVENT' THEN p.runvol*({mass}) END AS pass_class_mass_kg,
       b.year IS NOT NULL AS ebe_present,{ebecols},coalesce(f.particle_flag,false) AS strict_particle_flag,f.particle_causes
       FROM daily d LEFT JOIN pass p USING(year,julian) LEFT JOIN ebe b USING(year,julian) LEFT JOIN flags f USING(year,julian)
       WHERE d.OFE=3 ORDER BY year,julian''').fetch_arrow_table()
    # Fresh canonical tables replay the existing accepted annual auditing code.
    sed,days=common.c.e.a.sediment_diagnostics(tables['element'].to_pylist(),audit_width,years,r['metrics']['sediment_export_kg_yr'])
    water=common.c.e.a.a.water_budget(tables['wat'].to_pylist(),areas,expected,years)
    assert sed==r['audit']['sediment'] and water==r['audit']['water'],(task['case_id'],lane,'accepted audit replay')
    annual=con.execute('''SELECT OFE,sum(sediment_out_kg) AS sediment_out_kg,sum(net_sediment_kg) AS net_sediment_kg,
      sum(greatest(net_sediment_kg,0)) AS positive_net_kg,sum(least(net_sediment_kg,0)) AS negative_net_kg,
      sum(surface_out_m3) AS surface_out_m3,sum(surface_in_m3) AS surface_in_m3,sum(lateral_out_m3) AS lateral_out_m3,sum(lateral_in_m3) AS lateral_in_m3,
      sum(precipitation_m3) AS precipitation_m3,sum(rain_melt_m3) AS rain_melt_m3,sum(et_m3) AS et_m3,sum(deep_percolation_m3) AS deep_percolation_m3,
      count(*) AS calendar_rows,count(*) FILTER (WHERE element_present) AS element_rows,
      count(*) FILTER (WHERE NOT element_present AND surface_out_m3>0) AS missing_element_with_surface_flow,
      count(*) FILTER (WHERE positive_sediment_zero_surface_water) AS positive_sediment_zero_surface_water
      FROM daily GROUP BY OFE ORDER BY OFE''').fetch_arrow_table().to_pylist()
    # This bound covers double-precision reassociation only, not native acceptance.
    u=2**-53;n=4*len(expected)+8;gamma=n*u/(1-n*u)
    for i,s in enumerate(annual):
        comparisons={'sediment_out_kg':sed['ofes'][i]['boundary_kg_yr'],'net_sediment_kg':sed['ofes'][i]['net_kg_yr'],'positive_net_kg':sed['ofes'][i]['positive_daily_net_kg_yr'],'negative_net_kg':sed['ofes'][i]['negative_daily_net_kg_yr']}
        comparisons={k:v*width_ratio for k,v in comparisons.items()}
        comparisons.update({x:water['ofes'][i][x+'_yr'] for x in ('surface_out_m3','surface_in_m3','lateral_out_m3','lateral_in_m3','precipitation_m3','rain_melt_m3','et_m3','deep_percolation_m3')})
        scale=max([abs(v) for k,v in s.items() if isinstance(v,(float,int))]+[1.0])/years
        for field,reference in comparisons.items():assert abs(s[field]/years-reference)<=gamma*scale,(task['case_id'],lane,field)
    check_source(desc['path'],desc['sha256'])
    con.close()
    return daily,terminal,dict(geometry_bridge=task['geometry'],historical_sediment_audit_width_basis='record_width_m',physical_ledger_width_basis='emitted_width_m',record=desc,parsed=receipts,particle_audit_sha256=sha(dest/'particle-audit-v2.json'),particle_events=flag_audit['events'],particle_flags=flag_audit['flags'],unavailable_diagnostics=flag_audit['numeric_unavailable_diagnostics'],annual=annual,report_kg_yr=r['metrics']['sediment_export_kg_yr'],report_delta_kg_yr=sed['report_delta_kg_yr'],report_bound_kg_yr=sed['report_bound_kg_yr'],annual_accepted_audits_replayed_exactly=True)


def execute(task):
    dest=ROOT/'cases'/task['case_id'];dest.mkdir(parents=True,exist_ok=False)
    declhash=sha(ROOT/'declaration.json');tables={};receipts={};written={}
    for lane in ('legacy','modern'):
        daily,terminal,receipts[lane]=convert_lane(task,lane,dest/lane)
        tables[lane]=(daily,terminal)
        for name,t in [('daily-ofe',daily),('terminal',terminal)]:written[lane+'_'+name]=write_table(t,dest/f'{lane}-{name}.parquet',declhash)
    con=duckdb.connect();con.execute('SET threads=1')
    for lane,(daily,terminal) in tables.items():con.register(lane,daily);con.register(lane+'_terminal',terminal)
    identity=', '.join(f'{sqlquote(v)} AS {k}' for k,v in dict(case_id=task['case_id'],**task['case'],original_group=task['group']).items())
    fields=', '.join(f'{lane[0]}."{f}" AS {lane}_{f}' for lane in ('legacy','modern') for f in PAIR_FIELDS)
    deltas=', '.join(f'm.{f}-l.{f} AS delta_{f}' for f in ('surface_out_m3','surface_in_m3','lateral_out_m3','lateral_in_m3','deep_percolation_m3','soil_stock_m3','sediment_out_kg','sediment_in_kg','net_sediment_kg'))
    pair=con.execute(f'''SELECT {identity},l.year,l.julian,l.sim_day_index,l.date,l.OFE,l.role,l.local_area_m2,l.cumulative_area_m2,l.width_m,l.record_width_m,{fields},{deltas},
      CASE WHEN l.element_present AND m.element_present THEN 'both' WHEN l.element_present THEN 'legacy_only' WHEN m.element_present THEN 'modern_only' ELSE 'neither' END AS sediment_observation_support,
      coalesce(m.sediment_out_kg,0)-coalesce(l.sediment_out_kg,0) AS delta_reported_sediment_out_kg,
      coalesce(m.net_sediment_kg,0)-coalesce(l.net_sediment_kg,0) AS delta_reported_net_sediment_kg
      FROM legacy l JOIN modern m USING(year,julian,OFE) ORDER BY year,julian,OFE''').fetch_arrow_table()
    assert pair.num_rows==tables['legacy'][0].num_rows==tables['modern'][0].num_rows
    written['paired_daily']=write_table(pair,dest/'paired-daily-ofe.parquet',declhash)
    con.register('paired',pair)
    special=[f for f in tables['legacy'][1].column_names if f.startswith(('pass_','ebe_','strict_','particle_'))]
    tcols=', '.join(f'{lane[0]}."{f}" AS {lane}_{f}' for lane in ('legacy','modern') for f in special)
    term=con.execute(f'''SELECT p.*,{tcols} FROM paired p JOIN legacy_terminal l USING(year,julian) JOIN modern_terminal m USING(year,julian) WHERE p.OFE=3 ORDER BY p.year,p.julian''').fetch_arrow_table()
    written['paired_terminal']=write_table(term,dest/'paired-terminal.parquet',declhash)
    con.close()
    result=dict(task=task,years=task['last_year']-task['first_year']+1,lanes=receipts,outputs=written)
    save(dest/'receipt.json',result)
    print(task['case_id'],'annual boundaries/water reconcile; calendar rows',pair.num_rows,flush=True)
    return dict(case_id=task['case_id'],receipt=str(dest/'receipt.json'),sha256=sha(dest/'receipt.json'))


def run(preflight=False):
    d=json.loads((ROOT/'declaration.json').read_text());assert d['script_sha256']==sha(__file__) and d['dependencies']==dependencies()
    if preflight:
        rows=[execute(t) for t in d['tasks'] if t['case_id'] in d['actual_preflight_case_ids']]
        assert len(rows)==2;save(ROOT/'preflight.json',dict(records=rows,declaration_sha256=sha(ROOT/'declaration.json')));return
    pre=json.loads((ROOT/'preflight.json').read_text());assert pre['declaration_sha256']==sha(ROOT/'declaration.json')
    for r in pre['records']:assert sha(r['receipt'])==r['sha256']
    rows=pre['records'];done={r['case_id'] for r in rows}
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows.extend(pool.map(execute,[t for t in d['tasks'] if t['case_id'] not in done]))
    save(ROOT/'results.json',rows)
    print('Completed paired ledger116cases',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','preflight','run'));args=parser.parse_args()
    {'declare':declare,'preflight':lambda:run(True),'run':run}[args.action]()
