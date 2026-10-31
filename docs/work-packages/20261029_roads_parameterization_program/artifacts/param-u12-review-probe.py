import importlib.util,tempfile,os,random
from pathlib import Path
root=Path('/workdir/wepp-forest-release-20261009')
s=importlib.util.spec_from_file_location('p',root/'tests/test_param_continuity_sign.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Factory:
 def mktemp(self,n):return Path(tempfile.mkdtemp(prefix=n))
os.environ['PARAM_SOURCE']=str(root/'src/param.for');old=m.probe.__wrapped__(Factory())
os.environ['PARAM_SOURCE']='/workdir/wepppy/out/roads-parameterization-program-20261031/param-sign-u12-combined/prototype/param.for';new=m.probe.__wrapped__(Factory())
r=random.Random(421)
ratios=[-1.0000001192092896,-.9999999403953552,-1.01,-.99,2.,-2.]
count=0
for b in [-2.,0.,.5,3.]:
 for ratio in ratios:
  a=r.uniform(-2,2)
  before=old(2,a,b,[ratio,ratio]);after=new(2,a,b,[ratio,ratio]);assert before==after,(a,b,ratio,before,after)
  count+=1
# Actual extracted producer fallback: spart1 below threshold -> qostar=-2.
values=[1e-6,1.,1.,1.,1.,1.,1.,1.]
for b in [-1.,0.,1.]:
 assert old(1,.5,b,values)==new(1,.5,b,values)
 count+=1
print('Exact parsed coefficient parity controls',count)
