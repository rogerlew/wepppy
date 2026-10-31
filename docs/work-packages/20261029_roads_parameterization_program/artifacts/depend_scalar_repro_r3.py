"""Reduce the released failure to DEPEND and an independent closed-form root."""
from decimal import Decimal,localcontext
from pathlib import Path
import hashlib,json,struct,subprocess
HERE=Path(__file__).resolve().parent
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/depend-failure-r3/scalar')
SRC=Path('/workdir/wepp-forest-release-20261009/src')
VALUES=dict(xu=.0500000007,xl=1.,a=0.,b=.131171137,du=-16.3956165,phi=88269.4375,theta=0.,ktrato=.970817983,qostar=2.05239344)
DRIVER="""      program probe
      real xu,xl,a,b,du,phi,theta,ktrato,qostar,depend,result
      read(*,*) xu,xl,a,b,du,phi,theta,ktrato,qostar
      result=depend(xu,xl,a,b,du,phi,theta,ktrato,qostar)
      write(*,*) 'RESULT',result
      end
"""

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
def main():
    ROOT.mkdir(exist_ok=False);driver=ROOT/'probe.for';driver.write_text(DRIVER)
    source=SRC/'depend.for';observed=ROOT/'depend-observed.for';text=source.read_text();marker='      call depval(xu,xdend,a,b,phi,theta,du,ktrato,qostar,'
    assert text.count(marker)==3
    observed.write_text(text.replace(marker,"      write(*,*) 'TRIAL',xdend,xdend+qostar\n"+marker))
    values={k:f32(v) for k,v in VALUES.items()};stdin=' '.join(str(x) for x in values.values())+'\n';(ROOT/'input.txt').write_text(stdin)
    runs=[]
    for name,dep in [('released',source),('observed',observed)]:
        binary=ROOT/name
        command=['/usr/bin/gfortran','-O2','-fno-align-commons','-ffixed-line-length-72','-ffpe-trap=invalid,zero,overflow','-I',str(SRC),str(driver),str(SRC/'depeqs.for'),str(dep),'-o',str(binary)]
        subprocess.run(command,check=True,capture_output=True,text=True)
        result=subprocess.run([str(binary)],input=stdin,capture_output=True,text=True,timeout=30)
        (ROOT/(name+'.stdout')).write_text(result.stdout);(ROOT/(name+'.stderr')).write_text(result.stderr)
        assert result.returncode==-8
        runs.append(dict(lane=name,returncode=result.returncode,binary_sha256=sha(binary),command=command,stdout=result.stdout))
    with localcontext() as context:
        context.prec=80;d={k:Decimal.from_float(v) for k,v in values.items()}
        assert d['a']==d['theta']==0
        # Independent integrating-factor solution: D=A+(DU-A)*(U/V)^(1+phi).
        A=d['phi']*d['b']*d['ktrato']/(1+d['phi']);U=d['xu']+d['qostar']
        root=U*((A-d['du'])/A).ln().__truediv__(1+d['phi']).exp()-d['qostar']
        assert d['xu']<root<d['xl']
        reference=str(root)
    report=dict(values_float32=values,xl_provenance='GDB xmin=1; DEPEND initializes xmin=xl and does not change xmin when qostar>=0.',
        independent_root=reference,reference_precision_digits=80,runs=runs,
        native_source_sha256={n:sha(SRC/n) for n in ('depend.for','depeqs.for')},script_sha256=sha(Path(__file__)),
        disposition='Confirmed solver-domain/step overflow on a finite interior root; do not repair by loosening traps or changing soil parameters.')
    text=json.dumps(report,indent=2)+'\n';(ROOT/'result.json').write_text(text);(HERE/'depend-scalar-r3-result.json').write_text(text)
    print('Both scalar replays reproduce SIGFPE; independent root',reference,flush=True)
if __name__=='__main__':main()
