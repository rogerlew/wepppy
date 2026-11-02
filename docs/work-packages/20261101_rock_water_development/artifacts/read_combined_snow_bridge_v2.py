"""Original full-period B04 snow interaction reader; no physical admission."""
import math
from pathlib import Path
import struct

import read_snow_cap_diagnostics as snow
import read_combined_frost_activation as activation
from read_combined_frost_activation import binding, integer, require

FIELDS = {'SNOW_ENTRY': ('R',8), 'SNOW_BRANCH_INPUT': ('R',6),
          'SNOW_WARM_PACK': ('R',4), 'SNOW_CAP_PRE': ('R',8),
          'MELT_RAW': ('R',10), 'MELT_CAP_FLAG': ('I',1),
          'MELT_RETURN': ('R',3), 'SNOW_CAP_FLAGS': ('I',4),
          'SNOW_DEBIT': ('R',4), 'SNOW_RETURN': ('R',10)}


def decode(token, kind):
    require(token.lstrip('-+').isdigit(), 'Invalid integer encoding')
    value = int(token)
    integer(value, -(1 << 31), (1 << 31)-1)
    if kind == 'I':
        return value
    require(kind == 'R', 'Unknown primitive kind')
    result = struct.unpack('>f', (value & 0xffffffff).to_bytes(4,'big'))[0]
    require(math.isfinite(result), 'Nonfinite encoded real')
    return result


def lifecycle_keys(path, calendar):
    dates = [tuple(d) for d in calendar]
    require(dates and dates == sorted(set(dates)), 'Invalid calendar')
    for y,d in dates:
        integer(y,1,2147483647); integer(d,1,366)
    allowed=set(dates); groups={}; seq=0; footer=False; last=None
    with Path(path).open() as stream:
        require(stream.readline().strip() == 'B2_LIFECYCLE_SCHEMA 1', 'Lifecycle header')
        for line in stream:
            words=line.split(); require(words and not footer, 'Lifecycle trailing/empty record')
            if words[0]=='B2_LIFECYCLE_END':
                require(len(words)==2 and int(words[1])==seq, 'Lifecycle footer count');footer=True;continue
            require(len(words)==25, 'Lifecycle shape')
            n,y,d,ofe,layer,cy,cd,valid=map(int,words[1:9]); date=(y,d)
            require(words[0] in ('OPEN','SOIL_PRE','SOIL_POST','WIN_GATE','WIN_PRE','WIN_POST','WB_OPEN','CLOSE'), 'Unknown lifecycle stage')
            layer_valid = layer == 0 if words[0] == 'WIN_GATE' else 1 <= layer <= 100
            require(n==seq+1 and date in allowed and ofe==1 and layer_valid and valid in (0,1), 'Lifecycle identity')
            require(last is None or date>=last, 'Lifecycle date order')
            values=list(map(float,words[9:]))
            require(all(math.isfinite(v) and snow.f(v)==v for v in values), 'Lifecycle binary32 values')
            if valid==0:require((cy,cd)==(0,0),'Lifecycle cache provenance')
            groups.setdefault(date,[]).append((words[0],layer,(cy,cd),valid,values))
            seq=n;last=date
    require(footer and seq>0 and set(groups)==allowed, 'Incomplete lifecycle calendar/footer')
    result=[]; previous=(0,0); layer_count=None
    for date, rows in groups.items():
        if layer_count is None:
            layer_count=sum(row[0]=='OPEN' for row in rows)
            require(1<=layer_count<=100,'Layer count')
        gate_rows=[r for r in rows if r[0]=='WIN_GATE']
        require(len(gate_rows)==1,'Missing/duplicate winter gate')
        gate=gate_rows[0][4]
        require(gate[3:]==[0.]*13,'Winter gate unused operands')
        winter=gate[1]>0 or gate[0]<=0 or gate[2]>0
        names=['OPEN','SOIL_PRE','SOIL_POST','WIN_GATE']
        if winter:names+=['WIN_PRE','WIN_POST']
        names+=['WB_OPEN','CLOSE']
        expected=[(name,layer) for name in names for layer in ([0] if name=='WIN_GATE' else range(1,layer_count+1))]
        require([(r[0],r[1]) for r in rows]==expected,'Lifecycle exact stage/layer/gate order')
        for name,layer,epoch,valid,values in rows:
            expected_epoch=date if name=='CLOSE' else previous
            require(epoch==expected_epoch and valid==int(expected_epoch!=(0,0)),'Lifecycle cache epoch/validity')
        if winter:result.append((*date,1))
        previous=date
    return result


def records(path):
    seq=0;entries=0;returns=0;footer=False
    with Path(path).open() as stream:
        require(stream.readline().strip()=='B5 1','Bridge header')
        for line in stream:
            words=line.split();require(words and not footer,'Bridge trailing/empty record')
            if words[0]=='END':
                require(len(words)==4 and list(map(int,words[1:]))==[seq,entries,returns],'Bridge footer census')
                footer=True;continue
            require(len(words)>=8,'Bridge record shape')
            n,y,d,ofe,hour=map(int,words[:5]);kind,tag=words[5:7];count=int(words[7])
            require(n==seq+1,'Bridge missing/duplicate sequence')
            for value,lo,hi in ((y,1,2147483647),(d,1,366),(ofe,1,1),(hour,1,24)):
                integer(value,lo,hi)
            require(tag in FIELDS and (kind,count)==FIELDS[tag] and len(words)==8+count,'Bridge tag/kind/shape')
            values=[decode(v,kind) for v in words[8:]]
            seq=n;entries+=tag=='SNOW_ENTRY';returns+=tag=='SNOW_RETURN'
            yield (y,d,ofe,hour),tag,values
    require(footer and seq>0 and entries==returns,'Incomplete bridge')


def audit_rows(rows, expected_keys):
    expected=[(*key,h) for key in expected_keys for h in range(1,25)]
    require(expected and expected==sorted(set(expected)),'Expected invocation order')
    groups=0;active=None;next_tag='SNOW_ENTRY';warm=False;proofs=[];cold=0
    following={'SNOW_CAP_PRE':'MELT_RAW','MELT_RAW':'MELT_CAP_FLAG','MELT_CAP_FLAG':'MELT_RETURN','MELT_RETURN':'SNOW_CAP_FLAGS','SNOW_CAP_FLAGS':'SNOW_DEBIT','SNOW_DEBIT':'SNOW_RETURN'}
    for clock,tag,values in rows:
        require(groups<len(expected) and tuple(clock)==expected[groups], 'Unexpected/omitted snow clock')
        require(tag==next_tag,'Missing/duplicate/out-of-order snow owner')
        if tag=='SNOW_ENTRY':active={};next_tag='SNOW_BRANCH_INPUT'
        active[tag]=values
        if tag=='SNOW_BRANCH_INPUT':
            mean=snow.f(snow.f(values[0]+values[1])/2)
            warm=active['SNOW_ENTRY'][0]>0 and mean>=0
            next_tag='SNOW_WARM_PACK' if warm else 'SNOW_RETURN'
        elif tag=='SNOW_WARM_PACK':next_tag='SNOW_CAP_PRE' if values[0]>0 else 'SNOW_DEBIT'
        elif tag in following:next_tag=following[tag]
        elif tag=='SNOW_RETURN':
            snow.equal([values[7]],[active['SNOW_ENTRY'][7]],'Snowfall input changed')
            if warm:
                proof=snow.snow_proof(active,'cap_candidate');proof['clock']=list(clock);proofs.append(proof)
            else:cold+=1
            groups+=1;active=None;next_tag='SNOW_ENTRY'
    require(active is None and groups==len(expected),'Truncated/missing snow group')
    return dict(passed=True,invocations=len(expected_keys),hour_groups=groups,warm_groups=len(proofs),cold_groups=cold,
                applied_count=sum(p['applied'] for p in proofs),full_cap_count=sum(p['full_cap'] for p in proofs),
                warm_proofs=proofs,scientific_acceptance=False,
                constraints=['Cold branches have clock/branch/finite framing proof only, not a pack-budget proof.',
                             'Lifecycle physical validation, exact source parity and admission are external required gates.'])


def read(path,lifecycle_path,calendar):
    dependencies=[binding(p) for p in (path,lifecycle_path,__file__,snow.__file__,activation.__file__)]
    keys=lifecycle_keys(lifecycle_path,calendar)
    result=audit_rows(records(path),keys)
    require(dependencies==[binding(p['path']) for p in dependencies],'Mutated bridge dependency')
    result['bindings']=dependencies;result['winter_keys']=[list(k) for k in keys]
    return result
