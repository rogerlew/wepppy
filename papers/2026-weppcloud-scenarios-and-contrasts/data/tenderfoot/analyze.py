"""Reproduce Tenderfoot scenario/contrast tables and figures from a frozen snapshot.

Run with the repository .venv Python. Positive deltas mean treatment minus baseline.
No production code or run artifacts are modified. Missing/inconsistent inputs fail.
"""
from pathlib import Path
import hashlib
import json
import platform
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RAW = HERE / 'raw'
OUT = HERE / 'results'
SCENARIOS = ['undisturbed', 'thinning_30_75', 'thinning_65_90']
KEYS = {
    'area_ha': 'Total contributing area to outlet',
    'precip_m3_yr': 'Avg. Ann. Precipitation volume in contributing area',
    'water_m3_yr': 'Avg. Ann. water discharge from outlet',
    'hillslope_loss_t_yr': 'Avg. Ann. total hillslope soil loss',
    'channel_loss_t_yr': 'Avg. Ann. total channel soil loss',
    'outlet_sediment_t_yr': 'Avg. Ann. sediment discharge from outlet',
}
ANNUAL = {
    'Total water discharge from outlet': 'water_m3',
    'Total sediment discharge from outlet': 'outlet_sediment_t',
    'Total hillslope soil loss in contributing area': 'hillslope_loss_t',
    'Total channel soil loss': 'channel_loss_t',
}

def runpath(name):
    if name == 'undisturbed':
        return RAW
    if isinstance(name, int):
        return RAW / '_pups/omni/contrasts' / str(name)
    return RAW / '_pups/omni/scenarios' / name


def table(name, filename):
    return pd.read_parquet(runpath(name) / 'wepp/output/interchange' / filename)


def metrics(name):
    d = table(name, 'loss_pw0.out.parquet')
    assert not d.key.duplicated().any()
    return d.set_index('key').value


def annual(name):
    d = table(name, 'loss_pw0.all_years.out.parquet')
    d = d[d.key.isin(ANNUAL)].pivot(index='year', columns='key', values='value').rename(columns=ANNUAL)
    assert list(d.index) == list(range(1, 101)) and not d.isna().any().any()
    return d


def main():
    OUT.mkdir(exist_ok=True)
    manifest = json.loads((HERE/'snapshot_manifest.json').read_text())
    for entry in manifest['files']:
        assert hashlib.sha256((RAW/entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']
    omni = json.loads((RAW/'omni.nodb').read_text())['py/state']
    checks = {'snapshot_files_verified': len(manifest['files']), 'dependency_hashes_verified': 0}
    for dep in omni['_contrast_dependency_tree'].values():
        for source in dep['dependencies'].values():
            path = RAW / source['loss_path'].split('/animal-misgiving/',1)[1]
            assert hashlib.sha1(path.read_bytes()).hexdigest() == source['sha1']
            checks['dependency_hashes_verified'] += 1
    hills = pd.read_parquet(RAW/'omni/scenarios.hillslope_summaries.parquet')
    h = {s: hills[hills.scenario==s].set_index('Topaz ID').sort_index() for s in SCENARIOS}
    base = metrics('undisturbed')
    baseannual = annual('undisturbed')
    area = h['undisturbed']['Landuse Area (ha)'].sum()
    combined = pd.read_parquet(RAW/'omni/scenarios.out.parquet')
    scenario_rows, annual_rows = [], []
    for s in SCENARIOS:
        m = metrics(s)
        np.testing.assert_allclose(combined[combined.scenario==s].set_index('key').value.reindex(m.index), m)
        np.testing.assert_allclose(h[s]['Landuse Area (ha)'], h['undisturbed']['Landuse Area (ha)'])
        assert h[s].index.equals(h['undisturbed'].index)
        row = {'scenario':s, **{k:float(m[v]) for k,v in KEYS.items()}}
        row['hillslope_area_ha'] = area
        row['hillslope_loss_t_yr'] = h[s]['Soil Loss (kg/yr)'].sum()/1000
        row['hillslope_delivery_t_yr'] = h[s]['Sediment Yield (kg/yr)'].sum()/1000
        row['hillslope_loss_t_ha_yr'] = row['hillslope_loss_t_yr']/area
        row['outlet_sediment_t_ha_yr'] = row['outlet_sediment_t_yr']/row['area_ha']
        row['water_mm_yr'] = row['water_m3_yr']/row['area_ha']/10
        row['precip_mm_yr'] = row['precip_m3_yr']/row['area_ha']/10
        for col in ['Runoff (m^3)','Lateral Flow (m^3)','Baseflow (m^3)']:
            row[col] = h[s][col].sum()
        scenario_rows.append(row)
        a = annual(s)
        for ac, mc in [('water_m3','water_m3_yr'),('outlet_sediment_t','outlet_sediment_t_yr'),('channel_loss_t','channel_loss_t_yr'),('hillslope_loss_t','hillslope_loss_t_yr')]:
            assert np.isclose(a[ac].mean(),row[mc],rtol=.001,atol=.11), (s,ac)
        e = table(s,'ebe_pw0.parquet')
        assert e.simulation_year.nunique() == 100
        # Retain all records for totals; duplicate labels prohibit daily-date analyses.
        checks[s+'_event_day_index_duplicates'] = int(e.sim_day_index.duplicated().sum())
        assert np.isclose(e.runoff_volume.sum()/100,row['water_m3_yr'],rtol=1e-5)
        assert np.isclose(e.sediment_yield.sum()/100/1000,row['outlet_sediment_t_yr'],atol=.1)
        annual_rows.append(a.assign(scenario=s).reset_index())
    scenarios=pd.DataFrame(scenario_rows).set_index('scenario')
    for col in ['water_m3_yr','hillslope_loss_t_yr','outlet_sediment_t_yr','channel_loss_t_yr']:
        scenarios[col+'_change_pct']=(scenarios[col]/scenarios.loc['undisturbed',col]-1)*100
    scenarios.to_csv(OUT/'scenarios.csv')
    pd.concat(annual_rows).to_csv(OUT/'scenario_annual.csv',index=False)
    definitions={}
    for line in (RAW/'omni/contrast_id_definitions.psv').read_text().splitlines():
        cid, ids=line.split('|'); definitions[int(cid)] = set(map(int,ids.split(',')))
    assert len(definitions)==36
    cexport=pd.read_parquet(RAW/'omni/contrasts.out.parquet')
    rows=[]; crannual=[]; issues=[]; memberships=[]
    for cid,selected in sorted(definitions.items()):
        name=omni['_contrast_names'][cid-1]
        dep = omni['_contrast_dependency_tree'][name]
        sidecar_path = RAW/f'omni/contrasts/contrast_{cid:05d}.tsv'
        assert hashlib.sha1(sidecar_path.read_bytes()).hexdigest() == dep['sidecar_sha1']
        s=name.split('__to__')[1]
        group=(cid+1)//2
        assert definitions[2*group-1]==definitions[2*group]
        assert selected <= set(h[s].index)
        sidecar=pd.read_csv(RAW/f'omni/contrasts/contrast_{cid:05d}.tsv',sep='\t',header=None,names=['topaz','path'])
        assert len(sidecar)==len(h[s]) and not sidecar.topaz.duplicated().any()
        actual=set(sidecar.loc[sidecar.path.str.contains('/scenarios/'+s+'/'), 'topaz'])
        assert actual==selected, cid
        status=json.loads((RAW/f'omni/contrasts/contrast_{cid:05d}.status.json').read_text())
        assert status['status']=='completed'
        m=metrics(cid)
        ex=cexport[cexport.contrast_id==cid].set_index('key')
        np.testing.assert_allclose(ex.value.reindex(m.index),m)
        bad=ex[~np.isclose(ex.control_v,base.reindex(ex.index),rtol=1e-10,atol=1e-8)]
        for key,r in bad.iterrows():
            issues.append({'contrast_id':cid,'key':key,'export_control':r.control_v,'baseline_control':base[key]})
        ids=sorted(selected)
        treated=[i for i in ids if h[s].loc[i,'Landuse Key'] != h['undisturbed'].loc[i,'Landuse Key']]
        row={'contrast_id':cid,'group':group,'scenario':s,'selected_hillslopes':len(ids),
             'treated_hillslopes':len(treated),'selected_area_ha':h[s].loc[ids,'Landuse Area (ha)'].sum(),
             'treated_area_ha':h[s].loc[treated,'Landuse Area (ha)'].sum()}
        for i in ids: memberships.append({'contrast_id':cid,'group':group,'scenario':s,'topaz_id':i,'treatment_changed':i in treated})
        for key,col in KEYS.items():
            row[key]=m[col]; row['delta_'+key]=m[col]-base[col]
        for source,dest in [('Soil Loss (kg/yr)','local_hillslope_loss_t_yr'),('Sediment Yield (kg/yr)','local_hillslope_delivery_t_yr')]:
            row['delta_'+dest]=(h[s].loc[ids,source]-h['undisturbed'].loc[ids,source]).sum()/1000
        # Independent reconstruction of mixed hillslope mass from source scenarios.
        expected=h['undisturbed']['Soil Loss (kg/yr)'].sum()/1000+row['delta_local_hillslope_loss_t_yr']
        assert np.isclose(m[KEYS['hillslope_loss_t_yr']],expected,atol=.12,rtol=0), (cid,expected)
        for metric in ['outlet_sediment_t_yr','water_m3_yr']:
            row['delta_'+metric+'_per_treated_ha']=row['delta_'+metric]/row['treated_area_ha']
        a=annual(cid)
        delta=a-baseannual
        for col in ['water_m3','outlet_sediment_t']:
            row[col+'_annual_increase_years']=int((delta[col]>0).sum())
            row[col+'_annual_delta_median']=delta[col].median()
            row[col+'_annual_delta_p05']=delta[col].quantile(.05)
            row[col+'_annual_delta_p95']=delta[col].quantile(.95)
        for ac,mc in [('water_m3','water_m3_yr'),('outlet_sediment_t','outlet_sediment_t_yr')]:
            assert np.isclose(a[ac].mean(),row[mc],rtol=.001,atol=.11)
        crannual.append(delta.add_prefix('delta_').assign(contrast_id=cid,group=group,scenario=s).reset_index())
        rows.append(row)
    contrasts=pd.DataFrame(rows)
    contrasts.to_csv(OUT/'contrasts.csv',index=False)
    pd.concat(crannual).to_csv(OUT/'contrast_annual_deltas.csv',index=False)
    pd.DataFrame(memberships).to_csv(OUT/'group_membership.csv',index=False)
    pd.DataFrame(issues).to_csv(OUT/'export_control_mismatches.csv',index=False)
    # Check whether isolated groups form a partition before evaluating additivity.
    groups=[definitions[c] for c in range(1,37,2)]
    assert sum(map(len,groups))==len(set.union(*groups))==len(h['undisturbed'])
    assert set.union(*groups)==set(h['undisturbed'].index)
    checks.update({'groups':18,'contrasts':36,'partition_hillslopes':len(h['undisturbed']),
                   'export_control_mismatches':len(issues), 'years':100,
                   'python':platform.python_version(),'pandas':pd.__version__, 'numpy':np.__version__,
                   'matplotlib':matplotlib.__version__})
    (OUT/'validation.json').write_text(json.dumps(checks,indent=2)+'\n')
    add=[]
    for s in SCENARIOS[1:]:
        for metric in ['water_m3_yr','outlet_sediment_t_yr','channel_loss_t_yr','hillslope_loss_t_yr']:
            delta_col = 'delta_local_hillslope_loss_t_yr' if metric == 'hillslope_loss_t_yr' else 'delta_'+metric
            isolated=contrasts.loc[contrasts.scenario==s,delta_col].sum()
            whole=scenarios.loc[s,metric]-scenarios.loc['undisturbed',metric]
            add.append({'scenario':s,'metric':metric,'sum_isolated_deltas':isolated,'whole_scenario_delta':whole,
                        'sum_minus_whole':isolated-whole,'sum_over_whole':isolated/whole})
    pd.DataFrame(add).to_csv(OUT/'additivity.csv',index=False)
    diagnostics=[]
    for s in SCENARIOS[1:]:
        d=contrasts[contrasts.scenario==s]
        delta=annual(s)-baseannual
        diagnostics.append({'scenario':s,
            'local_delivery_outlet_spearman':float(d.delta_local_hillslope_delivery_t_yr.rank().corr(d.delta_outlet_sediment_t_yr.rank())),
            'sediment_increase_years':int((delta.outlet_sediment_t>0).sum()),
            'water_increase_years':int((delta.water_m3>0).sum()),
            'annual_sediment_delta_median_t':float(delta.outlet_sediment_t.median()),
            'annual_sediment_delta_p05_t':float(delta.outlet_sediment_t.quantile(.05)),
            'annual_sediment_delta_p95_t':float(delta.outlet_sediment_t.quantile(.95))})
    pd.DataFrame(diagnostics).to_csv(OUT/'response_diagnostics.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(9,4),layout='constrained')
    addframe=pd.DataFrame(add)
    for ax,metric,scale,title in zip(axes,['water_m3_yr','outlet_sediment_t_yr'],[1e6,1],['Water increase (million m³/year)','Sediment increase (tonne/year)']):
        vals=addframe[addframe.metric==metric].set_index('scenario').loc[SCENARIOS[1:]]
        x=np.arange(2)
        ax.bar(x-.18,vals.whole_scenario_delta/scale,.36,label='Full scenario',color='#267eab')
        ax.bar(x+.18,vals.sum_isolated_deltas/scale,.36,label='Sum of isolated groups',color='#be5a22')
        ax.set_xticks(x,['30/75','65/90']);ax.set_xlabel('Canopy/ground cover (%)');ax.set_ylabel(title)
    axes[0].legend(fontsize=8)
    fig.savefig(OUT/'routing_nonadditivity.png',dpi=200);fig.savefig(OUT/'routing_nonadditivity.svg');plt.close(fig)
    # Figures show paired deterministic simulation responses, not confidence intervals.
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    colors=['#be5a22','#267eab']
    for s,color in zip(SCENARIOS[1:],colors):
        d=contrasts[contrasts.scenario==s]
        axes[0].plot(d.group,d.delta_outlet_sediment_t_yr,'o-',color=color,label=s.replace('thinning_','').replace('_','/'))
        axes[1].scatter(d.delta_local_hillslope_delivery_t_yr,d.delta_outlet_sediment_t_yr,color=color,label=s)
        for _,r in d[d.group.isin([1,6,12,16,17,18])].iterrows():
            axes[1].annotate(str(int(r.group)),(r.delta_local_hillslope_delivery_t_yr,r.delta_outlet_sediment_t_yr),fontsize=8,xytext=(3,3),textcoords='offset points')
    for ax in axes: ax.axhline(0,color='gray',lw=.7); ax.set_ylabel('Change in outlet sediment (tonne/year)');ax.grid(alpha=.2)
    axes[0].set_xlabel('Spatial group (analysis ID)');axes[0].set_xticks(range(1,19));axes[0].legend(title='Canopy/ground cover (%)')
    axes[1].set_xlabel('Change in hillslope sediment delivery (tonne/year)')
    fig.savefig(OUT/'contrast_location_response.png',dpi=200);fig.savefig(OUT/'contrast_location_response.svg');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(11,4),layout='constrained')
    for ax,col,label in zip(axes,['hillslope_loss_t_ha_yr','water_mm_yr','outlet_sediment_t_ha_yr'],['Hillslope soil loss\n(tonne/ha/year)','Outlet water\n(mm/year)','Outlet sediment\n(tonne/ha/year)']):
        ax.bar(['Baseline','30/75','65/90'],scenarios[col],color=['#686868']+colors);ax.set_ylabel(label)
    fig.savefig(OUT/'scenario_comparison.png',dpi=200);fig.savefig(OUT/'scenario_comparison.svg');plt.close(fig)
    print(scenarios[['hillslope_loss_t_ha_yr','water_mm_yr','outlet_sediment_t_yr']].to_string())
    print(pd.DataFrame(add).to_string(index=False))
    print(json.dumps(checks))

if __name__=='__main__':
    main()
