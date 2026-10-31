import importlib.util,tempfile,os
from pathlib import Path
native=Path('/workdir/wepp-forest-release-20261009')
s=importlib.util.spec_from_file_location('route_test',native/'tests/test_route_inflow_boundary.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
root=Path(tempfile.mkdtemp(prefix='route-u9-edge-'))
(root/'src').symlink_to(native/'src',target_is_directory=True)
(root/'tests/native').mkdir(parents=True)
driver=(native/'tests/native/roads_route_boundary_driver.for').read_text()
assert driver.count('      cinftc(2)=.001')==1
(root/'tests/native/roads_route_boundary_driver.for').write_text(driver.replace('      cinftc(2)=.001','      cinftc(2)=-.001'))
m.ROOT=root
class Factory:
 def mktemp(self,n):return Path(tempfile.mkdtemp(prefix=n))
f=m.native_route.__wrapped__(Factory())
for initial in [0.,.01]:
 print('initial',initial,f(.1,initial=initial))
