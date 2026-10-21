"""Observe remaining hourly infiltration after the existing distribution loop."""
from pathlib import Path
import difflib
import shutil
src=Path('/workdir/watershed-physical-water-audit-20261021/observer-source-v2')
dst=src.with_name('hourly-observer-source')
shutil.copytree(src,dst)
p=dst/'src/watbal_hourly.for';before=p.read_text();s=before
needle='      save watcon, fcdep, totlqc'
assert s.count(needle)==1
s=s.replace(needle,'''      integer auditunit
      logical auditinit,auditon
      save auditunit,auditinit,auditon
      data auditinit /.false./
'''+needle)
needle='      sep(iplane) = 0.0'
assert s.count(needle)==1
s=s.replace(needle,'''      if (.not.auditinit) then
        inquire(file='water_audit.on',exist=auditon)
        if (auditon) open(newunit=auditunit,
     1    file='water_audit_hourly.txt',status='new',action='write')
        auditinit=.true.
      endif
'''+needle)
needle='c       ------ combined standing & fallen residue'
assert s.count(needle)==1
s=s.replace(needle,'''      if (auditon) write(auditunit,9901)
     1  year,sdate,iplane,ii,hrfin,xfin
c
'''+needle)
needle='      return'
assert s.count(needle)==1
s=s.replace(needle,''' 9901 format(4(i8,1x),2(es24.16,1x))
'''+needle)
p.write_text(s)
art=Path('/workdir/wepppy/docs/work-packages/20261021_watershed_physical_water_audit/artifacts')
(art/'hourly-observation.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/src/watbal_hourly.for',tofile='b/src/watbal_hourly.for')))
