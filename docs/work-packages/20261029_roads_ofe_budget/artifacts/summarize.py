"""Reproduce portable tables, evidence and the report figure from retained runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(root, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import duckdb
    import pyarrow.parquet as pq
    from wepppy.wepp.soils.utils import WeppSoilUtil

    analysis=root/'analysis-v3'
    records=json.loads((root/'factorial-v1/summary.json').read_text())
    results=json.loads((analysis/'results.json').read_text())
    effects=json.loads((analysis/'effects.json').read_text())
    for name in ('results.json','effects.json','acceptance.json','provenance.json'):
        shutil.copyfile(analysis/name,destination/name)
    shutil.copyfile(root/'declaration.json',destination/'declaration.json')
    evidence=[{k:r[k] for k in ('name','case','binary','inputs','outputs','wat_rows','status')} for r in records]
    (destination/'run-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    prior=Path('/wc1/runs/ro/roads-prepared-soil-hydraulics-20261029/confirmation-v1')
    reproduction=[]
    for r in records:
        if r['case']['variant']!='111':continue
        folder=prior/(r['name'][:-3]+'roles')
        old=json.loads((folder/'record.json').read_text())
        files=sorted(set(r['outputs']) & set(old['outputs']))
        if r['metrics']!=old['metrics']:
            raise ValueError('Roles endpoint failed reproduction')
        for name in files:
            if digest(folder/'output'/name)!=old['outputs'][name] or old['outputs'][name]!=r['outputs'][name]:
                raise ValueError('Native output reproduction failed')
        reproduction.append(dict(name=r['name'],prior_record=str(folder/'record.json'),prior_record_sha256=digest(folder/'record.json'),identical_outputs=files,metrics_equal=True))
    (destination/'prior-reproduction.json').write_text(json.dumps(reproduction,indent=2)+'\n')
    with (destination/'summary.csv').open('w') as stream:
        fields=['name','binary','variant','report_export_kg_yr','ratio_to_2010','report_reconciled']
        fields += [role+'_'+metric for role in ('road','fill','buffer') for metric in ('boundary_kg_yr','net_kg_yr','surface_out_m3_yr')]
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for r in results:
            row=dict(name=r['name'],binary=r['case']['binary'],variant=r['case']['variant'],report_export_kg_yr=r['metrics']['sediment_export_kg_yr'],ratio_to_2010=r.get('report_ratio_to_2010'),report_reconciled=r.get('sediment',{}).get('report_reconciled'))
            if 'sediment'in r:
                for i,role in enumerate(('road','fill','buffer')):
                    for metric in ('boundary_kg_yr','net_kg_yr'):
                        row[role+'_'+metric]=r['sediment']['ofes'][i][metric]
                    row[role+'_surface_out_m3_yr']=r['water']['ofes'][i]['surface_out_m3_yr']
            writer.writerow(row)
    panel=[e['profile'] for e in effects]
    labels=['Site sand\nunrutted','Site clay\nunrutted','Birmingham clay\nunrutted','Site sand\nrutted','Denver loam\nrutted','Charleston silt\ninsloped']
    selected=[next(r for r in results if r['name']==p+'-modern-111') for p in panel]
    # Independent aggregation checks use the persisted Rust-reader tables.
    reaggregated=[]
    for result in selected:
        folder=root/'factorial-v1'/result['name']
        record=next(r for r in records if r['name']==result['name'])
        element=str(folder/'output/interchange/H.element.parquet')
        water=str(folder/'output/interchange/H.wat.parquet')
        con=duckdb.connect()
        values=con.execute('SELECT OFE, sum(SedLeave) FROM read_parquet(?) GROUP BY OFE ORDER BY OFE',[element]).fetchall()
        if [v[0] for v in values] != [1,2,3]:
            raise ValueError('Independent sediment OFE coverage mismatch')
        for (i,v),expected in zip(values,result['sediment']['ofes']):
            if abs(v*record['width_m']/16-expected['boundary_kg_yr'])>1e-8:
                raise ValueError('Independent sediment aggregation mismatch')
        values=con.execute('SELECT OFE, sum(Q), sum(Dp) FROM read_parquet(?) GROUP BY OFE ORDER BY OFE',[water]).fetchall()
        con.close()
        if [v[0] for v in values] != [1,2,3]:
            raise ValueError('Independent water OFE coverage mismatch')
        for (i,q,dp),expected in zip(values,result['water']['ofes']):
            if abs(q*sum(result['areas_m2'][:i])/16000-expected['surface_out_m3_yr'])>1e-8 or abs(dp*result['areas_m2'][i-1]/16000-expected['deep_percolation_m3_yr'])>1e-8:
                raise ValueError('Independent water aggregation mismatch')
        reaggregated.append(dict(name=result['name'],sediment_and_water_sql_reaggregation=True))
    (destination/'independent-reaggregation.json').write_text(json.dumps(reaggregated,indent=2)+'\n')
    depths=[]
    for soil in ('sand','clay'):
        for variant in ('111','legacy'):
            name=f'site-{soil}-outunrut-'+('gravel' if soil=='sand' else 'paved')+f'-high-modern-{variant}'
            folder=root/'factorial-v1'/name
            ofes=WeppSoilUtil(str(folder/'runs/p1.sol')).obj['ofes']
            rows=pq.read_table(folder/'output/interchange/H.wat.parquet',columns=['OFE','ProfileDepth']).to_pylist()
            depths.append(dict(name=name,input_bottom_mm=[o['horizons'][-1]['solthk'] for o in ofes],reported_depths_mm={i:sorted({r['ProfileDepth'] for r in rows if r['OFE']==i}) for i in (1,2,3)}))
    (destination/'profile-depth-audit.json').write_text(json.dumps(depths,indent=2)+'\n')
    fig,axes=plt.subplots(2,1,figsize=(11,8),layout='constrained')
    x=np.arange(6)
    axes[0].bar(x-.18,[e['legacy_2010_export_kg_yr'] for e in effects],.36,label='WEPP2010 / legacy soils',color='#666666')
    axes[0].bar(x+.18,[r['metrics']['sediment_export_kg_yr'] for r in selected],.36,label='WEPP261026 / conditioned generated soils (111)',color='#0072B2')
    axes[0].set_ylabel('Report sediment export (kg/year)');axes[0].legend(loc='upper right',fontsize=9)
    positive=np.zeros(6);negative=np.zeros(6)
    for i,(role,color) in enumerate(zip(('Road','Fill','Buffer'),('#0072B2','#E69F00','#009E73'))):
        values=np.array([r['sediment']['ofes'][i]['net_kg_yr'] for r in selected])
        axes[1].bar(x,values,bottom=np.where(values>=0,positive,negative),color=color,label=role)
        positive+=np.maximum(values,0);negative+=np.minimum(values,0)
    axes[1].axhline(0,color='black',linewidth=.7);axes[1].set_ylabel('ELEMENT signed net exchange (kg/year)')
    axes[1].legend(loc='upper right',fontsize=9)
    for ax in axes:ax.set_xticks(x,labels);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Roads element budgets: all hydraulic conditioning enabled (111)')
    fig.supxlabel('Net exchange is not gross detachment. Charleston boundary total exceeds report by 0.595 kg/year.',fontsize=9)
    fig.savefig(destination/'ofe-budgets.png',dpi=160)
    portable={p.name:digest(p) for p in destination.iterdir() if p.is_file() and p.name not in ('portable-sha256.json','validation.md')}
    (destination/'portable-sha256.json').write_text(json.dumps(portable,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--destination',type=Path,default=Path(__file__).parent)
    args=parser.parse_args();summarize(args.root,args.destination)
