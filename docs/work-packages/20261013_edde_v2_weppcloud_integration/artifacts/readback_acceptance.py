"""Read actual prepared CLI and WEPP consumer outputs in a fresh process."""
import hashlib
import json
from pathlib import Path
import numpy as np
from wepppy.nodb.core import Climate, Watershed, Soils
from wepppy.climates.edde.cligen import read_cli, _validate_cli
HERE=Path(__file__).resolve().parent
records=[]
for name in ('edde-ca-20261014','edde-us-current-20261014'):
    root=Path('/wc1/runs/ed')/name
    c=Climate.getInstance(str(root)); w=Watershed.getInstance(str(root)); t=w.translator_factory()
    record={'runid':name,'projection':c.edde_projection,'spatial_mode':int(c.climate_spatialmode),'provenance':c.edde_provenance,'files':[]}
    for top in w._subs_summary:
        hill=t.wepp(top=int(top)); source=root/'climate'/c.sub_summary(top)['cli_fn']; prepared=root/'wepp/runs'/f'p{hill}.cli'
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        assert digest(source)==digest(prepared)
        frame=read_cli(prepared);_validate_cli(frame)
        assert len(frame)==366 and str(frame.index[0].date())=='2060-01-01' and str(frame.index[-1].date())=='2060-12-31'
        item={'topaz_id':top,'wepp_id':hill,'source':source.name,'prepared':prepared.name,'sha256':digest(prepared),'days':len(frame)}
        output=root/'wepp/output'/f'H{hill}.wat.dat'
        if output.exists():
            values=np.array([[float(x) for x in line.split()] for line in output.read_text().splitlines() if len(line.split())==25 and line.split()[0].isdigit()])
            assert values.shape==(366,25) and np.isfinite(values).all()
            assert (values[:,2]==2060).all() and np.array_equal(values[:,1],np.arange(1,367))
            assert np.allclose(values[:,3],frame['prcp'],rtol=0,atol=.011)
            item['consumer']={'file':str(output.relative_to(root)),'sha256':digest(output),'rows':len(values),'precip_matches_cli':True}
        record['files'].append(item)
    s=Soils.getInstance(str(root));record['soil_setup']={'mode':int(s.mode),'initial_sat':s.initial_sat,'built':s.soils is not None}
    records.append(record)
(HERE/'artifact-readback.json').write_text(json.dumps(records,indent=2)+'\n')
print([(r['runid'],len(r['files']),sum('consumer' in f for f in r['files']),r['soil_setup']) for r in records])
