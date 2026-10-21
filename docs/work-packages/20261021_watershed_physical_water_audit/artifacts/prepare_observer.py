"""Isolate exact release sources and add read-only channel accounting probes."""
from pathlib import Path
import difflib
import io
import json
import subprocess
import tarfile

source=Path('/workdir/wepp-forest-release-20261009')
root=Path('/workdir/watershed-physical-water-audit-20261021/observer-source-v2')
root.mkdir(exist_ok=False)
commit='6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb'
blob=subprocess.check_output(['git','archive',commit,'src','fpm-src'],cwd=source)
with tarfile.open(fileobj=io.BytesIO(blob)) as t:t.extractall(root,filter='data')
p=root/'src/wshchr.for';before=p.read_text();s=before
s=s.replace('      integer i, it, itt, itpk, ih, is, nseg, ic, ishp, nt0', '''      integer i, it, itt, itpk, ih, is, nseg, ic, ishp, nt0
      integer auditunit,auditq,iaudit
      logical auditon,auditinit
      save auditunit,auditq,auditon,auditinit
      data auditinit /.false./''')
s=s.replace('      eps = 1.e-8','''      if (.not.auditinit) then
        inquire(file='water_audit.on',exist=auditon)
        if (auditon) then
          open(newunit=auditunit,file='water_audit_channel.txt',
     1         status='new',action='write')
          open(newunit=auditq,file='water_audit_hydrograph.txt',
     1         status='new',action='write')
        endif
        auditinit=.true.
      endif
      eps = 1.e-8''',1)
needle='\n      lastStor(ichan) = sfnl(ichan)'
assert s.count(needle)==1
s=s.replace(needle,'''
c     Read-only audit of existing states, before lastStor advances.
      if (auditon) then
        write(auditunit,9101) year,sdate,ielmt,ichan,
     1    rvolon(ielmt),chnvol(ielmt),rtrans(ielmt),
     1    volint(ichan),sinit(ichan),sfnl(ichan),lastStor(ichan),
     1    chvol,runvol(ielmt),tmpvol(ielmt),chnl1,dtchr,
     1    qBase(ichan),rvotop(ielmt),rvolat(ielmt)
        do iaudit=0,ntchr
          write(auditq,9102) year,sdate,ielmt,iaudit,
     1      dtchr,qin(iaudit),qlat(iaudit),q1(iaudit,ichan)
        enddo
      endif
'''+needle)
s=s.replace(' 104  format', ''' 9101 format(4(i8,1x),15(es24.16,1x))
 9102 format(4(i8,1x),4(es24.16,1x))
 104  format''',1)
p.write_text(s)
art=Path('/workdir/wepppy/docs/work-packages/20261021_watershed_physical_water_audit/artifacts')
(art/'channel-observation.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/src/wshchr.for',tofile='b/src/wshchr.for')))
(art/'observer-provenance.json').write_text(json.dumps(dict(source=str(source),commit=commit,root=str(root),purpose='Read-only channel state and rate observations; parity required'),indent=2)+'\n')
