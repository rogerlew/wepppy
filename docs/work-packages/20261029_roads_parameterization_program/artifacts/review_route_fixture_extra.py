from pathlib import Path
import json,subprocess,hashlib
r=json.loads(Path('/tmp/erod-u7-route-fixture-review.json').read_text());F=Path(r['observer']);S=Path('/workdir/wepp-forest-release-20261009/src');P=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/erod-event-u6/probe/src')
text=(F/'probe.for').read_text();mark='      xx=-1000.0';extra='''      if(mode.eq.2)then
        phi=-2.0
        qin=-qostar
        qout=0.0
        nslpts(iplane)=3
        xl(2,iplane)=.0005
        xu(3,iplane)=.0005
        xl(3,iplane)=1.0
        ainf(3)=0.0
        binf(3)=0.0
        cinf(3)=1.0
        ainftc(3)=0.0
        binftc(3)=0.0
        cinftc(3)=.001
      else if(mode.eq.3)then
        nslpts(iplane)=3
        xl(2,iplane)=.49992
        ainftc(2)=1.0
        binftc(2)=-1.0
        cinftc(2)=.2500001
        xu(3,iplane)=xl(2,iplane)
        xl(3,iplane)=1.0
        ainf(3)=0.0
        binf(3)=0.0
        cinf(3)=1.0
        ainftc(3)=0.0
        binftc(3)=0.0
        cinftc(3)=9.58052766009132e-8
      else if(mode.eq.4)then
        cinftc(2)=0.0
        binftc(2)=1.0
      endif
''';assert text.count(mark)==1;text=text.replace(mark,extra+mark);(F/'probe_extra.for').write_text(text)
text=(F/'depos.for').read_text();text=text.replace('      return\n',"      write(*,*) 'DEPOS_EXIT',xb,xe,du,ldlast,dl,ilast\n      return\n");(F/'depos_extra.for').write_text(text)
files=[Path(x) for x in r['source_sha256']];files=[F/'depos_extra.for' if x.name=='depos.for' else x for x in files]
p=subprocess.run(['/usr/bin/gfortran','-O2','-fno-align-commons','-ffixed-line-length-72','-ffpe-trap=invalid,zero,overflow','-fcheck=all','-I',str(S),str(F/'probe_extra.for'),*map(str,files),'-o',str(F/'probe_extra')],text=True,capture_output=True)
if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
rows=[]
for name,mode,q,L,theta in [('negative_small_inflow',2,-.001,.01,0),('u8_capacity_cancellation',3,1,1e-7,0),('exact_zero_inflow',4,0,0,.1)]:
 p=subprocess.run([str(F/'probe_extra')],input=f'{mode} {q} {L} {theta}\n',text=True,capture_output=True,timeout=10);row=dict(name=name,q=q,initial_load=L,theta=theta,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr);rows.append(row);print(row)
Path('/tmp/erod-u7-u8-route-extra-review.json').write_text(json.dumps(dict(observer=str(F),source_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},rows=rows),indent=2)+'\n')
