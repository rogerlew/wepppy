"""Synthetic framing/arithmetic controls only; never native evidence."""
import calendar
import json
from pathlib import Path
import shutil
import sys
import read_native_v2 as n

out=Path(sys.argv[1]); out.mkdir()
base=out/'synthetic'; (base/'runs').mkdir(parents=True); (base/'output').mkdir()
rows=[]; wb=[]; hk=[]
fixture={'parsed':{'ofes':[{'sat':.75,'horizons':[{'solthk':200.,'wp':.1,'fc':.2,'rfg':0.}]}]}}
for ofe in range(1,4):
    for layer in range(1,4):
        dry=n.f(.1); fc=n.f(.2); por=n.f(.5); air=n.f(.95)
        dg=n.f(.1 if layer<3 else .2); depth=n.f(.1 if layer==1 else .2*(layer-1))
        ul=n.mul(n.sub(por,dry),dg); st=n.mul(n.sub(n.mul(n.mul(.75,por),1),dry),dg)
        cap=n.mul(dg,n.sub(fc,dry))
        values={'SO_SCON_INPUT':[dry,fc,dg,depth,0.,1300.],
                'SO_SCON_PORE':[por,air,1.,1300.,1300.,dry],
                'SO_SCON_ROCK':[dry,fc,n.f(.3),1.,por,dg],
                'SO_SCON_DRY':[dry,fc,por,dg,1.,air],
                'SO_SCON_UL':[ul,por,dry,dg,st,depth],
                'SO_SCON_K':[1e-6,1e-6,dg,depth,0.,0.]}
        for tag,v in values.items(): rows.append((tag,ofe,layer,v))
        wb.append(('SO_WBH_UL',ofe,layer,values['SO_SCON_UL']))
        for tag,v in [('WBH_HK_FCUL',[cap,ul]),('WBH_HK_RATIO',[n.f(cap/ul),0.])]:
            hk.append(f'{tag} y= 1 d= 1 e= {ofe} c= 0 s= {layer} v1= {v[0]:.4E} v2= {v[1]:.4E}\n')
def trace(records):
    return ''.join(f'{tag} {i} {o} {l} '+ ' '.join(f'{v:.16e}' for v in vals)+'\n' for i,(tag,o,l,vals) in enumerate(records,1))
(base/'runs/storage-init.txt').write_text(trace([r for o in range(1,4) for r in rows+wb if r[1]==o])); (base/'runs/wepp_observe.log').write_text(''.join(hk))
for suffix in ['ebe','element','loss','pass','plot','soil']: (base/f'output/H1.{suffix}.dat').write_text('1.0\n')
with (base/'output/H1.wat.dat').open('w') as f:
    for o in range(1,4):
        for y in range(1,17):
            for d in range(1,367 if calendar.isleap(y) else 366):
                c=['0']*25; c[:3]=map(str,[o,d,y]); c[21]='400'; f.write(' '.join(c)+'\n')
assert n.read(base,fixture)['passed']
def change_value(text,tag,index):
    lines=text.splitlines(keepends=True)
    i=next(i for i,line in enumerate(lines) if line.startswith(tag+' '))
    c=lines[i].split(); c[index]=str(float(c[index])+.001); lines[i]=' '.join(c)+'\n'
    return ''.join(lines)
mutations={
 'wb-value':lambda s:change_value(s,'SO_WBH_UL',5),
 'initial-stock':lambda s:change_value(s,'SO_SCON_UL',8),
 'missing-storage':lambda s:s.splitlines(keepends=True)[1:],
 'duplicate-storage':lambda s:s.splitlines(keepends=True)+[s.splitlines(keepends=True)[0]],
 'zero-porosity':lambda s:s.replace('5.0000000000000000e-01','0.0000000000000000e+00',1),
 'wb-operand':lambda s:s.replace('SO_WBH_UL 19 1 1','SO_WBH_UL 19 1 2',1),
}
accepted=[]
for name,mutate in mutations.items():
    root=out/name; shutil.copytree(base,root); p=root/'runs/storage-init.txt'
    changed=mutate(p.read_text()); p.write_text(''.join(changed) if isinstance(changed,list) else changed)
    try: n.read(root,fixture)
    except ValueError: accepted.append(name)
    else: raise ValueError('Corruption accepted '+name)
for name,filename,change in [
 ('wrong-hk-clock','runs/wepp_observe.log',lambda s:s.replace('WBH_HK_FCUL y= 1 d= 1','WBH_HK_FCUL y= 2 d= 1',1)),
 ('missing-hk','runs/wepp_observe.log',lambda s:''.join(x for x in s.splitlines(keepends=True) if not x.startswith('WBH_HK_FCUL'))),
 ('wrong-hk','runs/wepp_observe.log',lambda s:s.replace('v1= 1.0000E-02','v1= 9.0000E-02',1)),
 ('calendar-missing','output/H1.wat.dat',lambda s:''.join(s.splitlines(keepends=True)[1:])),
 ('nonfinite-output','output/H1.ebe.dat',lambda s:'nan\n')]:
    root=out/name; shutil.copytree(base,root); p=root/filename; prior=p.read_text(); changed=change(prior)
    if changed==prior: raise ValueError('Mutation did not apply '+name)
    p.write_text(changed)
    try: n.read(root,fixture)
    except ValueError: accepted.append(name)
    else: raise ValueError('Corruption accepted '+name)
(out/'receipt.json').write_text(json.dumps(dict(passed=True,synthetic_only=True,rejected=accepted),indent=2)+'\n')
print(accepted)
