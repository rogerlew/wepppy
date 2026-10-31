"""Retain residual net exchanges and component-lane set comparisons."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/road-pore-screen-r3')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(row):return tuple(row['case'][k] for k in ('climate','soil','design','surface','traffic'))
def main():
    rows=json.loads((ROOT/'results.json').read_text())
    remaining=[r for r in rows if r['lane']=='coupled' and r['group']=='small_exceedance' and not r['within']]
    coupled={key(r) for r in rows if r['lane']=='coupled' and r['within']}
    conductivity={key(r) for r in rows if r['lane']=='conductivity' and r['within']}
    result=dict(remaining_small_cases=len(remaining),positive_net_buffer=sum(r['audit']['sediment']['ofes'][2]['net_kg_yr']>0 for r in remaining),
        positive_net_fill=sum(r['audit']['sediment']['ofes'][1]['net_kg_yr']>0 for r in remaining),
        zero_road_boundary=sum(r['audit']['sediment']['ofes'][0]['boundary_kg_yr']==0 for r in remaining),
        coupled_gains_over_conductivity=sorted(coupled-conductivity),coupled_losses_to_conductivity=sorted(conductivity-coupled),
        rows=[dict(case=r['case'],reference_kg_yr=r['reference_kg_yr'],export_kg_yr=r['export_kg_yr'],ofes=r['audit']['sediment']['ofes']) for r in remaining],
        limitation='Annual net exchange is not tagged particle origin or a causal attribution; negative annual buffer exchange can include individual source events.',
        source_results_sha256=sha(ROOT/'results.json'),script_sha256=sha(Path(__file__)))
    text=json.dumps(result,indent=2)+'\n';(ROOT/'residuals.json').write_text(text);(HERE/'road-pore-screen-r3-residuals.json').write_text(text)
    print('Residual and component-lane sets recorded')
if __name__=='__main__':main()
