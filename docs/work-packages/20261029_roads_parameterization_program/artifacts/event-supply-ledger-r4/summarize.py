"""Validate persisted paired ledgers and summarize diagnostic response mechanisms."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib
import json
import math
import statistics
import sys

import duckdb
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import ledger
sha=ledger.sha;save=ledger.save


def records(con,sql):return con.execute(sql).fetch_arrow_table().to_pylist()
def stats(values):
    vals=[x for x in values if x is not None]
    return dict(n=len(vals),missing=len(values)-len(vals),median=statistics.median(vals) if vals else None,min=min(vals) if vals else None,max=max(vals) if vals else None)


def main():
    declaration=json.loads((ROOT/'declaration.json').read_text());index=json.loads((ROOT/'results.json').read_text())
    assert len(index)==116 and {r['case_id'] for r in index}=={r['case_id'] for r in declaration['tasks']}
    cases=[];annual_checks=0;output_checks=0;source_checks=0;particle_events=0;particle_flags=[];unavailable=[]
    flux_fields={'sediment_out_kg','net_sediment_kg','positive_net_kg','negative_net_kg','surface_out_m3','surface_in_m3','lateral_out_m3','lateral_in_m3','precipitation_m3','rain_melt_m3','et_m3','deep_percolation_m3'}
    for item in index:
        assert sha(item['receipt'])==item['sha256'];r=json.loads(Path(item['receipt']).read_text());t=r['task'];y=r['years']
        for output in r['outputs'].values():
            assert sha(output['path'])==output['sha256'];meta=pq.ParquetFile(output['path']);assert meta.metadata.num_rows==output['rows'];output_checks+=1
        for lane,data in r['lanes'].items():
            record=ledger.check_source(data['record']['path'],data['record']['sha256']);source_checks+=1
            assert data['annual_accepted_audits_replayed_exactly'];annual_checks+=1
            particle_events+=data['particle_events'];particle_flags.extend(dict(case=t['case'],lane=lane,flag=f) for f in data['particle_flags'])
            unavailable.extend(dict(case=t['case'],lane=lane,field=f) for f in data['unavailable_diagnostics'])
            for parsed in data['parsed'].values():assert sha(parsed['path'])==parsed['sha256'];output_checks+=1
        c=dict(case_id=t['case_id'],**t['case'],group=t['group'],years=y,reference_kg_yr=t['reference_kg_yr'],lanes={})
        for lane,data in r['lanes'].items():
            c['lanes'][lane]=dict(report_kg_yr=data['report_kg_yr'],report_delta_kg_yr=data['report_delta_kg_yr'],report_bound_kg_yr=data['report_bound_kg_yr'],ofes=[{k:(v/y if k in flux_fields else v) for k,v in row.items()} for row in data['annual']])
        cases.append(c)
    con=duckdb.connect();con.execute('SET threads=4')
    con.execute('CREATE VIEW daily AS SELECT * FROM read_parquet('+ledger.sqlquote(ROOT/'cases/*/paired-daily-ofe.parquet')+')')
    con.execute('CREATE VIEW terminal AS SELECT * FROM read_parquet('+ledger.sqlquote(ROOT/'cases/*/paired-terminal.parquet')+')')
    # Calendar/geometry validation is independent of the ledger's generation loop.
    bad=records(con,'''SELECT case_id FROM daily GROUP BY case_id HAVING count(*)!=3*count(DISTINCT (year,julian)) OR count(*)!=count(DISTINCT (year,julian,OFE)) OR min(sim_day_index)!=1 OR max(sim_day_index)!=count(DISTINCT (year,julian))''');assert not bad,bad
    assert not records(con,'''SELECT case_id FROM daily WHERE date!=make_date(year,1,1)+(julian-1)::INTEGER OR NOT isfinite(delta_reported_sediment_out_kg) OR legacy_surface_out_m3<0 OR modern_surface_out_m3<0 OR legacy_sediment_out_kg<0 OR modern_sediment_out_kg<0 LIMIT 1''')
    dimensions=records(con,'SELECT count(*) AS ofe_days,count(DISTINCT (case_id,year,julian)) AS case_days,count(DISTINCT case_id) AS cases FROM daily')[0]
    support=records(con,'''SELECT original_group,role,sediment_observation_support,count(*) AS days,sum(delta_reported_sediment_out_kg) AS reported_sediment_difference_kg FROM daily GROUP BY ALL ORDER BY ALL''')
    event=records(con,'''SELECT case_id,
      count(*) AS calendar_days,count(*) FILTER (WHERE legacy_pass_event='EVENT') AS legacy_events,count(*) FILTER (WHERE modern_pass_event='EVENT') AS modern_events,
      count(*) FILTER (WHERE legacy_surface_out_m3>0) AS legacy_surface_flow_days,count(*) FILTER (WHERE modern_surface_out_m3>0) AS modern_surface_flow_days,
      count(*) FILTER (WHERE legacy_surface_out_m3=0 AND modern_surface_out_m3>0) AS modern_only_surface_flow_days,
      count(*) FILTER (WHERE legacy_surface_out_m3>0 AND modern_surface_out_m3=0) AS legacy_only_surface_flow_days,
      count(*) FILTER (WHERE legacy_element_present AND modern_element_present AND modern_sediment_in_kg<=legacy_sediment_in_kg AND modern_sediment_out_kg>legacy_sediment_out_kg) AS lower_inflow_higher_outflow_days,
      sum(CASE WHEN legacy_element_present AND modern_element_present AND modern_sediment_in_kg<=legacy_sediment_in_kg AND modern_sediment_out_kg>legacy_sediment_out_kg THEN modern_sediment_out_kg-legacy_sediment_out_kg ELSE 0 END) AS lower_inflow_higher_outflow_excess_kg,
      count(*) FILTER (WHERE legacy_element_present AND modern_element_present AND legacy_sediment_in_kg-modern_sediment_in_kg>0.001*width_m AND modern_sediment_out_kg-legacy_sediment_out_kg>0.001*width_m) AS printing_separated_lower_inflow_higher_outflow_days,
      sum(CASE WHEN legacy_element_present AND modern_element_present AND legacy_sediment_in_kg-modern_sediment_in_kg>0.001*width_m AND modern_sediment_out_kg-legacy_sediment_out_kg>0.001*width_m THEN modern_sediment_out_kg-legacy_sediment_out_kg ELSE 0 END) AS printing_separated_excess_kg,
      sum(delta_reported_sediment_out_kg) AS reported_outlet_difference_kg,
      sum(CASE WHEN legacy_element_present AND modern_element_present THEN modern_sediment_out_kg-legacy_sediment_out_kg ELSE 0 END) AS matched_element_difference_kg,
      sum(CASE WHEN sediment_observation_support='modern_only' THEN modern_sediment_out_kg ELSE 0 END) AS modern_only_reported_sediment_kg,
      sum(CASE WHEN sediment_observation_support='legacy_only' THEN legacy_sediment_out_kg ELSE 0 END) AS legacy_only_reported_sediment_kg,
      sum(CASE WHEN modern_pass_class_data_present THEN modern_pass_runvol*modern_pass_sedcon_1 ELSE 0 END)/nullif(sum(modern_pass_class_mass_kg),0) AS modern_terminal_clay_mass_fraction,
      sum(CASE WHEN legacy_pass_class_data_present THEN legacy_pass_runvol*legacy_pass_sedcon_1 ELSE 0 END)/nullif(sum(legacy_pass_class_mass_kg),0) AS legacy_terminal_clay_mass_fraction
      FROM terminal GROUP BY case_id ORDER BY case_id''')
    by_event={r['case_id']:r for r in event}
    for c in cases:
        e=by_event[c['case_id']];c['events']=e;m=c['lanes']['modern']['ofes'];l=c['lanes']['legacy']['ofes']
        delta=(m[2]['sediment_out_kg']-l[2]['sediment_out_kg'])*c['years']
        bound=(4*e['calendar_days']+8)*2**-53*max(abs(delta),m[2]['sediment_out_kg']*c['years'],l[2]['sediment_out_kg']*c['years'],1)
        assert abs(e['reported_outlet_difference_kg']-delta)<=bound
        assert abs(e['reported_outlet_difference_kg']-(e['matched_element_difference_kg']+e['modern_only_reported_sediment_kg']-e['legacy_only_reported_sediment_kg']))<=bound
        c['paired_annual']={f:{role:m[i][f]-l[i][f] for i,role in enumerate(ledger.ROLES)} for f in ('sediment_out_kg','net_sediment_kg','surface_out_m3','surface_in_m3','deep_percolation_m3')}
    def group_summary(items):
        return dict(cases=len(items),modern_report_kg_yr=stats([c['lanes']['modern']['report_kg_yr'] for c in items]),legacy_report_kg_yr=stats([c['lanes']['legacy']['report_kg_yr'] for c in items]),
          modern_lower_fill_supply=sum(c['paired_annual']['sediment_out_kg']['fill']<0 for c in items),modern_higher_outlet=sum(c['paired_annual']['sediment_out_kg']['buffer']>0 for c in items),modern_lower_fill_higher_outlet=sum(c['paired_annual']['sediment_out_kg']['fill']<0 and c['paired_annual']['sediment_out_kg']['buffer']>0 for c in items),
          median_paired_sediment_change_kg_yr={role:stats([c['paired_annual']['sediment_out_kg'][role] for c in items]) for role in ledger.ROLES},
          median_paired_surface_volume_change_m3_yr={role:stats([c['paired_annual']['surface_out_m3'][role] for c in items]) for role in ledger.ROLES},
          cases_with_lower_inflow_higher_outflow_events=sum(c['events']['lower_inflow_higher_outflow_days']>0 for c in items),
          lower_inflow_higher_outflow_events=sum(c['events']['lower_inflow_higher_outflow_days'] for c in items),
          printing_separated_lower_inflow_higher_outflow_events=sum(c['events']['printing_separated_lower_inflow_higher_outflow_days'] for c in items),
          printing_separated_excess_kg=sum(c['events']['printing_separated_excess_kg'] for c in items),
          lower_inflow_higher_outflow_excess_kg=sum(c['events']['lower_inflow_higher_outflow_excess_kg'] for c in items),
          matched_element_difference_kg=sum(c['events']['matched_element_difference_kg'] for c in items),
          modern_only_reported_sediment_kg=sum(c['events']['modern_only_reported_sediment_kg'] for c in items),legacy_only_reported_sediment_kg=sum(c['events']['legacy_only_reported_sediment_kg'] for c in items),
          terminal_clay_mass_fraction={'modern':stats([c['events']['modern_terminal_clay_mass_fraction'] for c in items]),'legacy':stats([c['events']['legacy_terminal_clay_mass_fraction'] for c in items])})
    groups={g:group_summary([c for c in cases if c['group']==g]) for g in sorted({c['group'] for c in cases})}
    strata={field:{str(v):group_summary([c for c in cases if c[field]==v]) for v in sorted({c[field] for c in cases})} for field in ledger.KEYS}
    top=records(con,'''SELECT case_id,original_group,year,julian,date,legacy_sediment_in_kg,modern_sediment_in_kg,legacy_sediment_out_kg,modern_sediment_out_kg,legacy_surface_in_m3,modern_surface_in_m3,legacy_surface_out_m3,modern_surface_out_m3,legacy_keff_mm_h,modern_keff_mm_h,legacy_ki_si_kg_s_m4,modern_ki_si_kg_s_m4,legacy_kr_si_s_m,modern_kr_si_s_m,sediment_observation_support,delta_reported_sediment_out_kg FROM terminal QUALIFY row_number() OVER(PARTITION BY case_id ORDER BY delta_reported_sediment_out_kg DESC,year,julian)<=3 ORDER BY case_id,delta_reported_sediment_out_kg DESC''')
    for r in top:r['date']=r['date'].isoformat()
    gaps=con.execute('''SELECT * FROM daily WHERE (NOT legacy_element_present AND legacy_surface_out_m3>0) OR (NOT modern_element_present AND modern_surface_out_m3>0) OR (legacy_sediment_out_kg>0 AND legacy_surface_out_m3=0) OR (modern_sediment_out_kg>0 AND modern_surface_out_m3=0)''').fetch_arrow_table()
    ledger.write_table(gaps,ROOT/'undefined-or-unobserved-flux-days.parquet',sha(ROOT/'declaration.json'))
    save(ROOT/'case-summary.json',cases);save(ROOT/'top-discrepancy-events.json',top)
    summary=dict(status='Paired observational accounting only; no parameter acceptance.',dimensions=dimensions,source_records_rehashed=source_checks,output_artifacts_rehashed=output_checks,annual_accepted_audits_replayed_exactly=annual_checks,annual_reported_difference_decompositions_reconciled=116,particle_events=particle_events,strict_particle_flags=particle_flags,unavailable_element_diagnostics=len(unavailable),unavailable_by_field=dict(Counter(x['field']['column'] for x in unavailable)),undefined_or_unobserved_flux_days=gaps.num_rows,groups=groups,strata=strata,observation_support=support,script_sha256=sha(__file__),declaration_sha256=sha(ROOT/'declaration.json'),results_sha256=sha(ROOT/'results.json'),case_summary_sha256=sha(ROOT/'case-summary.json'),top_events_sha256=sha(ROOT/'top-discrepancy-events.json'),external_corrected_particle_receipt_sha256=sha(ledger.ART/'particle-audit-v2-reverification.json'),limitations=['Different complete profiles and format-specific state; no single-parameter causal attribution.','Net exchange is not tagged origin or gross erosion/deposition.','Missing ELEMENT observations are NULL; reported-row differences use explicit bookkeeping zeros only.','Terminal class fractions do not identify upstream class delivery or per-OFE particle provenance.','21 distinct legacy decks recur across116cases; no independent-material inference.','No WEPP2010 event data, withheld materials or new native executions.'])
    save(ROOT/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('groups','strata','observation_support','strict_particle_flags','limitations')},indent=2),flush=True)
    print('Small-reference group:',json.dumps(groups['small_exceedance'],indent=2),flush=True)

if __name__=='__main__':main()
