"""Real AshPost facade publication on the explicit one-hill replay baseline."""
from pathlib import Path
import json,shutil
import numpy as np
import pandas as pd
from wepppy.nodb.core import Watershed
from wepppy.nodb.mods.ash_transport import Ash,AshPost
root=Path('/wc1/runs/mo/mofe-water-replay-five-year-20261020')
source=Path('/wc1/runs/up/up-pedantry')
watershed=Watershed.getInstance(str(root));translator=watershed.translator_factory()
meta={str(topaz):dict(burn_class=3 if translator.wepp(top=topaz)==5 else 1,
                     area_ha=watershed.hillslope_area(topaz)/10000,
                     ash_type=1 if translator.wepp(top=topaz)==5 else None)
      for topaz in watershed._subs_summary}
for name in ['ash.nodb','ashpost.nodb']:
 data=json.loads((source/name).read_text().replace(str(source),str(root)))
 if name=='ash.nodb':data['py/state']['meta']=meta
 (root/name).write_text(json.dumps(data,indent=2))
post=AshPost.getInstance(str(root));post.run_post(recurrence=[2,5])
assert Ash.getInstance(str(root)).water_accounting_warning is None
actual=pd.read_parquet(root/'ash/post/watershed_daily.parquet')
baseline=pd.read_parquet(root/'wepp/output/interchange/totalwatsed3.parquet')
joined=actual.merge(baseline,on=['year','julian'],validate='many_to_one')
expected=joined['ash_runoff (m^3)']/joined.Area*1000+joined['Lateral Flow']
np.testing.assert_allclose(joined['Streamflow_ash_corr (mm)'],expected,rtol=1e-10,atol=1e-8)
proof=json.loads((root/'ash/post/water_accounting.json').read_text())
receipt={'baseline':'constructed one-hill PASS baseline, not routed watershed','rows':len(actual),'water_warning':None,'mapping':proof['mapping'],'outputs':proof['outputs'],'schema_manifest':(root/'ash/post/ashpost_version.json').exists(),'documentation':(root/'ash/post/README.md').exists()}
Path('/workdir/wepppy/docs/work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_ash_orchestration.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
