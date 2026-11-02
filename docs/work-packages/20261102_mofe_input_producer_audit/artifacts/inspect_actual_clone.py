from pathlib import Path
import json
from wepppy.nodb.core import Wepp, Landuse, Soils, Watershed
from wepppy.wepp.management import read_management
from wepppy.wepp.soils.utils import WeppSoilUtil
wd='/wc1/runs/mi/mipa-calm-20261102'
w=Wepp.getInstance(wd);l=Landuse.getInstance(wd);s=Soils.getInstance(wd)
result={'wepp_bin':w.wepp_bin,'multi_ofe':w.multi_ofe,'landuse_assignment_count':len(l.domlc_mofe_d or {}),'hills':[]}
for path in sorted((Path(wd)/'landuse').glob('hill_*.mofe.man')):
    topaz=path.name.split('_')[1].split('.')[0]
    man=read_management(str(path));sol=Path(wd)/'soils'/f'hill_{topaz}.mofe.sol'
    result['hills'].append({'topaz':topaz,'nofe':man.nofe,'plants':[p.name for p in man.plants],
        'assignments':l.domlc_mofe_d.get(topaz),'soil_exists':sol.exists(),
        'soil_ofes':len(WeppSoilUtil(str(sol)).obj['ofes']) if sol.exists() else None})
Path('docs/work-packages/20261102_mofe_input_producer_audit/artifacts/actual_clone_inventory_v1.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
