"""Execute actual release CHRQIN using its committed native-test harness."""
import importlib.util
import json
import os
from pathlib import Path
ROOT=Path('/workdir/watershed-physical-water-audit-20261021/flat-hydrograph-system')
ROOT.mkdir(exist_ok=False)
os.environ['PATH']='/usr/bin:/bin'
source=Path('/workdir/wepp-forest-release-20261009/tests/test_component_reconstruction.py')
spec=importlib.util.spec_from_file_location('native_test',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Factory:
    def mktemp(self,name):
        p=ROOT/name;p.mkdir();return p
run=mod.reconstruct.__wrapped__(Factory())
cases=[('aligned_control',1200.,1.,1200.),('fractional_last_interval',900.,1.,900.),('peak_duration_below_volume',1000.,1.,600.),('observed_daily_1983_182',313.90,.067072,4680.),('observed_hourly_2017_37',177.17,.0035153,46800.)]
results=[]
for name,v,peak,duration in cases:
    for nt0 in [0,1]:
        q=run(vr=v,pr=peak,vs=0,duration=duration,active=0,nt0=nt0)
        total=sum(q[1:])*600
        results.append(dict(case=name,nt0=nt0,requested_volume_m3=v,peak_m3s=peak,duration_s=duration,integrated_volume_m3=total,deficit_m3=v-total))
assert abs(results[0]['deficit_m3'])<1e-6
assert abs(results[2]['deficit_m3']-300)<1e-6
assert abs(results[4]['deficit_m3']-400)<1e-6
(ROOT/'audit.json').write_text(json.dumps(dict(compiler='/usr/bin/gfortran',source_harness=str(source),source_commit='6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb',results=results),indent=2)+'\n')
print(json.dumps(results,indent=2))
