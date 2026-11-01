"""Retain actual SIFT builder outputs from finite declared source records."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
from wepppy.wepp.soils.utils import WeppSoilUtil

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--repo',required=True,type=Path)
ap.add_argument('--out',required=True,type=Path)
a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
test=a.repo/'tests/locales/canada/bc/soils/test_sift_rock_basis.py'
ns=runpy.run_path(str(test));result=[]
for name,volume in [('zero',0.),('normal',20.),('high',80.)]:
 root=a.out/name;root.mkdir()
 stats=ns['build_fixture'](root,volume)
 soil=WeppSoilUtil(str(root/'rock.sol'));ofe=soil.obj['ofes'][0]
 mass=100*(volume*2.65)/(volume*2.65+(100-volume)*1.3)
 assert ofe['sat']==.75
 for h in ofe['horizons']:assert float(h['rfg'])==float(f'{mass:.1f}')
 assert [float(h['solthk']) for h in ofe['horizons']]==[50,150,200,300,600,1000,2000]
 row=dict(name=name,source_volume_percent=volume,density=1.3,expected_mass_percent=mass,
          emitted_mass_percent=float(f'{mass:.1f}'),native_capped_mass_percent=min(85.,float(f'{mass:.1f}')),
          sat=.75,horizons=len(ofe['horizons']),files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()})
 result.append(row)
receipt={'cases':result,'builder_source_sha256':hashlib.sha256((a.repo/'wepppy/locales/canada/bc/soils/sift/sift.py').read_bytes()).hexdigest(),
         'test_helper_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'scope':'Actual builder from synthetic BCSLF records; not a live deployed geodatabase extraction'}
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
