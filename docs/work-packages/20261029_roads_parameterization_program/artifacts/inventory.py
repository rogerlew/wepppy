"""Inventory generated material profiles without reading model outcomes."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261029')
SOURCES=(Path('/wc1/runs/ad/addicted-reservist/soils'),Path('/wc1/runs/cl/clogging-starch/soils'))
USED={'1718465','2711184','2711250','1718510','2711195','1856573','53949','1718494'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from wepppy.wepp.soils.utils import WeppSoilUtil
    ROOT.mkdir(exist_ok=False)
    rows=[];rejected=[]
    for directory in SOURCES:
        for path in sorted(directory.glob('*.sol')):
            if not path.stem.isdigit():continue
            text=path.read_text()
            if not re.search(r'^#.*Source Data: Surgo',text,re.M):
                rejected.append(dict(path=str(path),reason='Not a provenance-bearing generated SSURGO specimen'))
                continue
            soil=WeppSoilUtil(str(path))
            if soil.datver!=7778 or len(soil.obj['ofes'])!=1:
                rejected.append(dict(path=str(path),reason='Outside declared single-OFE 7778 source scope'))
                continue
            ofe=soil.obj['ofes'][0]
            material={k:v for k,v in ofe.items() if k not in ('slid','texid')}
            signature=hashlib.sha256(json.dumps(material,sort_keys=True,allow_nan=False).encode()).hexdigest()
            block=text.split('# Restricting Layer:',1)[1].split('# defaults',1)[0]
            rows.append(dict(path=str(path),mukey=path.stem,sha256=digest(path),material_sha256=signature,
                previously_used_label=path.stem in USED,restriction_provenance=block.strip(),
                horizons=[dict(depth_mm=h['solthk'],ksat_mm_h=h['ksat'],sand=h['sand'],clay=h['clay']) for h in ofe['horizons']],
                current_boundary=ofe['res_lyr']))
    used_signatures={r['material_sha256'] for r in rows if r['previously_used_label']}
    for row in rows:row['material_seen_in_prior_studies']=row['material_sha256'] in used_signatures
    result=dict(source_directories=list(map(str,SOURCES)),script_sha256=digest(Path(__file__)),profiles=rows,rejected=rejected,
                inspected_native_outcomes=False,unique_material_profiles=len({r['material_sha256'] for r in rows}),
                unused_unique_material_profiles=len({r['material_sha256'] for r in rows}-used_signatures))
    (ROOT/'inventory.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (HERE/'inventory.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('unique_material_profiles','unused_unique_material_profiles')},indent=2))


if __name__=='__main__':main()
