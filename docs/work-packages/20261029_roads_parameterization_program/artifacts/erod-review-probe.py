import importlib.util,tempfile
from pathlib import Path
import math,json
p=Path('/workdir/wepp-forest-release-20261009/tests/test_erod_interval_support.py')
s=importlib.util.spec_from_file_location('te',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Factory:
 def mktemp(self,n):return Path(tempfile.mkdtemp(prefix=n))
f=m.native_erod.__wrapped__(Factory())
cases=[
 {'xb':0.,'xe':.009,'theta':.1,'load':0.,'capacity':.0005},
 {'xb':.002,'xe':.009,'theta':.1,'load':.0007,'capacity':.001},
 {'xb':.992,'xe':.999,'theta':.1,'load':.0007,'capacity':.001,'ilast':100},
 {'xb':0.,'xe':.009,'theta':.1,'load':.001,'capacity':.001},
 {'xb':.002,'xe':.009,'theta':.1,'load':.0011,'capacity':.001},
 {'xb':0.,'xe':.009,'theta':.1,'load':.0007,'capacity':0.},
 {'xb':.002,'xe':.009,'theta':.1,'load':0.,'capacity':0.},
 {'xb':0.,'xe':.009,'theta':.0,'load':.0007,'capacity':.001},
 {'xb':0.,'xe':.009,'theta':.1,'load':.0007,'capacity':.0016},
 {'xb':0.,'xe':.009,'theta':.1,'load':.0007,'capacity':.0015999999},
 {'xb':0.,'xe':.009,'theta':.1,'load':.0007,'capacity':.0016000001},
]
for case in cases:
 r=f(**case)
 print(json.dumps({'case':case,'result':r,'analytical_cross':case['xb']+(case['capacity']-case['load'])/case['theta'] if case['theta'] else None}))
