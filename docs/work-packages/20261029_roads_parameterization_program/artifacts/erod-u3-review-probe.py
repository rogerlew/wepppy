import importlib.util,tempfile,math,time,json
from pathlib import Path
p=Path('/workdir/wepp-forest-release-20261009/tests/test_erod_interval_support.py')
s=importlib.util.spec_from_file_location('te',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Factory:
 def mktemp(self,n):return Path(tempfile.mkdtemp(prefix=n))
f=m.native_erod.__wrapped__(Factory())
cases=[dict(xb=0.,xe=.009,theta=0.,load=0.,capacity=-.008,btc=1.,erodibility=1.),
 dict(xb=0.,xe=.009,theta=0.,load=0.,capacity=-.007,btc=1.,erodibility=1.),
 dict(xb=0.,xe=.009,theta=0.,load=0.,capacity=-.006,btc=1.,erodibility=1.),
 dict(xb=0.,xe=.009,theta=0.,load=0.,capacity=-.004,btc=1.,erodibility=1.)]
for c in cases:
 start=time.monotonic();r=f(**c)
 print(json.dumps(dict(case=c,result=r,seconds=time.monotonic()-start,expected=.5*(c['xe']+c['capacity']))))
