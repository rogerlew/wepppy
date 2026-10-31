"""Independent first-crossing probe for a closing/reopening capacity."""
import importlib.util
import tempfile
from pathlib import Path
p=Path('/workdir/wepp-forest-release-20261009/tests/test_erod_interval_support.py')
s=importlib.util.spec_from_file_location('erod_test',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Factory:
    def mktemp(self,name):return Path(tempfile.mkdtemp(prefix=name))
f=m.native_erod.__wrapped__(Factory())
print('native',f(0.,.009,theta=0.,load=0.,capacity=.000016,
                 atc=1.,btc=-.01,erodibility=1.))
def capacity(x):return x*x-.01*x+.000016
for h in (1e-8,5e-9):
    x=0.;load=0.
    def derivative(x,load):return 1-load/capacity(x)
    for _ in range(400000):
        k1=h*derivative(x,load)
        k2=h*derivative(x+h/2,load+k1/2)
        k3=h*derivative(x+h/2,load+k2/2)
        k4=h*derivative(x+h,load+k3)
        new=load+(k1+2*k2+2*k3+k4)/6
        before=load-capacity(x);after=new-capacity(x+h)
        if after>0:
            print('independent',h,x+h*(-before)/(after-before))
            break
        x+=h;load=new
    else:raise AssertionError('No crossing before the singular boundary')
