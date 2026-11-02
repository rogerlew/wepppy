"""Original full-period bridge mutation controls; no native execution."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import read_combined_snow_bridge_v2 as reader
from check_snow_cap_diagnostics import snow_group


def run():
    checks=[]
    def reject(name,fn):
        try:fn()
        except ValueError:checks.append(name)
        else:raise AssertionError(name)
    group=snow_group(.01,350.)
    cold={'SNOW_ENTRY':[0.]*8,'SNOW_BRANCH_INPUT':[1.,1.,0.,0.,100.,1000.],'SNOW_RETURN':[0.]*10}
    rows=[((1,1,1,h),tag,values) for h in range(1,25) for tag,values in (group if h==1 else cold).items()]
    result=reader.audit_rows(rows,[(1,1,1)])
    assert result['applied_count']==1 and result['warm_groups']==1 and result['cold_groups']==23
    checks.append('warm cap plus23 cold limited groups')
    for name,mutated in [('missing entry',rows[1:]),('duplicate entry',[rows[0]]+rows),('missing mandatory melt',[r for r in rows if r[1]!='MELT_RAW']),('truncated group',rows[:-1]),('missing whole hour',[r for r in rows if r[0][3]!=10]),('unexpected day',[( (1,2,1,c[3]),t,v) for c,t,v in rows])]:
        reject(name,lambda m=mutated:reader.audit_rows(m,[(1,1,1)]))
    bad=copy.deepcopy(rows)
    at=next(i for i,r in enumerate(bad) if r[1]=='SNOW_CAP_FLAGS');bad[at][2][2]=0
    reject('candidate application changed',lambda:reader.audit_rows(bad,[(1,1,1)]))
    for value in ('2147483648','-2147483649','4294967295','1.0'):
        reject('integer range '+value,lambda v=value:reader.decode(v,'I'))
    reject('unknown kind',lambda:reader.decode('0','X'))
    reject('nan real',lambda:reader.decode('2143289344','R'))
    assert reader.decode('-2147483648','I')==-(1<<31)
    assert struct.pack('>f',reader.decode('-2147483648','R'))==b'\x80\0\0\0'
    checks.append('signed int32 negativezero distinct bits')
    def encoded():
        lines=['B5 1']
        for n,(clock,tag,values) in enumerate(rows,1):
            kind,count=reader.FIELDS[tag]
            bits=[int(v) if kind=='I' else struct.unpack('>i',struct.pack('>f',v))[0] for v in values]
            lines.append(' '.join(map(str,[n,*clock,kind,tag,count,*bits])))
        lines.append(f'END {len(rows)} 24 24')
        return '\n'.join(lines)+'\n'
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'bridge.txt';good=encoded();path.write_text(good)
        assert reader.audit_rows(reader.records(path),[(1,1,1)])['applied_count']==1
        checks.append('typed stream replay')
        for name,text in {'footer missing':'\n'.join(good.splitlines()[:-1])+'\n','footer wrong':good.replace('24 24\n','23 24\n'),'after footer':good+'x\n','wrong kind':good.replace('R SNOW_ENTRY','I SNOW_ENTRY',1),'unknown tag':good.replace('SNOW_ENTRY','FAKE',1),'duplicate sequence':good.replace('\n2 1','\n1 1',1),'overflow bits':good.replace('R SNOW_ENTRY 8','R SNOW_ENTRY 8 2147483648',1)}.items():
            path.write_text(text);reject(name,lambda:list(reader.records(path)))
    actual_path=Path('out/rock-water-development-20261101/R05-snow-cap-experiment-v3/cases/flagstaff-2711184-outrut-paved-high/candidate/diagnostic-readback.json')
    actual_binding=reader.binding(actual_path)
    actual=next(p for p in json.loads(actual_path.read_text())['snow'] if p['applied'])
    actual_group={tag:actual['inputs'][tag] for tag in reader.FIELDS if tag in actual['inputs']}
    actual_rows=[((1,1,1,h),tag,values) for h in range(1,25) for tag,values in (actual_group if h==1 else cold).items()]
    actual_result=reader.audit_rows(actual_rows,[(1,1,1)])['warm_proofs'][0]
    assert actual_result['owner_budget_exact_m']==actual['owner_budget_exact_m']
    checks.append('retained actual applied operands exact budget replay in synthetic clock harness')
    changed=copy.deepcopy(actual_rows)
    pos=next(i for i,r in enumerate(changed) if r[1]=='SNOW_RETURN');changed[pos][2][8]=0.
    reject('actual release mutation',lambda:reader.audit_rows(changed,[(1,1,1)]))
    assert reader.binding(actual_path)==actual_binding
    rawroot=Path('out/rock-water-development-20261101')
    lifecycle_bindings=[]
    for name in ['1718494-baseline','1718494-candidate','1856573-baseline','1856573-candidate','2711184-baseline','2711184-candidate']:
        source=rawroot/'B04-restoration-continuation-v2/observed/cases'/name/'runs/b02-daily-lifecycle.txt'
        if name=='1718494-baseline':source=rawroot/'B04-restoration-candidate-preparation-v4/observed/cases'/name/'runs/b02-daily-lifecycle.txt'
        before=reader.binding(source)
        dates=sorted({tuple(map(int,v[2:4])) for line in source.open() if len(v:=line.split())==25})
        keys=reader.lifecycle_keys(source,dates)
        assert keys and len(keys)==len(set(keys))
        if name=='1718494-baseline':
            receipt_path=rawroot/'B04-restoration-continuation-v2/first-pair-readback.json'
            full=next(c for c in json.loads(receipt_path.read_text())['cases'] if c['case']==name and c['variant']=='observed')
        else:
            receipt_path=source.parent.parent/'receipt.json';full=json.loads(receipt_path.read_text())
        assert full['passed'] and full['lifecycle']['passed'] and full['lifecycle']['winter_days']==len(keys)
        checks.append('actual full-reader winter census match '+name)
        assert reader.binding(source)==before
        lifecycle_bindings.append(dict(binding=before,full_reader_receipt=reader.binding(receipt_path),winter_invocations=len(keys)))
        checks.append('actual lifecycle including zero-index WIN_GATE '+name)
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'lifecycle.txt'
        content=source.read_text()
        lines=content.splitlines()
        gate=next(i for i,line in enumerate(lines) if line.split()[0]=='WIN_GATE')
        words=lines[gate].split();words[5]='1';lines[gate]=' '.join(words)
        path.write_text('\n'.join(lines)+'\n')
        reject('gate nonzero layer',lambda:reader.lifecycle_keys(path,dates))
        lines=content.splitlines();words=lines[1].split();words[5]='0';lines[1]=' '.join(words)
        path.write_text('\n'.join(lines)+'\n')
        reject('physical layer zero',lambda:reader.lifecycle_keys(path,dates))
        for label,field,value in [('unknown lifecycle tag',0,'FAKE'),('invalid cache validity',8,'2'),('wrong previous close epoch',6,'99')]:
            lines=content.splitlines();words=lines[1].split();words[field]=value;lines[1]=' '.join(words)
            path.write_text('\n'.join(lines)+'\n')
            reject(label,lambda:reader.lifecycle_keys(path,dates))
        lines=content.splitlines();words=lines[gate+1].split();words[0]='WIN_GATE';words[5]='0';lines[gate+1]=' '.join(words)
        path.write_text('\n'.join(lines)+'\n')
        reject('duplicate gate singleton',lambda:reader.lifecycle_keys(path,dates))

    return dict(passed=True,count=len(checks),controls=checks,actual_operand_binding=actual_binding,lifecycle_bindings=lifecycle_bindings)

if __name__=='__main__':print(json.dumps(run(),indent=2))
