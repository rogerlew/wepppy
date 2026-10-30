"""Portable evidence, independent aggregation and figures for the buffer study."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import experiment as e


def summarize(root):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import duckdb
    src=root/'reconciliation-v2';dest=Path(__file__).parent
    for name in ('results.json','upstream-coupling.json','same-grid-controls.json','legacy-reference-provenance.json','partial-analysis-hashes.json','acceptance.json'):
        shutil.copyfile(src/name,dest/name)
    shutil.copyfile(root/'declaration.json',dest/'declaration.json')
    results=json.loads((src/'results.json').read_text())
    with (dest/'summary.csv').open('w') as stream:
        fields=['profile','drainage','depth_offset_mm','kslast_mm_h','computational_depth_mm','report_export_kg_yr','ratio_to_2010','late_export_kg_yr','buffer_net_sediment_kg_yr','buffer_surface_in_m3_yr','buffer_surface_out_m3_yr','buffer_deep_percolation_m3_yr','buffer_lateral_out_m3_yr','near_capacity_days','upstream_output_exact']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for r in results:
            q=r['record'];w=r['water']['ofes'][2]
            writer.writerow(dict(profile=q['profile'],drainage=q['drainage'],depth_offset_mm=e.OFFSETS[q['depth']],kslast_mm_h=q['conductivity_mm_h'],
                                 computational_depth_mm=r['state']['profile_depth_mm'],report_export_kg_yr=q['metrics']['sediment_export_kg_yr'],ratio_to_2010=r['ratio_to_2010'],
                                 late_export_kg_yr=r['late_export_kg_yr'],buffer_net_sediment_kg_yr=r['sediment']['ofes'][2]['net_kg_yr'],
                                 buffer_surface_in_m3_yr=w['surface_in_m3_yr'],buffer_surface_out_m3_yr=w['surface_out_m3_yr'],buffer_deep_percolation_m3_yr=w['deep_percolation_m3_yr'],
                                 buffer_lateral_out_m3_yr=w['lateral_out_m3_yr'],near_capacity_days=r['state']['days_at_90pct_capacity'],upstream_output_exact=r['upstream_exact']))
    # Reaggregate boundary sediment and surface/deep water with an independent query.
    checks=[];con=duckdb.connect()
    for r in results:
        q=r['record'];folder=root/'runs'/q['name']
        prior=json.loads((root/'inputs'/q['profile']/'prior-record.json').read_text())
        slope=[l for l in (folder/'runs/p1.slp').read_text().splitlines() if l and not l.startswith('#')]
        areas=[prior['width_m']*float(slope[i].split()[1]) for i in (3,5,7)]
        rows=con.execute('SELECT OFE,sum(SedLeave) FROM read_parquet(?) GROUP BY OFE ORDER BY OFE',[str(folder/'output/interchange/H.element.parquet')]).fetchall()
        if [v[0] for v in rows]!=[1,2,3]:raise ValueError('SQL OFE coverage')
        for (i,v),o in zip(rows,r['sediment']['ofes']):
            if abs(v*prior['width_m']/16-o['boundary_kg_yr'])>1e-8:raise ValueError('SQL sediment mismatch')
        rows=con.execute('SELECT OFE,sum(Q),sum(Dp) FROM read_parquet(?) GROUP BY OFE ORDER BY OFE',[str(folder/'output/interchange/H.wat.parquet')]).fetchall()
        for (i,qv,dp),o in zip(rows,r['water']['ofes']):
            if abs(qv*sum(areas[:i])/16000-o['surface_out_m3_yr'])>1e-8 or abs(dp*areas[i-1]/16000-o['deep_percolation_m3_yr'])>1e-8:
                raise ValueError('SQL water mismatch')
        checks.append(dict(name=q['name'],independent_aggregation=True))
    con.close();e.a.dump(dest/'independent-reaggregation.json',checks)
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    titles=['Site sand / unrutted','Site clay / unrutted','Birmingham clay / unrutted','Denver loam / rutted']
    for ax,profile,title in zip(axes.flat,e.PANEL,titles):
        for drainage,color,label in [('current','#D55E00','Current drainage proxy'),('source','#0072B2','Source-based drainage')]:
            selected=[next(r for r in results if r['record']['profile']==profile and r['record']['drainage']==drainage and r['record']['depth']==d) for d in e.OFFSETS]
            ax.plot([-1,0,1],[r['record']['metrics']['sediment_export_kg_yr'] for r in selected],'o-',color=color,label=label)
        ax.axhline(selected[0]['legacy_export_kg_yr'],color='gray',linestyle='--',label='WEPP2010 reference')
        ax.set_title(title);ax.set_xticks([-1,0,1]);ax.set_ylim(bottom=0);ax.grid(alpha=.2)
        ax.set_xlabel('Buffer input bottom-depth offset (mm)');ax.set_ylabel('Report sediment export (kg/year)')
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3)
    fig.suptitle('Buffer drainage dominates the two selected high-export cases')
    fig.savefig(dest/'drainage-depth-response.png',dpi=160)
    hashes={p.name:e.a.digest(p) for p in dest.iterdir() if p.is_file() and p.name not in ('portable-sha256.json','validation.md')}
    e.a.dump(dest/'portable-sha256.json',hashes)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();summarize(args.root)
