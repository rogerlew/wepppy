"""Independent physical-unit/calendar/annual readback of the complete paired ledger.

Never executes WEPP or imports the ledger's implementation/audit helpers.
Kahan/accurate sums are compared using accumulated IEEE rounding bounds only;
these are analysis-algebra checks, not revised model acceptance thresholds.
"""
from pathlib import Path
from decimal import Decimal as D
import argparse
import calendar
import datetime
import hashlib
import json
import math
import duckdb
import pyarrow.parquet as pq

SED = {'sediment_out_kg':'boundary_kg_yr','net_sediment_kg':'net_kg_yr',
       'positive_net_kg':'positive_daily_net_kg_yr','negative_net_kg':'negative_daily_net_kg_yr'}
WATER = ('surface_out_m3','surface_in_m3','lateral_out_m3','lateral_in_m3',
         'precipitation_m3','rain_melt_m3','et_m3','deep_percolation_m3')
COUNTS = ('calendar_rows','element_rows','missing_element_with_surface_flow','positive_sediment_zero_surface_water')
FLUX = set(SED)|set(WATER)
SHA = '2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text())
def quote(path):return "'"+str(path).replace("'","''")+"'"
def half(token):return D(10)**D(token).as_tuple().exponent/D(2)
def near(actual,expected,scale,n):
    u=2**-53;gamma=(8*n+32)*u/(1-(8*n+32)*u)
    bound=gamma*max(scale,abs(expected),1.)
    assert abs(actual-expected)<=bound,(actual,expected,bound)
    return abs(actual-expected),bound


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--preflight',action='store_true');a=ap.parse_args()
    d=read(a.root/'declaration.json')
    assert len(d['tasks'])==116
    if a.preflight:
        index=read(a.root/'preflight.json')['records'];summary=None
        assert len(index)==2
        assert {x['case_id'] for x in index}==set(d['actual_preflight_case_ids'])
    else:
        index=read(a.root/'results.json');summary=read(a.root/'summary.json')
        assert len(index)==116
        assert {x['case_id'] for x in index}=={x['case_id'] for x in d['tasks']}
    assert sha(a.root/'ledger.py')==d['script_sha256']
    if summary is not None:
        assert sha(a.root/'summarize.py')==summary['script_sha256']
        analysis=read(a.root/'analysis-declaration.json')
        assert analysis['summary_script_sha256']==summary['script_sha256']
        assert analysis['ledger_declaration_sha256']==sha(a.root/'declaration.json')
        case_summary={c['case_id']:c for c in read(a.root/'case-summary.json')}
    for p,h in d['dependencies'].items():assert sha(p)==h,p
    con=duckdb.connect();con.execute('SET threads=1')
    names=['declaration.json','ledger.py','summarize.py']+(['preflight.json'] if a.preflight else ['results.json','summary.json','analysis-declaration.json','case-summary.json'])
    evidence={str(a.root/name):sha(a.root/name) for name in names}
    results=[];group_counts={};input_files=output_files=annual_checks=rows_checked=0
    for item in index:
        assert sha(item['receipt'])==item['sha256'];r=read(item['receipt']);task=r['task'];year0,year1=task['first_year'],task['last_year'];years=year1-year0+1
        expected=[(y,j,o) for y in range(year0,year1+1) for j in range(1,366+calendar.isleap(y)) for o in (1,2,3)]
        group_counts[task['group']]=group_counts.get(task['group'],0)+1
        records={};lane_precip={};row_receipt={'case_id':task['case_id'],'lanes':{}}
        for lane in ('legacy','modern'):
            desc=task['records'][lane];assert sha(desc['path'])==desc['sha256'];record=read(desc['path']);records[lane]=record
            assert record['binary_sha256']==SHA
            folder=Path(desc['path']).parent
            for section,sub in [('inputs','runs'),('auxiliary_inputs','runs')]:
                for name,h in record.get(section,{}).items():assert sha(folder/sub/name)==h;input_files+=1
            for name,h in record['outputs'].items():assert sha(folder/'output'/name)==h;output_files+=1
            lines=[line for line in (folder/'runs/p1.slp').read_text().splitlines() if line and not line.startswith('#')]
            wt=lines[2].split()[1];lt=[lines[i].split()[1] for i in (3,5,7)]
            assert D(wt)>0 and all(D(t)>0 for t in lt)
            width=float(wt);metadata_width=record['width_m'];ratio=width/metadata_width
            assert abs(D(wt)-D(str(metadata_width)))<=half(wt)
            assert abs(sum(map(D,lt))-D(str(record['profile_length_m'])))<=sum(map(half,lt))
            area=[width*float(t) for t in lt]
            daily_path=Path(item['receipt']).parent/f'{lane}-daily-ofe.parquet'
            output=r['outputs'][lane+'_daily-ofe'];assert sha(daily_path)==output['sha256']
            table=pq.read_table(daily_path)
            keys=list(zip(*(table[c].to_pylist() for c in ['year','julian','OFE'])))
            assert keys==expected and len(keys)==len(set(keys))
            assert table['sim_day_index'].to_pylist()==[i//3+1 for i in range(len(expected))]
            assert table['date'].to_pylist()==[datetime.date(y,1,1)+datetime.timedelta(days=j-1) for y,j,o in expected]
            rows_checked+=len(keys);lane_precip[lane]=table['precipitation_mm'].to_pylist()
            con.register('daily',table)
            wat=Path(item['receipt']).parent/lane/'H.wat.parquet';element=Path(item['receipt']).parent/lane/'H.element.parquet'
            con.execute('CREATE OR REPLACE TEMP VIEW rawwat AS SELECT * FROM read_parquet('+quote(wat)+')')
            con.execute('CREATE OR REPLACE TEMP VIEW rawelement AS SELECT * FROM read_parquet('+quote(element)+')')
            # Independent source-unit checks against freshly converted native rows.
            invalid=con.execute('''SELECT count(*) FROM daily d JOIN rawwat w USING(year,julian,OFE)
              LEFT JOIN rawelement e USING(year,julian,OFE)
              WHERE d.surface_out_m3 IS DISTINCT FROM w.Q*d.cumulative_area_m2/1000
                 OR d.surface_in_m3 IS DISTINCT FROM w.UpStrmQ*d.local_area_m2/1000
                 OR d.lateral_out_m3 IS DISTINCT FROM w.latqcc*d.local_area_m2/1000
                 OR d.lateral_in_m3 IS DISTINCT FROM w.SubRIn*d.local_area_m2/1000
                 OR d.soil_stock_m3 IS DISTINCT FROM w.SoilWaterTotal*d.local_area_m2/1000
                 OR d.sediment_out_kg IS DISTINCT FROM e.SedLeave*d.width_m
                 OR d.ki_si_kg_s_m4 IS DISTINCT FROM e.Ki*1000000
                 OR d.kr_si_s_m IS DISTINCT FROM e.Kr/1000
                 OR d.element_present IS DISTINCT FROM (e.OFE IS NOT NULL)
                 OR (e.OFE IS NULL AND (d.sediment_out_kg IS NOT NULL OR d.ki_si_kg_s_m4 IS NOT NULL))''').fetchone()[0]
            assert invalid==0
            ratios=con.execute('''SELECT count(*) FROM daily WHERE
               surface_concentration_kg_m3 IS DISTINCT FROM CASE WHEN surface_out_m3>0 THEN sediment_out_kg/surface_out_m3 END
               OR net_delivery_ratio IS DISTINCT FROM CASE WHEN sediment_in_kg>0 THEN sediment_out_kg/sediment_in_kg END
               OR net_sediment_kg IS DISTINCT FROM sediment_out_kg-sediment_in_kg''').fetchone()[0]
            assert ratios==0
            lane_result={'rows':table.num_rows,'width_token':wt,'metadata_width':metadata_width,'width_ratio':ratio,'max_annual_reassociation_error':0.}
            for i,original in enumerate(r['lanes'][lane]['annual']):
                assert set(original)==FLUX|set(COUNTS)|{'OFE'},set(original)
                assert all(isinstance(original[k],int) for k in COUNTS+('OFE',))
                assert all(isinstance(original[k],float) for k in FLUX)
                k=i+1
                geometry=con.execute('SELECT DISTINCT width_m,local_area_m2,cumulative_area_m2 FROM daily WHERE OFE=?',[k]).fetchall()
                assert geometry==[(width,area[i],sum(area[:i+1]))]
                values=con.execute('SELECT '+','.join(sorted(FLUX-{'positive_net_kg','negative_net_kg'}))+' FROM daily WHERE OFE=? ORDER BY year,julian',[k]).fetchall()
                columns={f:[row[j] for row in values if row[j] is not None] for j,f in enumerate(sorted(FLUX-{'positive_net_kg','negative_net_kg'}))}
                columns['positive_net_kg']=[max(v,0.) for v in columns['net_sediment_kg']]
                columns['negative_net_kg']=[min(v,0.) for v in columns['net_sediment_kg']]
                for field,vals in columns.items():
                    total=math.fsum(vals);scale=math.fsum(abs(v) for v in vals);delta,bound=near(total,original[field],scale,len(vals))
                    lane_result['max_annual_reassociation_error']=max(lane_result['max_annual_reassociation_error'],delta)
                    hist=(record['audit']['sediment']['ofes'][i][SED[field]]*ratio if field in SED else record['audit']['water']['ofes'][i][field+'_yr'])
                    near(total/years,hist,scale/years,len(vals));annual_checks+=1
            row_receipt['lanes'][lane]=lane_result
            con.unregister('daily')
        assert set(records['legacy']['inputs'])==set(records['modern']['inputs'])
        assert {n for n in records['legacy']['inputs'] if records['legacy']['inputs'][n]!=records['modern']['inputs'][n]}=={'p1.sol'}
        assert lane_precip['legacy']==lane_precip['modern']
        if not a.preflight:
            terminal=pq.read_table(Path(item['receipt']).parent/'paired-terminal.parquet')
            events=case_summary[task['case_id']]['events']
            row_receipt['EVENT_only_terminal_clay_fractions']={}
            for lane in ('legacy','modern'):
                types=terminal[lane+'_pass_event'].to_pylist()
                present=terminal[lane+'_pass_class_data_present'].to_pylist()
                masses=terminal[lane+'_pass_class_mass_kg'].to_pylist()
                vols=terminal[lane+'_pass_runvol'].to_pylist()
                clay=terminal[lane+'_pass_sedcon_1'].to_pylist()
                assert present==[t=='EVENT' for t in types]
                assert all(m is None for m,yes in zip(masses,present) if not yes)
                numer=math.fsum(v*c for v,c,yes in zip(vols,clay,present) if yes)
                denom=math.fsum(m for m in masses if m is not None)
                expected_fraction=numer/denom if denom>0 else None
                observed=events[lane+'_terminal_clay_mass_fraction']
                if expected_fraction is None:assert observed is None
                else:near(expected_fraction,observed,1.,len(types))
                row_receipt['EVENT_only_terminal_clay_fractions'][lane]=dict(EVENT_count=sum(present),EVENT_sediment_mass_kg=denom,clay_fraction=expected_fraction)
            selected=[]
            names=['legacy_element_present','modern_element_present','legacy_sediment_in_kg','modern_sediment_in_kg','legacy_sediment_out_kg','modern_sediment_out_kg','width_m']
            for lp,mp,li,mi,lo,mo,w in zip(*(terminal[n].to_pylist() for n in names)):
                if lp and mp and li-mi>0.001*w and mo-lo>0.001*w:selected.append(mo-lo)
            assert len(selected)==events['printing_separated_lower_inflow_higher_outflow_days']
            near(math.fsum(selected),events['printing_separated_excess_kg'],math.fsum(abs(v) for v in selected),len(selected))
            row_receipt['printing_separated_events']=len(selected)
        results.append(row_receipt)
        if len(results)%20==0:print(f'Independent review {len(results)}/116',flush=True)
    result=dict(passed=True,scope=('Two-case preflight only; no full-panel acceptance' if a.preflight else 'Full116 exact-R4 observational ledger; no parameter recommendation'),cases=len(index),lanes=2*len(index),
        full_calendar_ofe_rows_checked=rows_checked,original_input_files_rehashed=input_files,original_output_files_rehashed=output_files,
        independent_annual_flux_comparisons=annual_checks,group_counts=group_counts,
        units_checked=['cumulative Q area','local surface/lateral depths','stock depth','SedLeave kg/m times emitted width','Ki ×1e6','Kr /1e3'],
        undefined_ratios_remain_null=True,missing_element_not_physical_zero=True,
        terminal_clay_scope='EVENT-only mass-weighted terminal fraction; not all annual export or upstream class attribution',
        annualized_fields=sorted(FLUX),not_annualized_fields=list(COUNTS)+['OFE'],
        historical_sediment_geometry_bridge='historical per-year value × emitted_width / recorded_width',
        comparison_tolerance='IEEE accumulated reassociation bound only; no native scientific threshold changed',
        script_sha256=sha(__file__),evidence_sha256=evidence,rows=results)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','evidence_sha256']}))


if __name__=='__main__':main()
