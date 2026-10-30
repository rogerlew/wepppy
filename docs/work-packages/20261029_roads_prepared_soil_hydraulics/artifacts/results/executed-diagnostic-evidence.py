"""Publish diagnostic figures and prove physical equivalence of subdivision inputs."""
from pathlib import Path
import argparse
import csv
import json
import experiment as e
b=e.b


def audit(root,dest):
    records=[]
    for values in e.PANEL:
        stem='-'.join(values)+'-modern-'
        raw=json.loads((root/'diagnostic-v1'/(stem+'raw')/'record.json').read_text())
        split=json.loads((root/'subdivision-v1'/(stem+'split_all')/'record.json').read_text())
        paths=[]
        for index,(original,divided) in enumerate(zip(raw['soil_readback']['ofes'],split['soil_readback']['ofes'])):
            meta=lambda o:{k:v for k,v in o.items() if k not in ('nsl','horizons')}
            if meta(original)!=meta(divided):raise ValueError('Non-layer parameters changed')
            depths=sorted({0.0}|{h['solthk'] for o in (original,divided) for h in o['horizons']})
            intervals=[]
            for start,end in zip(depths,depths[1:]):
                point=(start+end)/2
                layers=[next(h for h in o['horizons'] if h['solthk']>=point) for o in (original,divided)]
                properties=[{k:v for k,v in h.items() if k!='solthk'} for h in layers]
                if properties[0]!=properties[1]:raise ValueError('Subdivision changed material properties')
                intervals.append({'top_mm':start,'bottom_mm':end,'properties':properties[0]})
            paths.append({'ofe':index+1,'equivalent_intervals':intervals})
        records.append({'case':stem,'original_soil_sha256':raw['inputs']['p1.sol'],
                        'split_soil_sha256':split['inputs']['p1.sol'],'equivalence':paths})
    b.dump(dest/'subdivision-equivalence.json',records)


def plot(root,dest):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows=list(csv.DictReader((root/'diagnostic-analysis-v1/comparisons.csv').open()))
    subdivision=list(csv.DictReader((root/'subdivision-analysis-v1/comparisons.csv').open()))
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    variants=['raw','roles','roles_fixed','layer200_k3','roles_fixed_erosion']
    labels=['Site / sandy loam','Birmingham / clay loam','Denver / loam','Birmingham / loam','Charleston / silt loam']
    for variant in variants:
        selected=[next(r for r in rows if r['variant']==variant and
                  tuple(r[k] for k in ('climate','soil','design','surface','traffic'))==case) for case in e.PANEL]
        ratios=[float(r['ratio_sediment_export_kg_yr']) for r in selected]
        axes[0].plot(range(len(ratios)),[v if v>0 else float('nan') for v in ratios],marker='o',label=variant)
    axes[0].annotate('raw, fixed, erosion = 0',(2,0.033),ha='center',fontsize=7)
    axes[0].axhspan(.1,10,color='gray',alpha=.15)
    axes[0].axhline(1,color='black',linewidth=.7)
    axes[0].set_yscale('log');axes[0].set_ylim(.025,300)
    axes[0].set_xticks(range(5),labels,rotation=35,ha='right')
    axes[0].set_ylabel('Export / WEPP2010 reference (zero labeled explicitly)')
    axes[0].set_title('Diagnostic panel: no treatment passes all five')
    axes[0].legend(fontsize=8)
    chosen=['format_unsplit','split_road','split_fill','split_buffer','split_all']
    values=[float(next(r for r in subdivision if r['climate']=='site' and r['variant']==v)['sediment_export_kg_yr']) for v in chosen]
    axes[1].bar(range(5),values,color=['#507c96']+['#b77b45']*4)
    axes[1].set_xticks(range(5),['Unsplit 9002','Split road','Split fill','Split buffer','Split all'],rotation=35,ha='right')
    axes[1].set_ylabel('Sediment leaving profile (kg/year)')
    axes[1].set_title('Equivalent soil properties; different subdivision')
    for i,v in enumerate(values):axes[1].text(i,v+70,f'{v:,.0f}',ha='center',fontsize=9)
    fig.savefig(dest/'diagnostics.png',dpi=180)
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=e.ROOT)
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args();args.destination.mkdir(parents=True,exist_ok=False)
    audit(args.root,args.destination);plot(args.root,args.destination)
