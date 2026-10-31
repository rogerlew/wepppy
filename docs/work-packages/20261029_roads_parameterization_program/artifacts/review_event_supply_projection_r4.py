"""Independent summary annualization and original legacy-soil retention checks."""
from pathlib import Path
import argparse
import hashlib
import json

FLUX={'sediment_out_kg','net_sediment_kg','positive_net_kg','negative_net_kg',
      'surface_out_m3','surface_in_m3','lateral_out_m3','lateral_in_m3',
      'precipitation_m3','rain_melt_m3','et_m3','deep_percolation_m3'}

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    cases={r['case_id']:r for r in read(a.root/'case-summary.json')}
    index=read(a.root/'results.json');assert len(index)==len(cases)==116
    count=0;paved=[];soils=set();formats=set();originals=[]
    for item in index:
        r=read(item['receipt']);c=cases[item['case_id']]
        for lane in ['legacy','modern']:
            for old,new in zip(r['lanes'][lane]['annual'],c['lanes'][lane]['ofes']):
                assert set(old)==set(new)
                for k,v in old.items():assert new[k]==(v/c['years'] if k in FLUX else v);count+=1
        if c['surface']=='paved':paved.append(dict(case_id=c['case_id'],legacy_road_kg_yr=c['lanes']['legacy']['ofes'][0]['sediment_out_kg'],modern_road_kg_yr=c['lanes']['modern']['ofes'][0]['sediment_out_kg']))
        native=read(r['task']['records']['legacy']['path']);current=Path(native['folder'])/'runs/p1.sol';original=Path(native['source'])/'runs/p1.sol'
        digest=sha(current);assert digest==sha(original)==native['inputs']['p1.sol']
        fmt=next(line.strip() for line in current.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))
        formats.add(fmt);soils.add(digest);originals.append(dict(current=str(current),original=str(original),sha256=digest))
    assert formats=={'98.4'} and len(soils)==21
    result=dict(annual_projection_exact=True,values_checked=count,annualized_fields=sorted(FLUX),
        paved_cases=paved,paved_road_exports_all_exactly_zero=all(r['legacy_road_kg_yr']==r['modern_road_kg_yr']==0 for r in paved),
        original_legacy_soils_byte_exact=116,distinct_legacy_soils=21,legacy_soil_formats=sorted(formats),original_soil_provenance=originals,
        case_summary_sha256=sha(a.root/'case-summary.json'),script_sha256=sha(__file__))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['paved_cases','original_soil_provenance']}))

if __name__=='__main__':main()
