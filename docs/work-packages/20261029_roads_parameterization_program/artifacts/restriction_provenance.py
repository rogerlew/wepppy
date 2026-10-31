"""Trace frozen development headers, prepared boundaries and owned source code."""
from pathlib import Path
import json
import re
import hashlib
from wepppy.wepp.soils.utils import WeppSoilUtil

HERE=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    design=json.loads((HERE/'design-v2.json').read_text())
    rows=[]
    for item in design['development']:
        p=Path(item['path']); assert sha(p)==item['sha256']
        text=p.read_text(); soil=WeppSoilUtil(str(p)).obj['ofes'][0]
        index=re.search(r'#\s+res_lyr_i (\S+)',text).group(1)
        kind=re.search(r'#\s+type: (.*)',text).group(1).strip()
        match=re.search(r'#\s+ksat(?: \(um/s\))?: ([0-9.]+)',text)
        conductivity=float(match.group(1)) if match else None
        category='no_detected_horizon' if index=='None' else 'lithic_metadata' if kind=='Lithic bedrock' else 'mineral_low_conductivity'
        expected=.01 if index=='None' else round(conductivity*3.6/1000,5)
        assert soil['res_lyr']==dict(slflag=1,ui_bdrkth=10000.,kslast=expected)
        rows.append(dict(mukey=item['mukey'],source=str(p),sha256=sha(p),category=category,
                         restriction_index=index,restriction_kind=kind,source_restrictive_ksat_um_s=conductivity,
                         source_converted_mm_h=conductivity*3.6 if conductivity is not None else None,
                         profile_depth_mm=soil['horizons'][-1]['solthk'],boundary=soil['res_lyr'],
                         header=text[:text.index('Any comments:')],
                         caveat='Classification from retained generated header and builder algorithm; no independent geologic validation. N/A is not proof that no geologic restriction exists.'))
    sources={}
    for file in ('wepppy/soils/ssurgo/ssurgo.py','wepppy/soils/ssurgo/ssurgo.md',
                 '/workdir/wepppy/out/roads-parameterization-program-20261031/restriction-provenance-inputs/input.for',
                 '/workdir/wepppy/out/roads-parameterization-program-20261031/restriction-provenance-inputs/perc.for'):
        p=Path(file).resolve();sources[str(p)]=sha(p)
    result=dict(materials=rows,source_hashes=sources,script_sha256=sha(Path(__file__)),
                conclusion='Non-AG writer uses an enabled 10 m boundary for no-detected and detected restrictions. Detected classes use converted source Ksat /1000; no-detected uses 0.01 mm/h. Distinct mineral/lithic provenance is not consulted by the detector or writer branch. Profile truncation/padding is separate from 200 mm insertion; no changes made.')
    (HERE/'restriction-provenance-v1.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('mukey','category','profile_depth_mm','boundary')} for r in rows],indent=2))
if __name__=='__main__':main()
