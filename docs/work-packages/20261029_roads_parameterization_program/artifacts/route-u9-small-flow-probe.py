import importlib.util,tempfile,os
from pathlib import Path
p=Path('/workdir/wepp-forest-release-20261009/tests/test_route_inflow_boundary.py')
s=importlib.util.spec_from_file_location('tr',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Factory:
 def mktemp(self,n):return Path(tempfile.mkdtemp(prefix=n))
f=m.native_route.__wrapped__(Factory())
for q in [-.001,-1e-5,-1e-6,-1e-7,-1e-8,1e-8,1e-42,1e-44]:
 try:print(q,f(q))
 except Exception as exc:print(q,type(exc).__name__,getattr(exc,'stdout',''),getattr(exc,'stderr',''))
